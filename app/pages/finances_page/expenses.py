import streamlit as st
import pandas as pd
import httpx
from datetime import datetime
from config import BASE_API_URL
import calendar


def get_subscriptions():
    r_data = httpx.get(BASE_API_URL + "finances/subscriptions", timeout=10)
    r_json = r_data.json()
    return r_json


def get_all_expenses_data():
    r_data = httpx.get(BASE_API_URL + "finances/all", timeout=100)
    r_json = r_data.json()
    return r_json


def get_current_expenses_data():
    r_data = httpx.get(BASE_API_URL + "finances/current", timeout=10)
    r_json = r_data.json()
    return r_json


def load_expenses():
    with st.spinner("Loading expenses..."):
        current_expenses_data = get_current_expenses_data()
        subscriptions_data = get_subscriptions()

        st.header(f"{calendar.month_name[datetime.now().month]} Expenses")

        current_expenses_df = pd.DataFrame(current_expenses_data)
        total_monthly_expenses = current_expenses_df["Total"].sum()

        st.subheader(f"Total: €{total_monthly_expenses}")
        st.bar_chart(current_expenses_df[["Date", "Total"]].set_index("Date"))

        with st.expander("Expand", expanded=False):
            st.dataframe(current_expenses_df)

        subscriptions_df = pd.DataFrame(subscriptions_data)
        monthly_subscriptions = subscriptions_df[
            subscriptions_df["Billing period"] == "monthly"
        ]

        st.header("Subscriptions")
        total_monthly_subscriptions = monthly_subscriptions["Solo Value"].sum()
        st.subheader(f"Total: €{total_monthly_subscriptions}")
        with st.expander("Expand", expanded=False):
            st.dataframe(subscriptions_df)
