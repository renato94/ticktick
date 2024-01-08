from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request
from icecream import ic
from api.ticktick import TickTickClient

state = uuid4()

app = FastAPI(debug=True)


@app.get("/authenticate")
def get_redirect_url():
    redirect_url = app.state.ticktick_client.get_redirect_url(state)
    ic(redirect_url)
    return {"success": True, "redirect_url": redirect_url}


@app.get("/token")
def get_token(request: Request):
    code = request.query_params.get("code")
    app.state.ticktick_client.set_code(code)
    access_token = app.state.ticktick_client.get_access_token()
    app.state.ticktick_client.set_access_token(access_token["access_token"])
    return {"success": True}


@app.get("/authenticated")
def get_tasks():
    if not app.state.ticktick_client.access_token:
        raise HTTPException(401, "Not authenticated")
    else:
        return {"success": True}


@app.get("/tasks")
def get_project_data():
    if not app.state.ticktick_client.access_token:
        raise HTTPException(401, "Not authenticated")
    else:
        tasks = app.state.ticktick_client.get_projects_data()
        return tasks


@app.on_event("startup")
async def startup_event():
    # Create your TickTick client here
    # This is just a placeholder, replace with your actual client creation code
    ticktick_client = TickTickClient()
    app.state.ticktick_client = ticktick_client
