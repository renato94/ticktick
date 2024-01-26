import streamlit as st
import pandas as pd
import calendar
from dateutil.parser import parse
from datetime import datetime
import httpx
from config import BASE_API_URL
import calendar
import altair as alt


def get_activities():
    r = httpx.get(
        BASE_API_URL + "garmin/activities",
        timeout=10,
    )
    r_json = r.json()
    return r_json


def show_current_month_activities():
    activities = get_activities()
    activities = [activities[k] for k in activities.keys()]
    activities_df = pd.DataFrame(activities)
    activities_df["Year"] = activities_df["Start Time"].apply(lambda x: parse(x).year)
    activities_df["Month"] = activities_df["Start Time"].apply(lambda x: parse(x).month)
    activities_df["Day"] = activities_df["Start Time"].apply(lambda x: parse(x).day)

    current_month = datetime.now().month
    current_year = datetime.now().year
    current_month_activities_df = activities_df[activities_df["Month"] == current_month]
    all_days_in_month = list(
        range(1, calendar.monthrange(current_year, current_month)[1] + 1)
    )
    # group by activity type and count the number of activities
    activities_per_day = {d: {"Total": 0} for d in all_days_in_month}
    for i, row in current_month_activities_df.iterrows():
        if row["Activity Type"] not in activities_per_day[row["Day"]].keys():
            activities_per_day[row["Day"]][row["Activity Type"]] = 1
        else:
            activities_per_day[row["Day"]][row["Activity Type"]] += 1
        activities_per_day[row["Day"]]["Total"] += 1

    grouped_activities_df = pd.DataFrame(activities_per_day).T
    grouped_activities_df["Day"] = grouped_activities_df.index

    st.altair_chart(
        alt.Chart(grouped_activities_df)
        .mark_bar()
        .encode(
            x=alt.X(
                "Day",
                sort=None,
                axis=alt.Axis(grid=False),
                scale=alt.Scale(domain=[all_days_in_month[0], all_days_in_month[-1]]),
            ),
            y=alt.Y("Total", axis=alt.Axis(title="Number of activities", grid=False)),
        ),
        use_container_width=True,
    )
