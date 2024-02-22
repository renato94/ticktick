import asyncio
from typing import Dict
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException
from icecream import ic

from backend.api import create_access_token, verify_token
from backend.api.core.exchanges_clients import (
    ExchangeClient,
    KuCoinClient,
    MexcClient,
    CryptoRankClient,
)
from backend.api.models import crypto
from backend.api.models.crypto import Exchange
from backend.api.sheets import create_drive_folder, get_google_services
from backend.api.routers.ticktick import TickTickClient, router as ticktick_router
from backend.api.routers.garmin import router as garmin_router
from backend.api.routers.github_api import GitHubClient, router as github_router
from backend.api.routers.crypto import router as crypto_router
from backend.api.routers.finances import router as finances_router
from backend.config import (
    ALGORITHM,
    GITHUB_ACCESS_TOKEN,
    KUCOIN_API_BASE_URL,
    KUCOIN_API_KEY,
    KUCOIN_API_PASSPHRASE,
    KUCOIN_API_SECRET,
    MEXC_API_KEY,
    MEXC_API_SECRET,
    MEXC_BASE_URL,
    OPT_KEY,
    SCOPES,
    SECRET_KEY,
    DRIVE_BASE_FOLDER,
    DRIVE_CRYPTO_FOLDER,
    DRIVE_GARMIN_FOLDER,
)
from pyotp import TOTP
from uuid import uuid4
from backend.api.database import create_database, get_db
from fastapi.security import OAuth2PasswordBearer
from backend.api.log import logger

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="otp")

app = FastAPI(debug=True)

app.include_router(garmin_router)
app.include_router(ticktick_router)
app.include_router(github_router)
app.include_router(crypto_router)
app.include_router(finances_router)


def create_drive_main_folders(
    drive_service, DRIVE_BASE_FOLDER, DRIVE_CRYPTO_FOLDER, DRIVE_GARMIN_FOLDER
):
    # BASE FOLDER
    result_base_folder = (
        drive_service.files()
        .list(
            q=f"name='{DRIVE_BASE_FOLDER}' and mimeType='application/vnd.google-apps.folder'",
        )
        .execute()
    )
    if result_base_folder.get("files") == []:  # Create base folder
        logger.info("creating base folder")
        base_folder_id = create_drive_folder(drive_service, DRIVE_BASE_FOLDER)
    else:
        base_folder_id = result_base_folder.get("files")[0].get("id")
    # CRYPTO FOLDER
    result_crypto_folder = (
        drive_service.files()
        .list(
            q=f"name='{DRIVE_CRYPTO_FOLDER}' and mimeType='application/vnd.google-apps.folder'",
        )
        .execute()
    )
    if result_crypto_folder.get("files") == []:
        crypto_folder_id = create_drive_folder(
            drive_service, DRIVE_CRYPTO_FOLDER, parent_id=base_folder_id
        )
    else:
        crypto_folder_id = result_crypto_folder.get("files")[0].get("id")
    # GARMIN FOLDER
    result_garmin_folder = (
        drive_service.files()
        .list(
            q=f"name='{DRIVE_GARMIN_FOLDER}' and mimeType='application/vnd.google-apps.folder'",
        )
        .execute()
    )
    if result_garmin_folder.get("files") == []:
        garmin_folder_id = create_drive_folder(
            drive_service, DRIVE_GARMIN_FOLDER, parent_id=base_folder_id
        )
    else:
        garmin_folder_id = result_garmin_folder.get("files")[0].get("id")
    return crypto_folder_id, garmin_folder_id


