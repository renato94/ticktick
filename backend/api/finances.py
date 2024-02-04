from backend.api.sheets import pull_sheet_data
from fastapi import APIRouter, Depends, Request
import calendar
from backend.config import SCOPES, SPREADSHEET_FINANCES_ID
import pandas as pd
from datetime import datetime

router = APIRouter(prefix="/finances", tags=["finances"])


def get_sheet_service(request: Request):
    return request.app.state.sheets_service


@router.get("/subscriptions")
def get_subscriptions(
    sheet_service=Depends(get_sheet_service),
):
    data_df = pull_sheet_data(sheet_service, SPREADSHEET_FINANCES_ID, "subscriptions")
    data_df["Total Value"] = data_df["Total Value"].astype(float)
    data_df["Solo Value"] = data_df["Solo Value"].astype(float)
    return data_df.to_dict(orient="records")


@router.get("/current")
def get_current_finances(
    sheet_service=Depends(get_sheet_service),
):
    data_df = pull_sheet_data(sheet_service, SPREADSHEET_FINANCES_ID, "Expenses")
    data_df["Total"] = data_df["Total"].astype(float)
    return data_df.to_dict(orient="records")
