from datetime import datetime, timedelta
import os
import time
from celery.schedules import crontab
from celery import Celery
from backend.api.core.exchanges_clients import KuCoinClient, MexcClient
from backend.api.routers.github_api import GitHubClient
from backend.config import GITHUB_ACCESS_TOKEN, SQLALCHEMY_DATABASE_URL
import httpx
from celery.signals import worker_process_init, worker_process_shutdown
from backend.api import database
from backend.api.models.crypto import Exchange, Symbol, Interval, Kline
import logging

logger = logging.getLogger(__name__)

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get(
    "CELERY_RESULT_BACKEND", "redis://localhost:6379"
)
log_file = ".logs/celery.log"
if not os.path.exists(".logs"):
    os.makedirs(".logs")
# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(),
    ],
)

# Add logger to the celery app
celery.conf.worker_log_format = "%(asctime)s - %(levelname)s - %(message)s"
celery.conf.worker_logger_name = "celery.worker"

# Example usage

db_conn = None


@worker_process_init.connect
def init_worker(**kwargs):
    global db_conn
    print("Initializing database connection for worker.")
    db_conn = database.get_db()


@worker_process_shutdown.connect
def shutdown_worker(**kwargs):
    global db_conn
    if db_conn:
        print("Closing database connectionn for worker.")
        db_conn.close()


@celery.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(
        crontab(),  # executes every minute
        get_exchanges_symbols.s(),
        expires=10,
    )
    sender.add_periodic_task(
        crontab(minute=0, hour="*/3"),  # executes every 3 hours
        get_github_repos.s(),
        expires=10,
    )


@celery.task(name="github_info")
def get_github_repos():
    github_client = GitHubClient(GITHUB_ACCESS_TOKEN)
    repos = github_client.get_repos()
    result = httpx.post("http://localhost:9090/github/repos/set", json=repos)
    logger.info(result)
    return True


@celery.task(name="get_symbol_klines")
def get_symbol_klines(exchange: str, symbol: str, base: str, interval: str):
    db = database.get_db()
    # make requests to exchange client and get klines until finding the last kline
    exchange = db.query(Exchange).filter(Exchange.name == exchange).first()
    if exchange.name == "KuCoin":
        kucoin_client = KuCoinClient(
            id=exchange.id,
            api_key=exchange.api_key,
            api_secret=exchange.secret_key,
            passphrase=exchange.passphrase,
            base_url=exchange.base_url,
        )
        symbol_db: Symbol = (
            db.query(Symbol)
            .filter(Symbol.symbol == symbol, Symbol.base_asset == base)
            .first()
        )
        interval_db: Interval = (
            db.query(Interval)
            .filter(Interval.exchange_id == exchange.id, Interval.interval == interval)
            .first()
        )
        # valid interval
        exchange_symbol = kucoin_client.build_symbol_pair(symbol_db)
        # iterate in past to find the last kline
        # if there is already data in the database, then start from the last kline
        last_kline = (
            db.query(Kline)
            .filter(
                Kline.symbol_id == symbol_db.id, Kline.interval_id == interval_db.id
            )
            .order_by(Kline.time.asc())
            .first()
        )

        if last_kline:
            start_date = datetime.fromtimestamp(int(last_kline.time))
        else:
            start_date = datetime.now()
        end_date = start_date - timedelta(days=5)

        start_date = int(start_date.timestamp())
        end_date = int(end_date.timestamp())

        while start_date > end_date:
            logger.info(
                str(datetime.fromtimestamp(start_date)),
                str(datetime.fromtimestamp(end_date)),
            )
            try:
                klines = kucoin_client.get_symbol_kline(
                    symbol=exchange_symbol,
                    interval=interval_db.interval,
                    start_at=start_date,
                    end_at=end_date,
                )
                last_kline = klines[-1]
            except Exception as e:
                logging.error(e)
                time.sleep(5)
                break

            start_date = int(last_kline["time"])
            # if 2 consequtive start_dates are the same, then we are in an infinite loop
            end_date = int(
                (datetime.fromtimestamp(start_date) - timedelta(days=5)).timestamp()
            )  # one day before

            logger.info(start_date)
            logger.info(end_date)
            for kline in klines:
                db.add(
                    Kline(
                        symbol_id=symbol_db.id,
                        interval_id=interval_db.id,
                        time=kline["time"],
                        open=kline["open"],
                        high=kline["high"],
                        low=kline["low"],
                        close=kline["close"],
                        volume=kline["volume"],
                        quote_asset_volume=None,
                    )
                )
        db.commit()


@celery.task(name="get_exchanges_symbols")
def get_exchanges_symbols():
    db = database.get_db()
    news_symbols = 0
    kucoin_exchange = db.query(Exchange).filter(Exchange.name == "KuCoin").first()
    kucoin_client = KuCoinClient(
        id=kucoin_exchange.id,
        api_key=kucoin_exchange.api_key,
        api_secret=kucoin_exchange.secret_key,
        passphrase=kucoin_exchange.passphrase,
        base_url=kucoin_exchange.base_url,
    )
    kucoin_symbols = kucoin_client.get_all_symbols()

    for symbol, base in kucoin_symbols.items():
        if (
            not db.query(Symbol)
            .filter(Symbol.symbol == symbol, Symbol.base_asset == base)
            .first()
        ):
            news_symbols += 1
            db.add(
                Symbol(exchange_id=kucoin_exchange.id, symbol=symbol, base_asset=base)
            )
    db.commit()
    logger.info(f"{kucoin_exchange.name} news_symbols: {news_symbols}")
    news_symbols = 0
    mexc_exchange = db.query(Exchange).filter(Exchange.name == "MEXC").first()
    mexc_client = MexcClient(
        mexc_exchange.id,
        mexc_exchange.api_key,
        mexc_exchange.secret_key,
        mexc_exchange.base_url,
    )
    logger.info(mexc_client)
    mexc_symbols = mexc_client.get_all_symbols()
    for symbol, base in mexc_symbols.items():
        if (
            not db.query(Symbol)
            .filter(Symbol.symbol == symbol, Symbol.base_asset == base)
            .first()
        ):
            news_symbols += 1
            db.add(Symbol(exchange_id=mexc_exchange.id, symbol=symbol, base_asset=base))
    db.commit()
    logger.info(f"{mexc_exchange.name} news_symbols: {news_symbols}")
    db.close()
