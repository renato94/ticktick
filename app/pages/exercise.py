import json
import streamlit as st
import gpxpy
import pandas as pd
import geopandas as gpd
import os
from dateutil.parser import parse
from datetime import timedelta
import httpx
from icecream import ic
from config import BASE_API_URL

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


def get_meta_activities(year, activity_df, activity_type):
    activities_df = activity_df[activity_df["Activity Type"] == activity_type]
    activities_df["Distance"] = activities_df["Distance (km)"].apply(to_float)

    start_date = activities_df["Start Time"].min()
    end_date = activities_df["Start Time"].max()

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

    calories = (activities_df["Calories"].apply(to_float)).mean()
    avg_heart_rate = (activities_df["Average Heart Rate (bpm)"].apply(to_float)).mean()
    max_heart_rate = (activities_df["Max. Heart Rate (bpm)"].apply(to_float)).max()
    return {
        "year": int(year),
        "number": len(activities_df.index),
        "total distance (km)": activities_df["Distance"].sum(),
        "total duration": str(
            timedelta(seconds=int(activities_df["Duration seconds"].sum()))
        ),
        "average heart rate": avg_heart_rate,
        "max heart rate": max_heart_rate,
        "average calories": calories,
        "start_date": start_date,
        "end_date": end_date,
    }


def get_agregated_activities(activities_df):
    unique_activities = activities_df["Activity Type"].unique()
    activities_df["Duration seconds"] = activities_df["Duration (h:m:s)"].apply(
        time_to_seconds
    )
    activities_df["Year"] = activities_df["Start Time"].apply(lambda x: parse(x).year)
    years = activities_df["Year"].unique()

    for activity_type in unique_activities:
        activities_df_per_year = []
        for year in years:
            activities_df_per_year.append(
                (year, activities_df[activities_df["Year"] == year])
            )

        activities_meta = []
        for year, activities_df in activities_df_per_year:
            activities_meta.append(
                get_meta_activities(year, activities_df, activity_type)
            )
        meta_df = pd.DataFrame(activities_meta)
        st.write(activity_type)
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
    ic(activity)
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
        activities_df = pd.DataFrame(activities)
        get_agregated_activities(activities_df)

        activities_ids = activities_df["Activity ID"].unique()
        activity = st.selectbox("Select activity", activities_ids)
        activity = get_single_activity(activity)
        activity_df = gpd.GeoDataFrame(activity["features"])
        ic(activity_df.columns)
        activity_df["latitude"] = activity_df["geometry"].apply(
            lambda x: x["coordinates"][1]
        )

        activity_df["longitude"] = activity_df["geometry"].apply(
            lambda x: x["coordinates"][0]
        )
        ic(activity_df.columns)
        st.map(activity_df, size=2)


if __name__ == "__main__":
    main()
