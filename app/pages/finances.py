import streamlit as st
import pandas as pd
import httpx
from dateutil import parser
from datetime import datetime
from config import BASE_API_URL
import calendar


def get_subscriptions():
    r_data = httpx.get(BASE_API_URL + "finances/subscriptions", timeout=10)
    r_json = r_data.json()
    return r_json


def get_crypto_data():
    r_data = httpx.get(BASE_API_URL + "crypto-rank/all", timeout=10)
    r_json = r_data.json()
    return r_json


def get_current_expenses_data():
    r_data = httpx.get(BASE_API_URL + "finances/current", timeout=10)
    r_json = r_data.json()
    return r_json


def get_all_expenses_data():
    r_data = httpx.get(BASE_API_URL + "finances/all", timeout=100)
    r_json = r_data.json()
    return r_json


def profit(s):
    return (
        ["background-color: green"] * len(s)
        if s["invested value"] < s["current investment value"]
        else ["background-color: red"] * len(s)
    )


def main():
    st.set_page_config(page_title="money", page_icon="💵", layout="wide")

    with st.spinner("Loading expenses..."):
        current_expenses_data = get_current_expenses_data()
        subscriptions_data = get_subscriptions()
        col1, col2 = st.columns([1, 1])
        with col1:
            st.header(f"{calendar.month_name[datetime.now().month]} Expenses")

            current_expenses_df = pd.DataFrame(current_expenses_data)
            total_monthly_expenses = current_expenses_df["Total"].sum()
            st.subheader(f"Total: €{total_monthly_expenses}")
            st.subheader("Total")
            with st.expander("Expand", expanded=False):
                st.dataframe(current_expenses_df)
        with col2:
            st.header("Subscriptions")
            subscriptions_df = pd.DataFrame(subscriptions_data)
            monthly_subscriptions = subscriptions_df[
                subscriptions_df["Billing period"] == "monthly"
            ]
            total_monthly_subscriptions = monthly_subscriptions["Solo Value"].sum()
            st.subheader(f"Total: €{total_monthly_subscriptions}")
            st.subheader("Total")
            with st.expander("Expand", expanded=False):
                st.dataframe(subscriptions_df)
    st.header("Crypto")
    with st.spinner("Loading crypto..."):
        crypto_data = get_crypto_data()
        with st.expander("Expand", expanded=False):
            crypto_df = pd.DataFrame(crypto_data).T
            totals_df = pd.DataFrame(
                {
                    "invested value": crypto_df["invested value"].sum(),
                    "current investment value": crypto_df[
                        "current investment value"
                    ].sum(),
                    "profit": crypto_df["current investment value"].sum()
                    - crypto_df["invested value"].sum(),
                    "profit %": round(
                        (
                            (
                                crypto_df["current investment value"].sum()
                                - crypto_df["invested value"].sum()
                            )
                            / crypto_df["invested value"].sum()
                        )
                        * 100,
                        2,
                    ),
                },
                index=[0],
            )
            st.dataframe(totals_df.style.apply(profit, axis=1))
            st.dataframe(crypto_df.style.apply(profit, axis=1))


if __name__ == "__main__":
    main()
