from icecream import ic
import httpx
from api.config import CRYPTO_RANK_API_KEY, CRYPTO_RANK_BASE_ENDPOINT
from fastapi import APIRouter
from api.config import SCOPES, SPREADSHEET_CRYPTO_ID
from api.sheets import pull_sheet_data


router = APIRouter(prefix="/crypto-rank", tags=["crypto-rank"])


@router.get("/initial_values")
def get_crypto_entries():
    # Read entries from google sheets
    data = pull_sheet_data(SCOPES, SPREADSHEET_CRYPTO_ID, "entries")
    return data


@router.get("/tickers")
def get_cryptos():
    symbols = []
    return CryptoRankClient.get_tickets(symbols)


class CryptoRankClient:
    def get_tickets(tickers):
        r = httpx.get(
            CRYPTO_RANK_BASE_ENDPOINT + "currencies",
            params={"api_key": CRYPTO_RANK_API_KEY, "symbols": ",".join(tickers)},
        )
        ic(r.json())
        return r.json()
