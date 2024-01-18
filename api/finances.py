from api.sheets import pull_sheet_data
from fastapi import APIRouter
import calendar
from api.config import SCOPES, SPREADSHEET_FINANCES_ID
import pandas as pd
from datetime import datetime
from icecream import ic

router = APIRouter(prefix="/finances", tags=["finances"])


@router.get("/all")
def get_all_finances():
    months = [calendar.month_name[i] for i in range(1, 13)]
    all_data_df = []
    for month in months:
        all_data_df.append(pull_sheet_data(SCOPES, SPREADSHEET_FINANCES_ID, month))
    return pd.concat(all_data_df).to_dict(orient="records")


@router.get("/current")
def get_current_finances():
    current_month = calendar.month_name[datetime.now().month]
    data_df = pull_sheet_data(SCOPES, SPREADSHEET_FINANCES_ID, current_month)
    data_df["Total"] = data_df["Total"].astype(float)
    return data_df.to_dict(orient="records")
