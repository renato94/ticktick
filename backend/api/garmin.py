from pathlib import Path
import subprocess
import os
from fastapi import APIRouter, Depends
import gpxpy
from icecream import ic
import csv
from backend.config import (
    GARMIN_PASSWORD,
    GARMIN_USERNAME,
    GARMIN_EXPORT_PATH,
    GARMIN_ROOT_PROJECT,
)
import pandas as pd
import geopandas as gpd

from backend.api import verify_token

router = APIRouter(prefix="/garmin", tags=["garmin"])


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


@router.get("/activities/update")
def update_latest_activites():
    if not os.path.exists(GARMIN_EXPORT_PATH):
        os.makedirs(GARMIN_EXPORT_PATH)

    # Run the gcexport.py CLI command to get the Garmin data
    command = [
        "python",
        os.path.join(GARMIN_ROOT_PROJECT, "gcexport.py"),
        "--username",
        GARMIN_USERNAME,
        "--password",
        GARMIN_PASSWORD,
        "--directory",
        GARMIN_EXPORT_PATH,
    ]
    result = subprocess.run(command)
    ic(result.stdout)

    if result.returncode == 0:
        return {"success": True}
    else:
        # Return an error message
        error = result.stderr
        return {"suceess": "False", "error": error}


@router.get("/activities")
def get_activities():
    activities = []

    # Path to the CSV file
    csv_file_path = os.path.join(GARMIN_EXPORT_PATH, "activities.csv")

    # Read the CSV file
    with open(csv_file_path, "r") as file:
        reader = csv.reader(file)
        for i_row, row in enumerate(reader):
            if i_row == 0:
                # Skip the header row
                columns = row
                continue
            activities.append(row)
    activities_json = {}
    for activity in activities:
        activity_json = {}
        for i_column, column in enumerate(columns):
            activity_json[column] = activity[i_column]
        activities_json[activity_json["Activity ID"]] = activity_json

    return activities_json


@router.get("/activities/{activity_id}")
def get_activity(activity_id):
    file_path = Path(GARMIN_EXPORT_PATH) / f"activity_{activity_id}.gpx"
    activity_df = gpx_to_geopandas(file_path)
    return activity_df.to_json()
