from datetime import datetime
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
from typing import Dict, List
from icecream import ic
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from backend.api.models.crypto import (
    Exchange,
    ExchangeSymbols,
    Interval,
    Kline,
    KlinesBase,
    Pair,
    Symbol,
    SymbolBase,
    SymbolPair,
)
from backend.config import DRIVE_CRYPTO_FOLDER, SCOPES, SPREADSHEET_CRYPTO_ID
from backend.api.core.exchanges_clients import (
    GENERAL_KLINE_INTERVALS,
    KuCoinClient,
    MexcClient,
)
from backend.api.sheets import pull_sheet_data
import pandas as pd
from dateutil import parser
import tempfile
from backend.celery_t.worker import get_symbol_klines as get_symbol_klines_task
from backend.api.log import logger

router = APIRouter(prefix="/crypto", tags=["crypto"])


def calculate_average_entry(initial_investment, num_tokens):
    if num_tokens == 0:
        return 0
    average_entry = initial_investment / num_tokens
    return average_entry


def get_kucoin_client(request: Request):
    return request.app.state.crypto_clients["KuCoin"]


def get_mex_client(request: Request):
    return request.app.state.crypto_clients["MEXC"]


@router.get("/all")
def get_crypto_entries(request: Request):
    # Read entries from google sheets
    data_df = pull_sheet_data(SCOPES, SPREADSHEET_CRYPTO_ID, "entries")
    data_df["invested value"] = data_df["invested value"].astype(float)
    data_df["n_tokens"] = data_df["n_tokens"].astype(float)

    crypto_dict = data_df.set_index("crypto rank id").to_dict(orient="index")
    r_crypto_rank = request.app.state.crypto_rank_client.get_symbols_by_ids(
        list(crypto_dict.keys())
    )

    for crypto in r_crypto_rank["data"]:
        c_id = str(crypto["id"])
        crypto_dict[c_id]["price"] = crypto["values"]["USD"]["price"]
        crypto_dict[c_id]["current investment value"] = (
            float(crypto["values"]["USD"]["price"]) * crypto_dict[c_id]["n_tokens"]
        )
        crypto_dict[c_id]["profit"] = (
            float(crypto_dict[c_id]["current investment value"])
            - crypto_dict[c_id]["invested value"]
        )
        crypto_dict[c_id]["profit %"] = round(
            (
                (
                    float(crypto_dict[c_id]["current investment value"])
                    - crypto_dict[c_id]["invested value"]
                )
                / float(crypto_dict[c_id]["invested value"])
            )
            * 100,
            2,
        )
        crypto_dict[c_id]["average entry"] = calculate_average_entry(
            crypto_dict[c_id]["invested value"], crypto_dict[c_id]["n_tokens"]
        )

    return crypto_dict


@router.get("/single/{crypto_symbol}")
def get_single_crypto(crypto_symbol: str, request: Request):
    r_crypto_rank = request.app.state.crypto_rank_client.get_symbols([crypto_symbol])
    return r_crypto_rank


def get_db(request: Request):
    return request.app.state.db


def get_exchange_client(request: Request, exchange_name: str):
    return request.app.state.crypto_clients[exchange_name]


@router.get("/all_symbols", response_model=List[ExchangeSymbols])
def get_all_tickers(request: Request, db=Depends(get_db)):
    # group exchange symbols and get them from the exchanges
    exchanges = db.query(Exchange).all()
    response = []
    # group symbols by exchange
    symbols_by_exchange = {}
    for exchange in exchanges:
        pairs_db = db.query(Pair).filter(Pair.exchange_id == exchange.id).all()
        pairs_ids = [pair.id for pair in pairs_db]
        pairs_dict = {p.id: p for p in pairs_db}
        symbols = (
            db.query(Symbol)
            .filter(Symbol.exchange_id == exchange.id, Symbol.pair_id.in_(pairs_ids))
            .all()
        )
        logger.info(f"symbols: {symbols[0]}")
        intervals: List[Interval] = (
            db.query(Interval).filter(Interval.exchange_id == exchange.id).all()
        )
        exchange_client = get_exchange_client(request, exchange.name)

        s_be = {}
        for s in symbols:
            if s.name not in s_be.keys():
                s_be[s.name] = []
            s_be[s.name].append(pairs_dict[s.pair_id].name)
        symbols_by_exchange = [SymbolPair(symbol=s, pairs=s_be[s]) for s in s_be.keys()]

        intervals = [it.name for it in intervals]

        response.append(
            ExchangeSymbols(
                exchange=exchange.name, symbols=symbols_by_exchange, intervals=intervals
            )
        )

    return response


