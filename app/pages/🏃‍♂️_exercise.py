import json
import streamlit as st
import gpxpy
import pandas as pd
import geopandas as gpd
import calendar
from dateutil.parser import parse
from datetime import timedelta
import httpx
from icecream import ic
from domain.exercise import get_activities
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


def try_division(x, y, val=0.0):
    try:
        return x / y
    except ZeroDivisionError:
        return val


def show_activities(activities_df):
    activity_options = {
        f'{a["Activity Type"]} - {a["Start Time"]}': a["Activity ID"]
        for _, a in activities_df.iterrows()
    }
    activity = st.selectbox("Select activity", activity_options.keys())
    activity_id = activity_options[activity]
    activity = get_single_activity(activity_id)
    try:
        activity_df = gpd.GeoDataFrame(activity["features"])
        activity_df["latitude"] = activity_df["geometry"].apply(
            lambda x: x["coordinates"][1]
        )
        activity_df["longitude"] = activity_df["geometry"].apply(
            lambda x: x["coordinates"][0]
        )
        st.map(activity_df, size=1)
    except Exception:
        st.error("Cannot display activity GPS data")


def get_agregated_activities(activities_df):
    unique_activities = activities_df["Activity Type"].unique()

    years = activities_df["Year"].unique()
    year_option = st.selectbox("select year", years)
    activity_option = st.selectbox(label="activity option", options=unique_activities)
    activities_meta = []
    act_df = activities_df[activities_df["Activity Type"] == activity_option]
    act_df = act_df[act_df["Year"] == year_option]

    show_activities(act_df)

    activities_meta.append(get_meta_activities(year_option, act_df, activity_option))
    meta_df = pd.DataFrame(activities_meta)

    # Group by month and count the number of activities
    act_df["Date"] = pd.to_datetime(act_df["Start Time"])

    monthly_dict = {
        month: {
            "Number of activities": 0,
            "Calories": 0,
            "Sum Heart Rate": 0,
            "Duration": 0,
            "Distance": 0,
        }
        for month in range(1, 13)
    }

    for _, row in act_df.iterrows():
        monthly_dict[row["Month"]]["Number of activities"] += 1
        monthly_dict[row["Month"]]["Calories"] += row["Calories"]
        monthly_dict[row["Month"]]["Sum Heart Rate"] += row["Average Heart Rate (bpm)"]
        monthly_dict[row["Month"]]["Duration"] += row["Duration seconds"]
        monthly_dict[row["Month"]]["Distance"] += row["Distance"]

    for month in monthly_dict.keys():
        monthly_dict[month]["Average Heart Rate"] = try_division(
            monthly_dict[month]["Sum Heart Rate"],
            monthly_dict[month]["Number of activities"],
        )
        monthly_dict[month]["Average Calories"] = try_division(
            monthly_dict[month]["Calories"], monthly_dict[month]["Number of activities"]
        )
        monthly_dict[month]["Average Duration"] = str(
            timedelta(
                seconds=int(
                    try_division(
                        monthly_dict[month]["Duration"],
                        monthly_dict[month]["Number of activities"],
                    )
                )
            )
        )
        monthly_dict[month]["Average Distance"] = try_division(
            monthly_dict[month]["Distance"], monthly_dict[month]["Number of activities"]
        )
        monthly_dict[month]["Month"] = calendar.month_name[month]

    monthly_df = pd.DataFrame(monthly_dict.values())
    monthly_df["Duration"] = monthly_df["Duration"].apply(
        lambda x: str(timedelta(seconds=int(x)))
    )
    st.altair_chart(
        alt.Chart(monthly_df)
        .mark_bar()
        .encode(
            x=alt.X("Month", sort=None),
            y="Number of activities",
            tooltip=[
                "Duration",
                "Average Duration",
                "Average Heart Rate",
                "Average Calories",
            ],
        ),
        use_container_width=True,
    )

    st.write(activity_option)
    st.write(meta_df)


def update_activities():
    r = httpx.get(
        BASE_API_URL + "garmin/activities/update",
        timeout=10,
    )
    r_json = r.json()
    if r_json["success"] is True:
        st.success("Update Garmin activities success")
    else:
        st.error("Update Garmin activities failed" + r_json["error"])


def get_single_activity(activity):
    if activity is None:
        return None
    r = httpx.get(BASE_API_URL + f"garmin/activities/{activity}", timeout=10)
    r_json = r.json()
    activity_json = json.loads(r_json)
    return activity_json


def verify_code(code):
    r = httpx.get(BASE_API_URL + f"verify/{code}", timeout=10)
    r_json = r.json()
    return r_json


def load_exercise_page():
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


@st.cache_data(experimental_allow_widgets=True)
def my_access_token(opt_code):
    r = httpx.get(BASE_API_URL + f"otp/{opt_code}", timeout=10)
    if r.status_code != 200:
        return None
    r_json = r.json()
    return r_json["access_token"]


def main():
    st.set_page_config(page_title="exercise", page_icon="🏃", layout="wide")
    load_exercise_page()


if __name__ == "__main__":
    main()
