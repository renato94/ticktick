import asyncio
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException
from icecream import ic

from backend.api import create_access_token, verify_token
from backend.api.exchanges_clients import KuCoinClient, MexcClient, CryptoRankClient
from backend.api.sheets import create_drive_folder, get_google_services
from backend.api.ticktick import TickTickClient, router as ticktick_router
from backend.api.garmin import router as garmin_router
from backend.api.github_api import GitHubClient, router as github_router
from backend.api.crypto import router as crypto_router
from backend.api.finances import router as finances_router
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

from fastapi.security import OAuth2PasswordBearer

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
        ic("creating base folder")
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
    drive_service, sheets_service = get_google_services(SCOPES)

    crypto_folder_id, garmin_folder_id = create_drive_main_folders(
        drive_service, DRIVE_BASE_FOLDER, DRIVE_CRYPTO_FOLDER, DRIVE_GARMIN_FOLDER
    )
    app.state.crypto_folder_id = crypto_folder_id
    app.state.garmin_folder_id = garmin_folder_id
    app.state.drive_service = drive_service
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
