from datetime import datetime
import streamlit as st
import httpx

from dateutil import parser
from config import BASE_API_URL
from icecream import ic


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


def todos_summary():
    tasks = get_ticktick_tasks()
    n_projects = len(tasks)
    cols = st.columns(n_projects)

    for p in tasks:
        with cols.pop():
            st.metric(label=p["project"]["name"], value=len(p["tasks"]))
