from icecream import ic
import httpx
from api.config import CRYPTO_RANK_API_KEY, CRYPTO_RANK_BASE_ENDPOINT
from fastapi import APIRouter, Request
from api.config import SCOPES, SPREADSHEET_CRYPTO_ID
from api.sheets import pull_sheet_data
import pandas as pd

router = APIRouter(prefix="/crypto-rank", tags=["crypto-rank"])


@router.get("/initial_values")
def get_crypto_entries(request: Request):
    # Read entries from google sheets
    data = pull_sheet_data(SCOPES, SPREADSHEET_CRYPTO_ID, "entries")
    columns = data[0]
    entries = data[1:]
    data_df = pd.DataFrame(entries, columns=columns)
    ic(columns)
    ids = data_df["crypto rank id"].tolist()
    r_crypto_rank = request.app.state.crypto_rank_client.get_symbols_by_ids(ids=ids)
    for symbol_data in r_crypto_rank:
        ic(symbol_data)


    return data_df.to_json()


@router.get("/tickers")
def get_cryptos(request: Request):
    symbols = []
    return request.app.state.crypto_rank_client.get_tickets(symbols)


class CryptoRankClient:
    def get_symbols(self, symbols):
        r = httpx.get(
            CRYPTO_RANK_BASE_ENDPOINT + "currencies",
            params={
                "api_key": CRYPTO_RANK_API_KEY,
                "symbols": ",".join(symbols),
                "state": "active",
            },
        )
        ic(r.json())
        return r.json()

    def get_symbols_by_ids(self, ids):
        r = httpx.get(
            CRYPTO_RANK_BASE_ENDPOINT + "currencies",
            params={
                "api_key": CRYPTO_RANK_API_KEY,
                "ids": ",".join(ids),
                "state": "active",
            },
        )
        ic(r.json())
        return r.json()
