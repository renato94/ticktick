import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import Depends, FastAPI, Request
from icecream import ic
import jwt
from api.crypto_rank import CryptoRankClient
from api.ticktick import TickTickClient, router as ticktick_router
from api.garmin import router as garmin_router
from api.github_api import GitHubClient, router as github_router
from api.crypto_rank import router as crypto_router
from api.finances import router as finances_router
from api.config import ALGORITHM, GITHUB_ACCESS_TOKEN, OPT_KEY, SECRET_KEY
from fastapi import BackgroundTasks
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
    # asyncio.create_task(github_client.get_repos())
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
        return {"error": "Invalid code"}


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=35)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(request: Request):
    authorization: str = request.headers.get("Authorization")
    token = authorization.split("Bearer ")[1].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        ic(payload)
        return payload
    except jwt.PyJWTError:
        ic("invalid token")
        return None


@app.get("/authenticated")
def authenticated(payload: dict = Depends(verify_token)):
    if payload:
        return {"authenticated": True}
    else:
        return {"authenticated": False}
