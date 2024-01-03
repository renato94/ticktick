from googleapiclient.discovery import build
import pandas as pd
import pickle
import os.path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from api.config import DATA_TO_PULL, SCOPES, SPREADSHEET_ID


def gsheet_api_check(SCOPES):
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


def pull_sheet_data(SCOPES, SPREADSHEET_ID, DATA_TO_PULL):
    creds = gsheet_api_check(SCOPES)
    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()
    result = (
        sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=DATA_TO_PULL).execute()
    )
    values = result.get("values", [])

    if not values:
        print("No data found.")
    else:
        rows = (
            sheet.values()
            .get(spreadsheetId=SPREADSHEET_ID, range=DATA_TO_PULL)
            .execute()
        )
        data = rows.get("values")
        print("COMPLETE: Data copied")
        return data


def write_ticktick_task():
    pass


data = pull_sheet_data(SCOPES, SPREADSHEET_ID, DATA_TO_PULL)
df = pd.DataFrame(data[1:], columns=data[0])

print(df.columns)
