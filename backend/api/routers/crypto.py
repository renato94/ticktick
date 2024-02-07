from datetime import datetime
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
from typing import List
from icecream import ic
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
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

router = APIRouter(prefix="/crypto", tags=["crypto"])


def calculate_average_entry(initial_investment, num_tokens):
    if num_tokens == 0:
        return 0
    average_entry = initial_investment / num_tokens
    return average_entry


def get_kucoin_client(request: Request):
    return request.app.state.kucoin_client


def get_mex_client(request: Request):
    return request.app.state.mexc_client


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


@router.get("/all_symbols")
def get_all_tickers(
    kucoin_client: KuCoinClient = Depends(get_kucoin_client),
    mexc_client: MexcClient = Depends(get_mex_client),
):
    r_kucoin_symbols = kucoin_client.get_all_symbols()
    kucoin_symbols = [s["symbol"] for s in r_kucoin_symbols["data"]]
    r_mex_symbols = mexc_client.get_all_symbols()
    mexc_symbols = r_mex_symbols["data"]
    return {"kucoin": kucoin_symbols, "mexc": mexc_symbols}


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
        if not round(float(currency_data["free"]), 1) < 1:
            if currency_name not in mexc_summary.keys():
                mexc_summary[currency_name] = {
                    "balance": currency_data["free"],
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
        "kucoin": kucoin_summary,
        "mexc": mexc_summary,
    }


def get_drive_service(request: Request):
    return request.app.state.drive_service


def calculate_expected_klines(start_date, end_date, interval) -> int:
    delta = end_date - start_date
    expected_klines = delta.total_seconds() / 60
    ic(interval)
    if interval == GENERAL_KLINE_INTERVALS.ONE_HOUR.value:
        ek = expected_klines / 60
    elif interval == GENERAL_KLINE_INTERVALS.FOUR_HOURS.value:
        ek = expected_klines / 240
    elif interval == GENERAL_KLINE_INTERVALS.ONE_DAY.value:
        ek = expected_klines / 1440
    elif interval == GENERAL_KLINE_INTERVALS.ONE_WEEK.value:
        ek = expected_klines / 10080
    else:
        raise HTTPException(400, "Invalid Interval")
    return int(ek)


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


def get_klines_from_exchanges(
    exchange,
    symbol,
    interval,
    start_at,
    end_at,
    kucoin_client,
    mexc_client,
):
    expected_klines = calculate_expected_klines(
        datetime.fromtimestamp(start_at), datetime.fromtimestamp(end_at), interval
    )
    ic(
        "requesting data:",
        datetime.fromtimestamp(start_at),
        datetime.fromtimestamp(end_at),
    )
    if exchange == "kucoin":
        klines = kucoin_client.get_symbol_kline(
            symbol, interval, expected_klines, start_at, end_at
        )
    elif exchange == "mexc":
        klines = mexc_client.get_symbol_kline(
            symbol, interval, expected_klines, start_at, end_at
        )
    else:
        raise HTTPException(400, "Invalid Exchange")
    return klines


def delete_drive_file(drive_service, file_id):
    drive_service.files().delete(fileId=file_id).execute()


