from icecream import ic
import httpx
from api.config import CRYPTO_RANK_API_KEY, CRYPTO_RANK_BASE_ENDPOINT
from fastapi import APIRouter, Request
from api.config import SCOPES, SPREADSHEET_CRYPTO_ID
from api.sheets import pull_sheet_data

router = APIRouter(prefix="/crypto-rank", tags=["crypto-rank"])


def calculate_average_entry(initial_investment, num_tokens):
    if num_tokens == 0:
        return 0
    average_entry = initial_investment / num_tokens
    return average_entry


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
        return r.json()
