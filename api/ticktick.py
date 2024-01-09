from uuid import uuid4
from pydantic import BaseModel
from typing import List
from datetime import datetime
from api.config import TICKTICK_CLIENT_ID, TICKTICK_CLIENT_SECRET
from icecream import ic
import httpx
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/ticktick", tags=["ticktick"])


class Subtask(BaseModel):
    title: str
    startDate: datetime
    isAllDay: bool
    sortOrder: int
    timeZone: str
    status: int
    completedTime: datetime


class Task(BaseModel):
    title: str
    content: str
    desc: str
    isAllDay: bool
    startDate: datetime
    dueDate: datetime
    timeZone: str
    reminders: List[str]
    repeatFlag: str
    priority: int
    sortOrder: int
    items: List[Subtask]


class TickTickClient:
    base_url = "https://api.ticktick.com"
    code = None
    access_token = None

    scope = "tasks:write tasks:read projects:read projects:write"

    def set_access_token(self, access_token: str):
        self.access_token = access_token

    def set_code(self, code: str):
        self.code = code

    def get_redirect_url(self, state):
        """
        Get the access token.

        Args:
            code (str): Authorization code.

        Returns:
            dict: Access token information.
        """

        post_endpoint = "https://ticktick.com/oauth/authorize"
        # Make the API call to retrieve the access token
        parameters = {
            "client_id": TICKTICK_CLIENT_ID,
            "scope": "tasks:write tasks:read",
            "state": state,
            "redirect_uri": "http://localhost:9090/token",
            "response_type": "code",
        }
        r = httpx.get(post_endpoint, params=parameters)
        ic(r.status_code)
        ic(r.text)
        redirect_url = r.text.replace("Found. Redirecting to ", "")
        redirect_url = "https://ticktick.com" + redirect_url
        return redirect_url

    def get_access_token(self):
        """
        Get the access token.

        Args:
            authorization_token (str): Authorization token.

        Returns:
            dict: Access token information.
        """

        post_endpoint = "https://ticktick.com/oauth/token"
        # Make the API call to retrieve the access token
        parameters = {
            "client_id": TICKTICK_CLIENT_ID,
            "client_secret": TICKTICK_CLIENT_SECRET,
            "code": self.code,
            "scope": "tasks:write tasks:read",
            "grant_type": "authorization_code",
            "redirect_uri": "http://localhost:9090/token",
        }
        r = httpx.post(post_endpoint, params=parameters)
        ic(r.status_code)
        ic(r.text)
        return r.json()

    def get_user_projects(self):
        """
        Get the user's projects.

        Returns:
            dict: User's projects.
        """

        get_endpoint = "/open/v1/project"
        # Make the API call to retrieve the user's projects
        r = httpx.get(
            self.base_url + get_endpoint,
            headers={"Authorization": "Bearer " + self.access_token},
        )
        return r.json()

    def get_projects_data(self):
        projects = self.get_user_projects()
        projects_ids = [p["id"] for p in projects]
        tasks = []
        for project_id in projects_ids:
            get_endpoint = f"/open/v1/project/{project_id}/data"
            r = httpx.get(
                self.base_url + get_endpoint,
                headers={"Authorization": "Bearer " + self.access_token},
            )
            tasks.append(r.json())
        return tasks

    def get_task(self, project_id, task):
        pass


@router.get("/authenticate")
def get_redirect_url(request: Request):
    redirect_url = request.app.state.ticktick_client.get_redirect_url(state)
    ic(redirect_url)
    return {"success": True, "redirect_url": redirect_url}


@router.get("/token")
def get_token(request: Request):
    code = request.query_params.get("code")
    request.app.state.ticktick_client.set_code(code)
    access_token = request.app.state.ticktick_client.get_access_token()
    request.app.state.ticktick_client.set_access_token(access_token["access_token"])
    return {"success": True}


@router.get("/authenticated")
def get_tasks(request: Request):
    if not request.app.state.ticktick_client.access_token:
        raise HTTPException(401, "Not authenticated")
    else:
        return {"success": True}


@router.get("/tasks")
def get_project_data(request: Request):
    if not request.app.state.ticktick_client.access_token:
        raise HTTPException(401, "Not authenticated")
    else:
        tasks = request.app.state.ticktick_client.get_projects_data()
        return tasks
