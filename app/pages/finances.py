import streamlit as st
import pandas as pd
import httpx
from config import BASE_API_URL


def get_crypto_data():
    r_data = httpx.get(BASE_API_URL + "crypto-rank/all", timeout=10)
    r_json = r_data.json()
    return r_json


def get_current_expenses_data():
    r_data = httpx.get(BASE_API_URL + "finances/current", timeout=10)
    r_json = r_data.json()
    return r_json


def profit(s):
    return (
        ["background-color: green"] * len(s)
        if s["invested value"] < s["current investment value"]
        else ["background-color: red"] * len(s)
    )


def main():
    st.set_page_config(page_title="money", page_icon="💵")
    current_expenses_data = get_current_expenses_data()
    current_expenses_df = pd.DataFrame(current_expenses_data)
    total_monthly_expenses = current_expenses_df["Total"].sum()

    data = get_crypto_data()

    crypto_df = pd.DataFrame(data).T

    st.header("Monthly Expenses")
    st.subheader(f"Total: ${total_monthly_expenses}")
    st.dataframe(current_expenses_df)
    st.header("Subscriptions")

    st.header("Crypto")
    totals_df = pd.DataFrame(
        {
            "invested value": crypto_df["invested value"].sum(),
            "current investment value": crypto_df["current investment value"].sum(),
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
