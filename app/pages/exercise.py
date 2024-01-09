import streamlit as st
import gpxpy
import pandas as pd
import geopandas as gpd
import os
from dateutil.parser import parse
from datetime import timedelta
import httpx

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


def get_meta_activities(year, activity_df):
    running_activities_df = activity_df[activity_df["Activity Type"] == "Running"]

    return {
        "year": int(year),
        "number of runs": len(running_activities_df.index),
        "total distance (km)": running_activities_df["Distance (km)"].sum(),
        "total duration": str(
            timedelta(seconds=int(running_activities_df["Duration seconds"].sum()))
        ),
        "start_date": str(parse(running_activities_df["Start Time"].min()).date()),
        "end_date": str(parse(running_activities_df["Start Time"].max()).date()),
    }


def get_execise_basic_view():
    activities_df = pd.read_csv(activities_csv_path)
    activities_df["Duration seconds"] = activities_df["Duration (h:m:s)"].apply(
        time_to_seconds
    )
    activities_df["Year"] = activities_df["Start Time"].apply(lambda x: parse(x).year)
    years = activities_df["Year"].unique()
    activities_df_per_year = []
    for year in years:
        activities_df_per_year.append(
            (year, activities_df[activities_df["Year"] == year])
        )

    activities_meta = []
    for year, activities_df in activities_df_per_year:
        activities_meta.append(get_meta_activities(year, activities_df))
    meta_df = pd.DataFrame(activities_meta, index=years)
    st.write(meta_df)


def update_activities():
    r = httpx.get(BASE_API_URL + "garmin/activities/update", timeout=10)
    r_json = r.json()
    if r_json["success"] is True:
        st.success("Update Garmin activities success")
    else:
        st.error("Update Garmin activities failed" + r_json["error"])


def main():
    st.set_page_config(page_title="exercise", page_icon="🏃")

    st.button("Refresh", on_click=update_activities)

   


if __name__ == "__main__":
    main()
