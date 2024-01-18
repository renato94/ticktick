from uuid import uuid4
from fastapi import FastAPI
from icecream import ic
from api.crypto_rank import CryptoRankClient
from api.ticktick import TickTickClient, router as ticktick_router
from api.garmin import router as garmin_router
from api.github_api import router as github_router
from api.crypto_rank import router as crypto_router
from api.finances import router as finances_router

state = uuid4()

app = FastAPI(debug=True)

app.include_router(garmin_router)
app.include_router(ticktick_router)
app.include_router(github_router)
app.include_router(crypto_router)
app.include_router(finances_router)


@app.on_event("startup")
async def startup_event():
    ticktick_client = TickTickClient()
    crypto_rank_client = CryptoRankClient()
    app.state.ticktick_client = ticktick_client
    app.state.crypto_rank_client = crypto_rank_client


@app.get("/health")
def health_check():
    return {"status": "ok"}
