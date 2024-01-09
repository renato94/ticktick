import subprocess
import os
from fastapi import APIRouter
from icecream import ic
import csv
from api.config import (
    GARMIN_PASSWORD,
    GARMIN_USERNAME,
    GARMIN_EXPORT_PATH,
    GARMIN_ROOT_PROJECT,
)

router = APIRouter(prefix="/garmin", tags=["garmin"])


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
                ic(row)
                columns = row
                continue
            activities.append(row)
    activities_json = []
    for activity in activities:
        activity_json = {}
        for i_column, column in enumerate(columns):
            activity_json[column] = activity[i_column]
        activities_json.append(activity_json)
    return activities_json