@router.get("/orders")
def get_orders(
    kucoin_client: KuCoinClient = Depends(get_kucoin_client),
    mexc_client: MexcClient = Depends(get_mex_client),
):
    r_kucoin_orders = kucoin_client.get_all_orders()
    r_mex_orders = mexc_client.get_all_orders()
    return {"kucoin": r_kucoin_orders, "mexc": r_mex_orders}


@router.get("/account")
def get_account(
    kucoin_client: KuCoinClient = Depends(get_kucoin_client),
    mexc_client: MexcClient = Depends(get_mex_client),
):
    r_kucoin_account = kucoin_client.get_account_summary()
    kucoin_summary = {}
    for currency_data in r_kucoin_account["data"]:
        currency_name = currency_data["currency"]
        if not round(float(currency_data["available"]), 1) < 1:
            if currency_name not in kucoin_summary.keys():
                kucoin_summary[currency_name] = {
                    "balance": currency_data["balance"],
                    "account_Type": currency_data["type"],
                }
    currencies_kucoin: List[str] = list(kucoin_summary.keys())

    r_currencies_price_kucoin = kucoin_client.get_symbol_price(
        symbols=currencies_kucoin
    )

    for currencie_name in kucoin_summary.keys():
        kucoin_summary[currencie_name]["price"] = r_currencies_price_kucoin["data"][
            currencie_name
        ]

    # ic(r_currencies_price_kucoin)
    r_mexc_account = mexc_client.get_account_summary()
    mexc_summary = {}
    for currency_data in r_mexc_account["balances"]:
        currency_name = currency_data["asset"]
        currency_balance = float(currency_data["free"]) + float(currency_data["locked"])
        if not round(currency_balance, 1) < 1:
            if currency_name not in mexc_summary.keys():
                mexc_summary[currency_name] = {
                    "balance": currency_balance,
                    "account_Type": r_mexc_account["accountType"],
                }

    r_currencies_price_mexc = mexc_client.get_symbol_price()
    # filter existing currencies in the mexc account

    currencies_price_mexc = {
        c["symbol"]: {"price": c["price"]} for c in r_currencies_price_mexc
    }
    for currencie_name in mexc_summary.keys():
        if currencie_name in mexc_summary.keys():
            mexc_summary[currencie_name]["price"] = currencies_price_mexc[
                currencie_name + "USDT"
            ]["price"]
    # ic(r_currencies_price_mexc)
    return {
        kucoin_client.name: kucoin_summary,
        mexc_client.name: mexc_summary,
    }


def get_drive_service(request: Request):
    return request.app.state.drive_service


def save_klines_to_drive(drive_service, crypto_folder_id, csv_name, df):
    ic(df.columns)
    # save to drive
    df.to_csv(csv_name)
    file_metadata = {
        "name": csv_name,
        "parents": [crypto_folder_id],
        "mimeType": "text/csv",
    }
    media = MediaFileUpload(csv_name, mimetype="text/csv")
    new_id = (
        drive_service.files().create(body=file_metadata, media_body=media).execute()
    )
    return new_id


def load_klines_from_drive(drive_service, file_id):
    request = drive_service.files().get_media(fileId=file_id)
    fh = tempfile.NamedTemporaryFile(delete=True)
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    fh.seek(0)
    df = pd.read_csv(fh, index_col=0)
    fh.close()
    return df


def calculate_dates_for_exchange_request(
    existing_start_date, existing_end_date, start_date, end_date
):
    if existing_start_date <= start_date and existing_end_date >= end_date:
        ic("all data in the csv")

        return None, None
    elif existing_start_date < start_date and existing_end_date < end_date:
        ic("need to request data after")
        # calculate delta btw existing_end_date and end_date
        delta_date = end_date - existing_end_date

        return existing_end_date, end_date
    elif existing_start_date > start_date and existing_end_date > end_date:
        ic("need to request data before")
        return start_date, existing_start_date
    elif existing_start_date > start_date and existing_end_date < end_date:
        ic("need to request data before and after")
        return start_date, end_date
    elif existing_start_date < start_date and existing_end_date > end_date:
        ic("need to request data before and after")
        return existing_end_date, existing_start_date
    else:
        ic("invalid date range")
        return None, None


def delete_drive_file(drive_service, file_id):
    drive_service.files().delete(fileId=file_id).execute()