@app.on_event("startup")
def startup_event():
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")
    logger.critical("critical message")

    drive_service, sheets_service = get_google_services(SCOPES)

    crypto_folder_id, garmin_folder_id = create_drive_main_folders(
        drive_service, DRIVE_BASE_FOLDER, DRIVE_CRYPTO_FOLDER, DRIVE_GARMIN_FOLDER
    )
    app.state.crypto_folder_id = crypto_folder_id
    app.state.garmin_folder_id = garmin_folder_id
    app.state.drive_service = drive_service
    app.state.sheets_service = sheets_service
    github_client = GitHubClient(GITHUB_ACCESS_TOKEN)
    ticktick_client = TickTickClient()
    crypto_rank_client = CryptoRankClient()

    db = get_db()
    from backend.api.models import goals

    create_database()

    def get_or_add_exchanges(db):

        kucoin_exchange = db.query(Exchange).filter(Exchange.name == "KuCoin").first()
        exchanges = []
        if not kucoin_exchange:
            kucoin_exchange = Exchange(
                name="KuCoin",
                api_key=KUCOIN_API_KEY,
                secret_key=KUCOIN_API_SECRET,
                passphrase=KUCOIN_API_PASSPHRASE,
                base_url=KUCOIN_API_BASE_URL,
            )
            db.add(kucoin_exchange)
            db.commit()

            add_kucoin_exchange_interval(db, kucoin_exchange.id)
            exchanges.append(kucoin_exchange)
        mexc_exchange = db.query(Exchange).filter(Exchange.name == "MEXC").first()
        if not mexc_exchange:
            mexc_exchange = Exchange(
                name="MEXC",
                api_key=MEXC_API_KEY,
                secret_key=MEXC_API_SECRET,
                base_url=MEXC_BASE_URL,
            )
            db.add(mexc_exchange)
            db.commit()
            add_mexc_echange_interval(db, mexc_exchange.id)
            exchanges.append(mexc_exchange)
            return exchanges
        else:
            return db.query(Exchange).all()

    def add_kucoin_exchange_interval(db, exchange_id):
        ONE_MINUTE = "1min"
        FIVE_MINUTES = "5min"
        FIFTHEEN_MINUTES = "15min"
        THIRTHY_MINUTEs = "30min"
        ONE_HOUR = "1hour"
        FOUR_HOURS = "4hour"
        ONE_DAY = "1day"
        ONE_WEEK = "1week"

        intervals = [
            ONE_MINUTE,
            FIVE_MINUTES,
            FIFTHEEN_MINUTES,
            THIRTHY_MINUTEs,
            ONE_HOUR,
            FOUR_HOURS,
            ONE_DAY,
            ONE_WEEK,
        ]

        for interval in intervals:
            db.add(crypto.Interval(exchange_id=exchange_id, name=interval))
        db.commit()

    def add_mexc_echange_interval(db, exchange_id):
        ONE_MINUTE = "1m"
        FIVE_MINUTES = "5m"
        FIFTHEEN_MINUTES = "15m"
        THIRTHY_MINUTEs = "30m"
        ONE_HOUR = "60m"
        FOUR_HOURS = "4h"
        ONE_DAY = "1d"
        ONE_WEEK = "1W"
        ONE_MONTH = "1M"

        intervals = [
            ONE_MINUTE,
            FIVE_MINUTES,
            FIFTHEEN_MINUTES,
            THIRTHY_MINUTEs,
            ONE_HOUR,
            FOUR_HOURS,
            ONE_DAY,
            ONE_WEEK,
            ONE_MONTH,
        ]

        for interval in intervals:
            db.add(crypto.Interval(exchange_id=exchange_id, name=interval))
        db.commit()

    exchanges = get_or_add_exchanges(db)
    kucoin_exchange = exchanges[0]
    mexc_exchange = exchanges[1]
    #add_kucoin_exchange_interval(db, kucoin_exchange.id)
    #add_mexc_echange_interval(db, mexc_exchange.id)
    logger.info(exchanges)
    app.state.db = db

    # asyncio.create_task(github_client.get_repos())
    app.state.tokens = []
    app.state.crypto_clients: Dict[str, ExchangeClient] = dict()
    app.state.ticktick_client = ticktick_client
    app.state.crypto_rank_client = crypto_rank_client
    app.state.crypto_clients[kucoin_exchange.name] = KuCoinClient(
        id=kucoin_exchange.id,
        name=kucoin_exchange.name,
        api_key=kucoin_exchange.api_key,
        api_secret=kucoin_exchange.secret_key,
        passphrase=kucoin_exchange.passphrase,
        base_url=kucoin_exchange.base_url,
    )

    app.state.crypto_clients[mexc_exchange.name] = MexcClient(
        id=mexc_exchange.id,
        name=mexc_exchange.name,
        api_key=mexc_exchange.api_key,
        api_secret=mexc_exchange.secret_key,
        base_url=mexc_exchange.base_url,
    )
    app.state.github_client = github_client
    app.state.totp = TOTP(OPT_KEY)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/otp/{code}")
def verify_code(code: str):
    if app.state.totp.verify(code):
        token = create_access_token({"sub": str(uuid4())})
        return {"access_token": token}
    else:
        raise HTTPException(status_code=401, detail="Invalid authentication code")


@app.get("/authenticated")
def authenticated(payload: dict = Depends(verify_token)):
    if payload:
        return {"authenticated": True}
    else:
        return {"authenticated": False}
