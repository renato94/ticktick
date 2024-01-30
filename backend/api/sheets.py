from googleapiclient.discovery import build
import pickle
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from icecream import ic
import pandas as pd


def creeds_api_check(SCOPES):
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return creds


def create_drive_folder(drive_service, folder_name, parent_id=None):
    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        file_metadata["parents"] = [parent_id]
    file = drive_service.files().create(body=file_metadata, fields="id").execute()
    print(f'Folder ID: "{file.get("id")}".')
    return file.get("id")


def create_sheet(drive_service, folder_id, sheet_name):
    file_metadata = {
        "name": sheet_name,
        "parents": [folder_id],
        "mimeType": "application/vnd.google-apps.spreadsheet",
    }
    file = drive_service.files().create(body=file_metadata, fields="id").execute()
    print(f"Sheet ID: {file.get('id')}.")
    return file.get("id")


def move_file_to_folder(drive_service, file_id, folder_id):
    file = drive_service.files().get(fileId=file_id, fields="parents").execute()
    previous_parents = ",".join(file.get("parents"))
    # Move the file to the new folder
    file = (
        drive_service.files()
        .update(
            fileId=file_id,
            addParents=folder_id,
            removeParents=previous_parents,
            fields="id, parents",
        )
        .execute()
    )
    return file.get("parents")


def get_google_services(SCOPES):
    creds = creeds_api_check(SCOPES)
    drive_service = build("drive", "v3", credentials=creds)
    sheet_service = build("sheets", "v4", credentials=creds)
    return drive_service, sheet_service


def pull_sheet_data(sheet_service, SPREADSHEET_ID, DATA_TO_PULL) -> pd.DataFrame:
    sheet_service = sheet_service.spreadsheets()
    result = (
        sheet_service.values()
        .get(spreadsheetId=SPREADSHEET_ID, range=DATA_TO_PULL)
        .execute()
    )
    values = result.get("values", [])

    if not values:
        print("No data found.")
        return pd.DataFrame()
    else:
        rows = (
            sheet_service.values()
            .get(spreadsheetId=SPREADSHEET_ID, range=DATA_TO_PULL)
            .execute()
        )
        data = rows.get("values")
        print("COMPLETE: Data copied")
        columns = data[0]
        entries = data[1:]
        for entry in entries:
            remaining_cols = len(columns) - len(entry)
            entry.extend([""] * remaining_cols)
        return pd.DataFrame(entries, columns=columns)