@router.get("/klines")
def get_symbol_klines(
    request: Request,
    exchange: str,
    symbol: str,
    pair: str,
    interval: str,
    start_at: int = None,
    end_at: int = None,
    db=Depends(get_db),
) -> List[KlinesBase]:
    exchange_db = db.query(Exchange).filter(Exchange.name == exchange).first()
    crypto_exchange_client: KuCoinClient | MexcClient = (
        request.app.state.crypto_clients[exchange_db.name]
    )
    logger.info(f"exchange_db: {exchange_db.name}")
    pair_db = (
        db.query(Pair)
        .filter(Pair.exchange_id == exchange_db.id, Pair.name == pair)
        .first()
    )

    symbol_db = (
        db.query(Symbol)
        .filter(
            Symbol.exchange_id == exchange_db.id,
            Symbol.name == symbol,
            Symbol.pair_id == pair_db.id,
        )
        .first()
    )
    # check if symbol and pair exists
    if not symbol_db:
        raise HTTPException(status_code=404, detail="Symbol not found")

    interval_db = (
        db.query(Interval)
        .filter(Interval.exchange_id == exchange_db.id, Interval.name == interval)
        .first()
    )
    # check if valid interval
    if not interval_db:
        raise HTTPException(status_code=404, detail="Interval not found")

    klines_filters = [
        Kline.symbol_id == symbol_db.id,
        Kline.interval_id == interval_db.id,
    ]

    if start_at:
        klines_filters.append(Kline.time >= str(start_at))
    if end_at:
        klines_filters.append(Kline.time <= str(end_at))
    klines: List[Kline] = db.query(Kline).filter(*klines_filters).all()
    if klines:
        return klines
    else:
        # trigger a celery task to get the klines
        
    # klines to dataframe
    # df = [
    #         {
    #             "time": k.time,
    #             "open": k.open,
    #             "high": k.high,
    #             "low": k.low,
    #             "close": k.close,
    #             "volume": k.volume,
    #         }
    #         for k in klines
    #     ]
    return klines


@router.get("/klines/all")
def get_klines(exchange: str, symbol: str, base: str, interval: str):
    # start celery task to get all klines for a interval and symbol
    task = get_symbol_klines_task.apply_async(args=[exchange, symbol, base, interval])
    return {"task_id": task.id, "status": "started"}


@router.get("/trades")
def get_trades(
    drive_service=Depends(get_drive_service),
    kucoin_client: KuCoinClient = Depends(get_kucoin_client),
    mexc_client: MexcClient = Depends(get_mex_client),
):
    dfs = []
    accounts = {}
    for e in [kucoin_client.name, mexc_client.name]:
        result = (
            drive_service.files()
            .list(
                q=f"name='{e}-trades.csv' and mimeType='text/csv'",
            )
            .execute()
        )
        # get file id
        file_id = result.get("files")[0].get("id")
        # download file
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_csv(fh)
        if e == "KuCoin":
            account = kucoin_client.parse_account(df)
        elif e == "MEXC":
            account = mexc_client.parse_account(df)
        accounts[e] = account
        dfs.append(df)
    return accounts


def calculate_support_resistance(df):
    sr = []
    n1 = 3
    n2 = 2
    for row in range(3, len(df) - n2):  # len(df)-n2
        if support(df, row, n1, n2):
            sr.append((row, df.low[row], 1))
        if resistance(df, row, n1, n2):
            sr.append((row, df.high[row], 2))
    print(sr)
    plotlist1 = [x[1] for x in sr if x[2] == 1]
    plotlist2 = [x[1] for x in sr if x[2] == 2]
    plotlist1.sort()
    plotlist2.sort()

    for i in range(1, len(plotlist1)):
        if i >= len(plotlist1):
            break
        if abs(plotlist1[i] - plotlist1[i - 1]) <= 0.005:
            plotlist1.pop(i)

    for i in range(1, len(plotlist2)):
        if i >= len(plotlist2):
            break
        if abs(plotlist2[i] - plotlist2[i - 1]) <= 0.005:
            plotlist2.pop(i)
    return plotlist1, plotlist2


def support(df1, l, n1, n2):  # n1 n2 before and after candle l
    for i in range(l - n1 + 1, l + 1):
        if df1.low[i] > df1.low[i - 1]:
            return 0
    for i in range(l + 1, l + n2 + 1):
        if df1.low[i] < df1.low[i - 1]:
            return 0
    return 1


# support(df,46,3,2)


def resistance(df1, l, n1, n2):  # n1 n2 before and after candle l
    for i in range(l - n1 + 1, l + 1):
        if df1.high[i] < df1.high[i - 1]:
            return 0
    for i in range(l + 1, l + n2 + 1):
        if df1.high[i] > df1.high[i - 1]:
            return 0
    return 1


# resistance(df, 30, 3, 5)
