from typing import List
from icecream import ic
import httpx
from backend.config import CRYPTO_RANK_API_KEY, CRYPTO_RANK_BASE_ENDPOINT
from fastapi import APIRouter, Depends, Request
from backend.config import SCOPES, SPREADSHEET_CRYPTO_ID
from backend.api.exchanges_clients import KuCoinClient, MexcClient
from backend.api.sheets import pull_sheet_data

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
    ic(r_kucoin_account)
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
    ic(r_currencies_price_kucoin)

    ic(kucoin_summary)
    for currencie_name in kucoin_summary.keys():
        ic(currencie_name)
        kucoin_summary[currencie_name]["price"] = r_currencies_price_kucoin["data"][currencie_name]
    
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


@router.get("/klines")
def get_symbol_klines(
    symbol: str,
    interval: str,
    start_at: int = None,
    end_at: int = None,
    kucoin_client: KuCoinClient = Depends(get_kucoin_client),
    mexc_client: MexcClient = Depends(get_mex_client),
):
    r_kucoin_klines = kucoin_client.get_symbol_kline(symbol, interval, start_at, end_at)
    r_mex_klines = mexc_client.get_symbol_kline(symbol, interval, start_at, end_at)
    if r_kucoin_klines:
        return r_kucoin_klines
    return r_mex_klines


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