import streamlit as st
import pandas as pd
import httpx
from dateutil import parser
from datetime import datetime
from config import BASE_API_URL
import calendar
from icecream import ic
import altair as alt


def get_subscriptions():
    r_data = httpx.get(BASE_API_URL + "finances/subscriptions", timeout=10)
    r_json = r_data.json()
    return r_json


def get_crypto_data():
    r_data = httpx.get(BASE_API_URL + "crypto/all", timeout=10)
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


def get_all_symbols():
    r_data = httpx.get(BASE_API_URL + "crypto/all_tickers", timeout=30)
    r_json = r_data.json()
    return r_json


def main():
    st.set_page_config(page_title="money", page_icon="💵", layout="wide")

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
    st.header("Crypto")
    crypto_symbols = get_all_symbols()
    exchanges = crypto_symbols.keys()
    symbols = []
    for k in crypto_symbols.keys():
        symbols = symbols + crypto_symbols[k]

    symbol_option = st.selectbox("Symbol", symbols)
    st.write(symbol_option)
    st.selectbox("Symbol", get_all_symbols())
    with st.spinner("Loading crypto..."):
        crypto_data = get_crypto_data()
        # remove cryptos already sold
        crypto_data = {k: v for k, v in crypto_data.items() if not v["sold euro"]}
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

            crypto_df["current investment percentage"] = (
                crypto_df["current investment value"]
                / crypto_df["current investment value"].sum()
            ) * 100

            crypto_df["initial investment percentage"] = (
                crypto_df["invested value"] / crypto_df["invested value"].sum()
            ) * 100

            col1, col2 = st.columns([1, 1])
            with col1:
                st.metric(
                    "Total invested value", f"€{totals_df['invested value'].values[0]}"
                )
                st.altair_chart(
                    alt.Chart(crypto_df)
                    .mark_arc()
                    .encode(theta="initial investment percentage", color="symbol", tooltip=["invested value", "symbol"])
                )

            with col2:
                st.metric(
                    "Total current investment value",
                    f"€{round(totals_df['current investment value'].values[0], 2)}",
                )
                st.altair_chart(
                    alt.Chart(crypto_df)
                    .mark_arc()
                    .encode(theta="current investment percentage", color="symbol", tooltip=["current investment value", "symbol"])
                )
            col1, col2 = st.columns([1, 1])
            with col1:
                st.metric("Total profit", f"€{totals_df['profit'].values[0]}")
            with col2:
                st.metric("Total profit %", f"{totals_df['profit %'].values[0]}%")
            st.dataframe(crypto_df.style.apply(profit, axis=1))


if __name__ == "__main__":
    main()
