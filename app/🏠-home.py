import streamlit as st
from streamlit_extras.switch_page_button import switch_page
from streamlit_calendar import calendar as st_calendar
import httpx
from datetime import datetime
from domain.todos import todos_summary

from domain.exercise import show_current_month_activities
from domain.coding import plot_current_month_commits


def get_title():
    kanye_api = "https://api.kanye.rest/"
    r = httpx.get(kanye_api)
    st.title(str(datetime.now().date()))
    st.write(f"\"{r.json()['quote']}\"\n - Kanye West")


def main():
    st.set_page_config(page_title="Renato", page_icon="🔥", layout="wide")

    get_title()
    calendar_options = {
        "editable": False,
        "themeSystem": "standard",
        "selectable": False,
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "timeGridWeek,timeGridDay,dayGridMonth",
        },
        "slotMinTime": "06:00:00",
        "slotMaxTime": "23:00:00",
        "initialView": "timeGridDay",
        "allDaySlot": False,
        "businessHours": {
            "daysOfWeek": [1, 2, 3, 4, 5],
            "startTime": "08:00",
            "endTime": "18:00",
        },
    }

    calendar_events = [
        {
            "title": "Event 1",
            "start": str(datetime(2024, 1, 28, 8, 0)),
            "end": str(datetime(2024, 1, 28, 8, 30)),
            "backgroundColor": "red",
        },
        {
            "title": "Event 2",
            "start": str(datetime(2024, 1, 28, 8, 15)),
            "end": str(datetime(2024, 1, 28, 8, 45)),
        },
        {
            "title": "Event 2",
            "start": "2023-07-31T07:30:00",
            "end": "2023-07-31T10:30:00",
            "resourceId": "cycle4",
        },
        {
            "title": "Event 3",
            "start": "2023-07-31T10:40:00",
            "end": "2023-07-31T12:30:00",
            "resourceId": "cycle7",
        },
    ]
    custom_css = """
        .fc-event-past {
            opacity: 0.8;
        }
        .fc-event-time {
            font-style: italic;
        }
        .fc-event-title {
            font-weight: 700;
        }
        .fc-toolbar-title {
            font-size: 2rem;
        }
    """

    calendar = st_calendar(
        events=calendar_events, options=calendar_options, custom_css=custom_css
    )

    exercise_btn = st.button("➤ Exercise")
    show_current_month_activities()
    if exercise_btn:
        switch_page("exercise")
    st.divider()
    todo_btn = st.button("➤ Todos")
    todos_summary()
    if todo_btn:
        switch_page("todos")
    st.divider()

    codgin_btn = st.button("➤ Coding")
    plot_current_month_commits()

    if codgin_btn:
        switch_page("coding")
    st.divider()

    finances_btn = st.button("➤ Finance")
    if finances_btn:
        switch_page("finances")


if __name__ == "__main__":
    main()
