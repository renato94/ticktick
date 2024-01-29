from googleapiclient.discovery import build
import pickle
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from icecream import ic
import pandas as pd


def gsheet_api_check(SCOPES):
    creds = None
    ic(os.path.exists("token.pickle"))
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


def pull_sheet_data(SCOPES, SPREADSHEET_ID, DATA_TO_PULL) -> pd.DataFrame:
    creds = gsheet_api_check(SCOPES)
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()
    result = (
        sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=DATA_TO_PULL).execute()
    )
    values = result.get("values", [])

    if not values:
        print("No data found.")
        return pd.DataFrame()
    else:
        rows = (
            sheet.values()
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