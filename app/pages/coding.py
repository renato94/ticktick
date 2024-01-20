import httpx
import streamlit as st
import streamlit_calendar
from streamlit_card import card
from config import BASE_API_URL

repos = None


def get_github_user():
    r = httpx.get(BASE_API_URL + "github/user")
    return r.json()


def get_github_repos():
    r_repos = httpx.get(BASE_API_URL + "github/repos")
    return r_repos.json()

def main():
    st.set_page_config(page_title="coding", page_icon="💻")
    user = get_github_user()
    card(
        title=user["name"],
        text=user["bio"],
        image=user["avatar_url"],
        url=user["html_url"],
    )
    repos = get_github_repos()
    st.write(repos)


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
