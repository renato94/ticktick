import httpx
import streamlit as st
import streamlit_calendar
from icecream import ic
from config import BASE_API_URL


def get_github_repos():
    r_repos = httpx.get(BASE_API_URL + "github/repos")
    n_repos = r_repos.json()["n_repos"]
    st.metric("Repositories", n_repos)
    timeout = 5 * n_repos
    with st.spinner("waiting"):
        r = httpx.get(BASE_API_URL + "github/repos/all", timeout=timeout)
    return r.json()


def main():
    st.set_page_config(page_title="coding", page_icon="💻")
    repos = get_github_repos()
    st.table(repos)

    calendar_options = {
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "resourceTimelineDay,resourceTimelineWeek,resourceTimelineMonth",
        },
        "slotMinTime": "06:00:00",
        "slotMaxTime": "18:00:00",
        "initialView": "resourceTimelineDay",
        "resourceGroupField": "building",
        "resources": [
            {"id": "a", "building": "Building A", "title": "Building A"},
            {"id": "b", "building": "Building A", "title": "Building B"},
            {"id": "c", "building": "Building B", "title": "Building C"},
            {"id": "d", "building": "Building B", "title": "Building D"},
            {"id": "e", "building": "Building C", "title": "Building E"},
            {"id": "f", "building": "Building C", "title": "Building F"},
        ],
    }
    calendar_events = [
        {
            "title": "Event 1",
            "start": "2023-07-31T08:30:00",
            "end": "2023-07-31T10:30:00",
            "resourceId": "a",
        },
        {
            "title": "Event 2",
            "start": "2023-07-31T07:30:00",
            "end": "2023-07-31T10:30:00",
            "resourceId": "b",
        },
        {
            "title": "Event 3",
            "start": "2023-07-31T10:40:00",
            "end": "2023-07-31T12:30:00",
            "resourceId": "a",
        },
    ]

    calendar_st = streamlit_calendar.calendar(
        events=calendar_events, options=calendar_options
    )
    st.write(calendar_st)


if __name__ == "__main__":
    main()