@router.get("/klines")
def get_symbol_klines(
    request: Request,
    exchange: str,
    symbol: str,
    interval: str,
    start_at: int = None,
    end_at: int = None,
    drive_service=Depends(get_drive_service),
    kucoin_client: KuCoinClient = Depends(get_kucoin_client),
    mexc_client: MexcClient = Depends(get_mex_client),
):
    ic(start_at, end_at)
    # check if it exists on drive saved klines
    crypto_folder_id = request.app.state.crypto_folder_id
    start_date = datetime.fromtimestamp(start_at)
    end_date = datetime.fromtimestamp(end_at)

    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")
    csv_name = f"{exchange}_{symbol}_{interval}_{start_date_str}_{end_date_str}.csv"
    csv_name_query = f"{exchange}_{symbol}_{interval}_"
    drive_query = f"'{crypto_folder_id}' in parents and name contains '{csv_name_query}' and name contains '.csv' and mimeType='text/csv' and trashed = false"
    ic(drive_query)
    result_kline_exists = drive_service.files().list(q=drive_query).execute()

    if result_kline_exists.get("files") != []:
        ic(result_kline_exists.get("files")[0].get("name"))
        ic(f"{csv_name} exists")

        # get start and end date of the saved csv
        found_file_name = result_kline_exists.get("files")[0].get("name")
        found_file_name = found_file_name.replace(".csv", "")
        found_file_name = found_file_name.replace(csv_name_query, "")
        file_id = result_kline_exists.get("files")[0].get("id")

        df_current = load_klines_from_drive(drive_service, file_id)

        ic(found_file_name)

        csv_start_date = parser.parse(found_file_name.split("_")[0])
        csv_end_date = parser.parse(found_file_name.split("_")[1])

        ic(csv_start_date, csv_end_date)
        ic(start_date, end_date)

        ic(csv_start_date <= start_date and csv_end_date >= end_date)
        ic(csv_start_date < start_date and csv_end_date < end_date)
        ic(csv_start_date > start_date and csv_end_date > end_date)
        ic(csv_start_date > start_date and csv_end_date < end_date)

        if csv_start_date <= start_date and csv_end_date >= end_date:
            ic("all data in the csv")

            ic("loaded df_current", df_current.columns)
            # filter the requested dates
            filtered_df = df_current[
                (df_current["time"] >= start_at) & (df_current["time"] <= end_at)
            ]
            ic("filtered df_current", filtered_df)
            return filtered_df.to_json()
        elif csv_start_date < start_date and csv_end_date < end_date:
            ic("need to request data after")
            # calculate delta btw existing_end_date and end_date
            klines = get_klines_from_exchanges(
                exchange,
                symbol,
                interval,
                end_at,
                csv_end_date.timestamp(),
                kucoin_client,
                mexc_client,
            )
            df = pd.DataFrame(klines)
            # load current csv
            df_current = load_klines_from_drive(drive_service, file_id)
            # prepend requested data to current csv
            df = pd.concat([df, df_current])
            ic(df.columns)
            # delete previus drive data
            new_csv_name = f"{exchange}_{symbol}_{interval}_{csv_start_date.strftime('%Y-%m-%d')}_{end_date_str}.csv"
            new_file_id = save_klines_to_drive(
                drive_service, crypto_folder_id, new_csv_name, df
            )
            ic(new_file_id)
            delete_drive_file(drive_service, file_id)
            return df.to_json()
        elif csv_start_date < start_date and csv_end_date < end_date:
            ic("need to request data before")
            klines = get_klines_from_exchanges(
                exchange,
                symbol,
                interval,
                start_at,
                csv_start_date.timestamp(),
                kucoin_client,
                mexc_client,
            )
            df = pd.DataFrame(klines)
            ic(df.columns)

            # load current csv
            ic(len(df_current))
            ic(len(df))
            # append requested data to current csv
            new_df = pd.concat([df, df_current])
            # delete previus drive data
            new_csv_name = f"{exchange}_{symbol}_{interval}_{start_date_str}_{csv_end_date.strftime('%Y-%m-%d')}.csv"
            new_file_id = save_klines_to_drive(
                drive_service, crypto_folder_id, new_csv_name, new_df
            )
            ic(new_file_id)
            delete_drive_file(drive_service, file_id)
            ic(new_df.columns)
            return new_df.to_json()

        elif csv_start_date > start_date and csv_end_date > end_date:
            ic("need to request data before and after")
            klines = get_klines_from_exchanges(
                exchange,
                symbol,
                interval,
                start_at,
                end_at,
                kucoin_client,
                mexc_client,
            )
            df = pd.DataFrame(
                klines,
                columns=["time", "open", "high", "low", "close"],
            )
            new_csv_name = (
                f"{exchange}_{symbol}_{interval}_{start_date_str}_{end_date_str}.csv"
            )
            delete_drive_file(drive_service, file_id)
            new_file_id = save_klines_to_drive(
                drive_service, crypto_folder_id, new_csv_name, new_df
            )
            ic(new_file_id)
            return df.to_json()
    else:
        ic(f"{csv_name} does not exist")

        klines = get_klines_from_exchanges(
            exchange,
            symbol,
            interval,
            start_at,
            end_at,
            kucoin_client,
            mexc_client,
        )

        if klines:
            df = pd.DataFrame(klines, columns=["time", "open", "high", "low", "close"])
            save_klines_to_drive(drive_service, crypto_folder_id, csv_name, df)
            return df.to_json()
        else:
            return pd.DataFrame(
                columns=["high", "open", "close", "volume", "time"]
            ).to_json()


@router.get("/trades")
def get_trades(
    drive_service=Depends(get_drive_service),
    kucoin_client: KuCoinClient = Depends(get_kucoin_client),
    mexc_client: MexcClient = Depends(get_mex_client),
):
    exchanges = ["kucoin", "mexc"]
    dfs = []
    accounts = {}
    for e in exchanges:
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
        if e == "kucoin":
            account = kucoin_client.parse_kucoin_account(df)
        elif e == "mexc":
            account = mexc_client.parse_mexc_account(df)
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
