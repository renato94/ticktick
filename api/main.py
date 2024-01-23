import asyncio
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Request
from icecream import ic
import jwt
from api import create_access_token, verify_token
from api.crypto_rank import CryptoRankClient
from api.ticktick import TickTickClient, router as ticktick_router
from api.garmin import router as garmin_router
from api.github_api import GitHubClient, router as github_router
from api.crypto_rank import router as crypto_router
from api.finances import router as finances_router
from api.config import ALGORITHM, GITHUB_ACCESS_TOKEN, OPT_KEY, SECRET_KEY
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
    asyncio.create_task(github_client.get_repos())
    app.state.tokens = []
    app.state.ticktick_client = ticktick_client
    app.state.crypto_rank_client = crypto_rank_client
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
