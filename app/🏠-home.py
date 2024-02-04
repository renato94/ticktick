from dataclasses import dataclass
import uuid
import altair
import pandas as pd
import streamlit as st
from streamlit_extras.switch_page_button import switch_page
from streamlit_calendar import calendar as st_calendar
import httpx
from datetime import datetime
from domain.todos import todos_summary
import calendar
from domain.exercise import show_current_month_activities
from domain.coding import plot_current_month_commits
from icecream import ic

import plotly.graph_objects as go


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
        "slotMaxTime": "24:00:00",
        "initialView": "timeGridWeek",
        "allDaySlot": False,
        # "businessHours": {
        #     "daysOfWeek": [1, 2, 3, 4, 5],
        #     "startTime": "06:00",
        #     "endTime": "18:00",
        # },
    }

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
        .fc-event-complete{
            text-decoration: line-through;
            background-color: #f0f0f0;
        }
    """

    @dataclass
    class CalendarEvent:
        id: uuid.UUID
        title: str
        start: datetime
        end: datetime
        color: str = None
        type: str = "general"

        def __post_init__(self):
            self.color = event_types[self.type]["color"]
            self.duration_seconds = self.calculate_duration()

        def calculate_duration(self):
            if self.end < self.start:
                return (self.start - self.end).total_seconds()
            else:
                return (self.end - self.start).total_seconds()

        def dict(self):
            return {
                "title": self.title,
                "start": str(self.start),
                "end": str(self.end),
                "backgroundColor": self.color,
            }

    # generate a function that creates events during the month of February during the weekdays at 18:45 - 19:15:

    def generate_events(
        month_id,
        event_name,
        start_time,
        end_time,
        exclude_days=[],
        type="general",
    ):
        events = []
        start_time = datetime.strptime(start_time, "%H:%M")
        end_time = datetime.strptime(end_time, "%H:%M")
        for day in range(1, 29):
            if (
                calendar.day_name[datetime(2024, month_id, day).weekday()]
                in exclude_days
            ):
                continue
            events.append(
                CalendarEvent(
                    id=uuid.uuid4(),
                    title=event_name,
                    start=datetime(
                        2024, month_id, day, start_time.hour, start_time.minute
                    ),
                    end=datetime(2024, month_id, day, end_time.hour, end_time.minute),
                    type=type,
                )
            )
        return events

    event_types = {
        "general": {"color": "red"},
        "exercise": {"color": "green"},
        "commutes": {"color": "blue"},
        "projects": {"color": "orange"},
        "home": {"color": "purple"},
        "sleep": {"color": "black"},
    }
    boxing_events = generate_events(
        2,
        "Boxing",
        "18:45",
        "20:15",
        exclude_days=["Saturday", "Sunday", "Thursday", "Tuesday"],
        type="exercise",
    )
    wake_up_events = generate_events(
        2,
        "Wake up",
        "06:30",
        "06:45",
        exclude_days=["Sunday"],
        type="sleep",
    )
    work__morning_events = generate_events(
        2,
        "Work morning",
        "08:30",
        "11:00",
        exclude_days=["Saturday", "Sunday"],
    )

    work_afternoon_events = generate_events(
        2,
        "Work afternoon",
        "13:00",
        "17:00",
        exclude_days=["Saturday", "Sunday"],
    )
    lunch_events = generate_events(
        2,
        "Lunch",
        "12:30",
        "13:00",
        type="home",
    )
    gym_events = generate_events(
        2,
        "Gym",
        "7:00",
        "8:00",
        exclude_days=["Saturday", "Sunday"],
        type="exercise",
    )

    sleep_events = generate_events(
        2,
        "Sleep",
        "22:00",
        "23:59",
        type="sleep",
    ) + generate_events(
        2,
        "Sleep",
        "00:00",
        "06:30",
        type="sleep",
    )

    running_events = generate_events(
        2,
        "Running",
        "18:45",
        "20:15",
        exclude_days=["Monday", "Wednesday", "Friday", "Sunday"],
        type="exercise",
    )

    dinner_events = generate_events(
        2,
        "Dinner",
        "20:30",
        "21:00",
        type="home",
    )
    project_events = generate_events(
        2,
        "Project",
        "11:00",
        "12:00",
        exclude_days=["Sunday"],
        type="projects",
    )

    marks_events = generate_events(
        2,
        "Marks",
        "21:00",
        "22:00",
        exclude_days=["Monday", "Wednesday", "Friday", "Sunday"],
        type="projects",
    )
    prepare_meal_events = generate_events(
        2,
        "Prepare day",
        "17:30",
        "18:30",
        exclude_days=["Monday", "Wednesday", "Friday"],
        type="home",
    )
    
    calendar_events = (
        boxing_events
        + wake_up_events
        + work__morning_events
        + work_afternoon_events
        + lunch_events
        + gym_events
        + sleep_events
        + running_events
        + dinner_events
        + project_events
        + marks_events
        + prepare_meal_events
    )
    total_hours_per_event = {}
    for event in calendar_events:
        if event.title not in total_hours_per_event.keys():
            total_hours_per_event[event.title] = event.duration_seconds
        else:
            total_hours_per_event[event.title] += event.duration_seconds
    total_hours_per_event = {k: int(v / 3600) for k, v in total_hours_per_event.items()}
    months_hours = calendar.monthrange(2024, 2)[1] * 24
    free_hours = months_hours - sum(total_hours_per_event.values())
    # total_hours_per_event["month hours"] = months_hours
    total_hours_per_event["free hours"] = free_hours

    calendar_events = [event.dict() for event in calendar_events]
    col1, col2 = st.columns([3, 1])
    with col1:
        calendar_click_event = st_calendar(
            events=calendar_events, options=calendar_options, custom_css=custom_css
        )
    with col2:
        st.write(calendar_click_event)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=list(total_hours_per_event.keys()),
                values=list(total_hours_per_event.values()),
            )
        ],
        layout=go.Layout(
            title="Hours per activity",
            showlegend=False,
        ),
    )
    st.plotly_chart(fig)
    st.write(total_hours_per_event)

    exercise_btn = st.button("➤ Exercise")
    # show_current_month_activities()
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
