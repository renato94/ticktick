from datetime import datetime
import streamlit as st
import httpx
import streamlit_authenticator as stauth
from icecream import ic
import yaml
from yaml.loader import SafeLoader
from dateutil import parser
from config import BASE_API_URL

example_resp_todos = [
    {
        "project": {
            "id": "6593de1f8f082f0c35728454",
            "name": "Personal",
            "color": "#FF6161",
            "sortOrder": -1099511627776,
            "viewMode": "list",
            "kind": "TASK",
        },
        "tasks": [
            {
                "id": "65949d5021d08a5710d0c1b4",
                "projectId": "6593de1f8f082f0c35728454",
                "sortOrder": -3298534948864,
                "title": "Read 10 min",
                "content": "",
                "desc": "",
                "startDate": "2024-01-08T00:00:00.000+0000",
                "dueDate": "2024-01-08T00:30:00.000+0000",
                "timeZone": "Europe/Amsterdam",
                "isAllDay": False,
                "priority": 0,
                "repeatFlag": "RRULE:FREQ=DAILY;INTERVAL=1",
                "completedTime": "2024-01-05T06:56:14.000+0000",
                "status": 0,
            },
            {
                "id": "6593dec421d08a5710d0b956",
                "projectId": "6593de1f8f082f0c35728454",
                "sortOrder": -1099511627776,
                "title": "100 flex",
                "content": "",
                "startDate": "2024-01-09T23:00:00.000+0000",
                "dueDate": "2024-01-09T23:00:00.000+0000",
                "timeZone": "Europe/Amsterdam",
                "isAllDay": True,
                "priority": 0,
                "repeatFlag": "RRULE:FREQ=DAILY;INTERVAL=1",
                "status": 0,
                "columnId": "",
            },
            {
                "id": "6593e519016441602be4ce85",
                "projectId": "6593de1f8f082f0c35728454",
                "sortOrder": -1099511693312,
                "title": "Journal",
                "startDate": "2024-01-08T23:00:00.000+0000",
                "dueDate": "2024-01-08T23:00:00.000+0000",
                "timeZone": "Europe/Amsterdam",
                "isAllDay": True,
                "priority": 0,
                "repeatFlag": "RRULE:FREQ=DAILY;INTERVAL=1",
                "status": 0,
                "columnId": "",
            },
            {
                "id": "6593ec5621d08a5710d0bfb0",
                "projectId": "6593de1f8f082f0c35728454",
                "sortOrder": -4398046576640,
                "title": "Plan Acores trip",
                "content": "",
                "desc": "",
                "startDate": "2024-02-02T11:00:00.000+0000",
                "dueDate": "2024-02-10T11:30:00.000+0000",
                "timeZone": "Europe/Amsterdam",
                "isAllDay": False,
                "priority": 0,
                "reminders": ["TRIGGER:PT0S"],
                "status": 0,
            },
            {
                "id": "659c12f221d08a42ff4c47dc",
                "projectId": "6593de1f8f082f0c35728454",
                "sortOrder": -5497558204416,
                "title": "Change all the lightbulbs at home",
                "content": "",
                "startDate": "2024-01-07T23:00:00.000+0000",
                "dueDate": "2024-01-07T23:00:00.000+0000",
                "timeZone": "Europe/Amsterdam",
                "isAllDay": True,
                "priority": 0,
                "status": 0,
                "tags": [],
            },
        ],
        "columns": [],
    },
    {
        "project": {
            "id": "6593de258f082f0c357284bd",
            "name": "Work",
            "color": "#E6EA49",
            "sortOrder": -2199023255552,
            "viewMode": "list",
            "kind": "TASK",
        },
        "tasks": [
            {
                "id": "6593de9121d08a5710d0b901",
                "projectId": "6593de258f082f0c357284bd",
                "sortOrder": -1099511627776,
                "title": "1hr work study/project",
                "content": "",
                "startDate": "2024-01-09T23:00:00.000+0000",
                "dueDate": "2024-01-09T23:00:00.000+0000",
                "timeZone": "Europe/Amsterdam",
                "isAllDay": True,
                "priority": 0,
                "repeatFlag": "RRULE:FREQ=WEEKLY;WKST=SU;INTERVAL=1;BYDAY=TU,MO,WE,TH,FR",
                "status": 0,
                "columnId": "",
            },
            {
                "id": "6593deaf21d08a5710d0b918",
                "projectId": "6593de258f082f0c357284bd",
                "sortOrder": -2199023255552,
                "title": "",
                "content": "",
                "timeZone": "Europe/Amsterdam",
                "isAllDay": True,
                "priority": 0,
                "status": 0,
                "tags": [],
            },
            {
                "id": "659bf34221d08a42ff4c45ef",
                "projectId": "6593de258f082f0c357284bd",
                "sortOrder": -2199023255552,
                "title": "End of year review",
                "content": "",
                "desc": "",
                "startDate": "2024-01-09T14:00:00.000+0000",
                "dueDate": "2024-01-09T14:00:00.000+0000",
                "timeZone": "Europe/Amsterdam",
                "isAllDay": False,
                "priority": 0,
                "reminders": ["TRIGGER:PT0S"],
                "repeatFlag": "",
                "status": 0,
                "columnId": "",
            },
            {
                "id": "659bf35f21d08a42ff4c45fa",
                "projectId": "6593de258f082f0c357284bd",
                "sortOrder": -3298534883328,
                "title": "Lattice goal/cleanup",
                "content": "",
                "desc": "",
                "startDate": "2024-01-08T23:00:00.000+0000",
                "dueDate": "2024-01-08T23:00:00.000+0000",
                "timeZone": "Europe/Amsterdam",
                "isAllDay": True,
                "priority": 0,
                "status": 0,
            },
        ],
        "columns": [],
    },
]


