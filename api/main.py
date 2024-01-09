from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request
from icecream import ic
from api.ticktick import TickTickClient, router as ticktick_router
from api.garmin import router as garmin_router
from api.github_api import router as github_router

state = uuid4()

app = FastAPI(debug=True)

app.include_router(garmin_router)
app.include_router(ticktick_router)
app.include_router(github_router)


@app.on_event("startup")
async def startup_event():
    ticktick_client = TickTickClient()
    app.state.ticktick_client = ticktick_client


@app.get("/health")
def health_check():
    return {"status": "ok"}
