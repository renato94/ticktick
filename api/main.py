import asyncio
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Request
from icecream import ic
import jwt
from api import create_access_token, verify_token
from api.crypto import CryptoRankClient
from api.exchanges_clients import KuCoinClient, MexcClient
from api.ticktick import TickTickClient, router as ticktick_router
from api.garmin import router as garmin_router
from api.github_api import GitHubClient, router as github_router
from api.crypto import router as crypto_router
from api.finances import router as finances_router
from api.config import (
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
    SECRET_KEY,
)
from pyotp import TOTP
from uuid import uuid4

from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="otp")

app = FastAPI(debug=True)

app.include_router(garmin_router)
app.include_router(ticktick_router)
app.include_router(github_router)
app.include_router(crypto_router)
app.include_router(finances_router)


@app.on_event("startup")
def startup_event():
    github_client = GitHubClient(GITHUB_ACCESS_TOKEN)
    ticktick_client = TickTickClient()
    crypto_rank_client = CryptoRankClient()
    kucoin_client = KuCoinClient(
        api_key=KUCOIN_API_KEY,
        api_secret=KUCOIN_API_SECRET,
        passphrase=KUCOIN_API_PASSPHRASE,
        base_url=KUCOIN_API_BASE_URL,
    )

    mexc_client = MexcClient(
        api_key=MEXC_API_KEY, api_secret=MEXC_API_SECRET, base_url=MEXC_BASE_URL
    )
    # asyncio.create_task(github_client.get_repos())
    app.state.tokens = []
    app.state.ticktick_client = ticktick_client
    app.state.crypto_rank_client = crypto_rank_client
    app.state.kucoin_client = kucoin_client
    app.state.mexc_client = mexc_client
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
