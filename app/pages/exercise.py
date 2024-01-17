import json
import streamlit as st
import gpxpy
import pandas as pd
import geopandas as gpd
import os
import calendar
from dateutil.parser import parse
from datetime import timedelta
import httpx
from icecream import ic
from config import BASE_API_URL
import calendar
import altair as alt

base_gpx_path = "garmin-connect-export/2024-01-02_garmin_connect_export"
activities_csv_path = base_gpx_path + "/activities.csv"


def gpx_to_geopandas(gpx_file_path):
    gpx_file = open(gpx_file_path, "r")
    gpx = gpxpy.parse(gpx_file)

    data = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                data.append([point.latitude, point.longitude])

    df = pd.DataFrame(data, columns=["Latitude", "Longitude"])
    df.rename(columns={"Latitude": "latitude", "Longitude": "longitude"}, inplace=True)
    # Convert DataFrame to GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.longitude, df.latitude))

    return gdf


def time_to_seconds(time_str):
    dt = parse(time_str)
    total_seconds = dt.hour * 3600 + dt.minute * 60 + dt.second
    return total_seconds


def to_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def get_meta_activities(year, act_df, activity_type):
    calories = (act_df["Calories"].apply(to_float)).mean()

    avg_heart_rate = act_df["Average Heart Rate (bpm)"].mean()
    max_heart_rate = act_df["Max. Heart Rate (bpm)"].max()

    start_date = act_df["Start Time"].min()
    end_date = act_df["Start Time"].max()

    start_date = (
        parse(start_date).date()
        if start_date and isinstance(start_date, float) is False
        else None
    )
    end_date = (
        parse(end_date).date()
        if end_date and isinstance(end_date, float) is False
        else None
    )

    return {
        "year": int(year),
        "number": len(act_df.index),
        "total distance (km)": act_df["Distance"].sum(),
        "total duration": str(timedelta(seconds=int(act_df["Duration seconds"].sum()))),
        "average heart rate": avg_heart_rate,
        "max heart rate": max_heart_rate,
        "average calories": calories,
        "start_date": start_date,
        "end_date": end_date,
    }


def get_agregated_activities(activities_df):
    unique_activities = activities_df["Activity Type"].unique()

    years = activities_df["Year"].unique()
    year_option = st.selectbox("select year", years)
    activity_option = st.selectbox(label="activity option", options=unique_activities)
    activities_meta = []
    act_df = activities_df[activities_df["Activity Type"] == activity_option]
    act_df = act_df[act_df["Year"] == year_option]

    activities_meta.append(get_meta_activities(year_option, act_df, activity_option))
    meta_df = pd.DataFrame(activities_meta)

    # Group by month and count the number of activities
    act_df["Date"] = pd.to_datetime(act_df["Start Time"])
    act_df["Number of activities"] = act_df.groupby("Month")["Activity Type"].transform(
        "count"
    )

    # Sum the remaining columns
    act_df = act_df.groupby("Month").sum(numeric_only=True).reset_index()
    st.write(
        alt.Chart(act_df)
        .mark_bar()
        .encode(
            x="Month:O",
            y="Number of activities",
            tooltip=["Month", "Number of activities"],
        )
    )

    st.write(activity_option)
    st.write(meta_df)


def update_activities():
    r = httpx.get(BASE_API_URL + "garmin/activities/update", timeout=10)
    r_json = r.json()
    if r_json["success"] is True:
        st.success("Update Garmin activities success")
    else:
        st.error("Update Garmin activities failed" + r_json["error"])


def get_activities():
    r = httpx.get(BASE_API_URL + "garmin/activities", timeout=10)
    r_json = r.json()
    return r_json


def get_single_activity(activity):
    if activity is None:
        return None
    r = httpx.get(BASE_API_URL + f"garmin/activities/{activity}", timeout=10)
    r_json = r.json()
    activity_json = json.loads(r_json)
    return activity_json


def main():
    st.set_page_config(page_title="exercise", page_icon="🏃")

    st.button("Refresh", on_click=update_activities)

    with st.spinner("Loading activities..."):
        activities = get_activities()
        activities = [activities[k] for k in activities.keys()]
        activities_df = pd.DataFrame(activities)
        st.write("All Activities")
        activities_df["Year"] = activities_df["Start Time"].apply(
            lambda x: parse(x).year
        )
        activities_df["Month"] = activities_df["Start Time"].apply(
            lambda x: parse(x).month
        )

        activities_df["Distance"] = activities_df["Distance (km)"].apply(to_float)
        activities_df["Calories"] = activities_df["Calories"].apply(to_float)
        activities_df = activities_df.astype(
            {
                "Average Heart Rate (bpm)": int,
                "Max. Heart Rate (bpm)": int,
            }
        )
        activities_df["Duration seconds"] = activities_df["Duration (h:m:s)"].apply(
            time_to_seconds
        )

        year_col = activities_df.pop("Year")
        activities_df.insert(0, "Year", year_col)

        month_col = activities_df.pop("Month")
        activities_df.insert(1, "Month", month_col)
        st.write(activities_df)
        get_agregated_activities(activities_df)

        activities_ids = activities_df["Activity ID"].unique()
        activity = st.selectbox("Select activity", activities_ids)
        activity = get_single_activity(activity)
        activity_df = gpd.GeoDataFrame(activity["features"])
        activity_df["latitude"] = activity_df["geometry"].apply(
            lambda x: x["coordinates"][1]
        )
        activity_df["longitude"] = activity_df["geometry"].apply(
            lambda x: x["coordinates"][0]
        )
        st.map(activity_df, size=1)


if __name__ == "__main__":
    main()