def get_ticktick_tasks():
    r = httpx.get(BASE_API_URL + "ticktick/tasks")
    r_json = r.json()
    return r_json


def todos_content():
    tasks = get_ticktick_tasks()
    st.metric("All tasks", len(tasks))

    
    for p in tasks:
        project_name = p["project"]["name"] 
        project_tasks = []
        for t in p["tasks"]:
            project_tasks.append(t["title"])
        st.metric(label=project_name, value=len(project_tasks))
        st.table(project_tasks)

    todays_tasks = []
    for p in tasks:
        for t in p["tasks"]:
            if (
                "dueDate" in t.keys()
                and parser.parse(t["dueDate"]).date() == datetime.now().date()
            ):
                todays_tasks.append(t["title"])
    st.metric(label="Today's tasks", value=len(todays_tasks))
    st.table(todays_tasks)




def page_content():
    r_projects = httpx.get(BASE_API_URL + "ticktick/authenticated")
    ic(r_projects.status_code)
    if r_projects.status_code == 200:
        todos_content()

    else:
        r = httpx.get(BASE_API_URL + "ticktick/authenticate")
        redirect_url = r.json()["redirect_url"]
        st.warning("Please authenticate TickTick")
        redirect_button = st.link_button("TickTick redirect", url=redirect_url)
        if not redirect_button:
            st.stop()
        ic("rerunning")
        st.rerun()


def login_page():
    users_yaml = "app/users.yaml"
    with open(users_yaml) as file:
        config = yaml.load(file, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
        config["preauthorized"],
    )

    authenticator.login("Login", "main")
    if st.session_state["authentication_status"]:
        authenticator.logout("Logout", "main", key="unique_key")
        page_content()
    elif st.session_state["authentication_status"] is False:
        st.error("Username/password is incorrect")

    elif st.session_state["authentication_status"] is None:
        st.warning("Please enter your username and password")


def main():
    st.set_page_config(page_title="Todos", page_icon="📋")
    login_page()


if __name__ == "__main__":
    main()
