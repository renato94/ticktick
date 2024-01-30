import streamlit as st
import pandas as pd
import httpx
from dateutil import parser
from datetime import datetime
from config import BASE_API_URL
import calendar
from icecream import ic
import altair as alt
import plotly.graph_objects as go


def calculate_support_resistance(df):
    sr = []
    n1 = 3
    n2 = 2
    for row in range(3, len(df) - n2):  # len(df)-n2
        if support(df, row, n1, n2):
            sr.append((row, df.low[row], 1))
        if resistance(df, row, n1, n2):
            sr.append((row, df.high[row], 2))
    print(sr)
    plotlist1 = [x[1] for x in sr if x[2] == 1]
    plotlist2 = [x[1] for x in sr if x[2] == 2]
    plotlist1.sort()
    plotlist2.sort()

    delta_merge_lines = 0.005
    for i in range(1, len(plotlist1)):
        if i >= len(plotlist1):
            break
        if abs(plotlist1[i] - plotlist1[i - 1]) <= delta_merge_lines:
            plotlist1.pop(i)

    for i in range(1, len(plotlist2)):
        if i >= len(plotlist2):
            break
        if abs(plotlist2[i] - plotlist2[i - 1]) <= delta_merge_lines:
            plotlist2.pop(i)
    return plotlist1, plotlist2


def support(df1, l, n1, n2):  # n1 n2 before and after candle l
    for i in range(l - n1 + 1, l + 1):
        if df1.low[i] > df1.low[i - 1]:
            return 0
    for i in range(l + 1, l + n2 + 1):
        if df1.low[i] < df1.low[i - 1]:
            return 0
    return 1


# support(df,46,3,2)


def resistance(df1, l, n1, n2):  # n1 n2 before and after candle l
    for i in range(l - n1 + 1, l + 1):
        if df1.high[i] < df1.high[i - 1]:
            return 0
    for i in range(l + 1, l + n2 + 1):
        if df1.high[i] > df1.high[i - 1]:
            return 0
    return 1


def get_subscriptions():
    r_data = httpx.get(BASE_API_URL + "finances/subscriptions", timeout=10)
    r_json = r_data.json()
    return r_json


def get_crypto_data():
    r_data = httpx.get(BASE_API_URL + "crypto/all", timeout=10)
    r_json = r_data.json()
    return r_json


def get_crypto_account():
    r_data = httpx.get(BASE_API_URL + "crypto/account", timeout=10)
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


def get_all_symbols():
    r_data = httpx.get(BASE_API_URL + "crypto/all_symbols", timeout=30)
    r_json = r_data.json()
    return r_json


def get_crypto_klines_data(exchange, symbol, interval, start_date, end_date):
    r_data = httpx.get(
        BASE_API_URL + "crypto/klines",
        timeout=100,
        params={
            "exchange": exchange,
            "symbol": symbol,
            "interval": interval,
            "start_at": start_date,
            "end_at": end_date,
        },
    )
    r_json = r_data.json()
    return pd.read_json(r_json)


def profit(s):
    return (
        ["background-color: green"] * len(s)
        if s["invested value"] < s["current investment value"]
        else ["background-color: red"] * len(s)
    )


def get_trades():
    r_data = httpx.get(BASE_API_URL + "crypto/trades", timeout=10)
    r_json = r_data.json()
    return r_json


def plot_holdings(crypto_data):
    with st.expander("Expand", expanded=False):
        crypto_df = pd.DataFrame(crypto_data).T

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
                .encode(
                    theta="initial investment percentage",
                    color="symbol",
                    tooltip=["invested value", "symbol"],
                )
            )

        with col2:
            st.metric(
                "Total current investment value",
                f"€{round(totals_df['current investment value'].values[0], 2)}",
            )
            st.altair_chart(
                alt.Chart(crypto_df)
                .mark_arc()
                .encode(
                    theta="current investment percentage",
                    color="symbol",
                    tooltip=["current investment value", "symbol"],
                )
            )
        col1, col2 = st.columns([1, 1])
        with col1:
            st.metric("Total profit", f"€{totals_df['profit'].values[0]}")
        with col2:
            st.metric("Total profit %", f"{totals_df['profit %'].values[0]}%")
        st.dataframe(crypto_df.style.apply(profit, axis=1))


def main():
    st.set_page_config(page_title="money", page_icon="💵", layout="wide")

    st.header("Crypto")
    crypto_symbols = get_all_symbols()
    symbols_options = []
    for k in crypto_symbols.keys():
        symbols_options = symbols_options + [f"{k}={c}" for c in crypto_symbols[k]]

    intervals = ["ONE_HOUR", "FOUR_HOURS", "ONE_DAY", "ONE_WEEK"]
    with st.form("my_form"):
        symbol_option = st.selectbox("Symbol", symbols_options)
        interval = st.selectbox("interval", intervals)
        start_time = st.date_input("start time")
        end_time = st.date_input("end time")
        submitted = st.form_submit_button("Submit")
        if submitted:
            start_date = int(
                datetime.combine(start_time, datetime.min.time()).timestamp()
            )
            end_date = int(datetime.combine(end_time, datetime.min.time()).timestamp())
            exchange = symbol_option.split("=")[0]
            symbol_option = symbol_option.split("=")[1]
            df = get_crypto_klines_data(
                exchange, symbol_option, interval, start_date, end_date
            )

            df = df.astype(
                {
                    "time": "int",
                    "open": "float64",
                    "high": "float64",
                    "low": "float64",
                    "close": "float64",
                }
            )
            ss, rr = calculate_support_resistance(df)
            ic(ss)
            ic(rr)
            fig = go.Figure(
                data=[
                    go.Candlestick(
                        x=df["time"].apply(lambda x: datetime.fromtimestamp(x)),
                        open=df["open"],
                        high=df["high"],
                        low=df["low"],
                        close=df["close"],
                        line=dict(width=1),
                    ),
                ]
            )
            # c = 0
            # while 1:
            #     if c > len(ss) - 1:
            #         fig.add_shape(
            #             type="line",
            #             x0=ss[c][0] - 3,
            #             y0=ss[c][1],
            #             x1=200,
            #             y1=ss[c][1],
            #             line=dict(
            #                 color="green",
            #                 width=1,
            #                 dash="dot",
            #             ),
            #         )
            #     c += 1
            # c = 0
            # while 1:
            #     if c > len(rr) - 1:
            #         fig.add_shape(
            #             type="line",
            #             x0=rr[c][0] - 3,
            #             y0=rr[c][1],
            #             x1=200,
            #             y1=rr[c][1],
            #             line=dict(
            #                 color="green",
            #                 width=1,
            #                 dash="dot",
            #             ),
            #         )
            #     c += 1
            st.plotly_chart(fig, theme="streamlit", use_container_width=True)

            # crypto_klines_df = pd.DataFrame(crypto_klines_data)
            # st.dataframe(crypto_klines_df)
            # st.line_chart(crypto_klines_df[["open", "close"]].set_index("open"))

    with st.spinner("Loading crypto..."):
        # crypto_data = get_crypto_data()
        # # remove cryptos already sold
        # crypto_data = {k: v for k, v in crypto_data.items() if not v["sold euro"]}
        # plot_holdings(crypto_data)
        trades = get_trades()
        for e in trades["dfs"]:
            st.dataframe(pd.read_json(e))

        st.write(trades["accounts"])
        crypto_accounts = get_crypto_account()
        holdings = []
        for k, v in crypto_accounts.items():
            for symbol_name in crypto_accounts[k]:
                crypto_accounts[k][symbol_name]["exchange"] = k
                crypto_accounts[k][symbol_name]["symbol"] = symbol_name

                holdings.append(crypto_accounts[k][symbol_name])
        account_df = pd.DataFrame(holdings)
        account_df = account_df.astype(
            {
                "balance": "float64",
                "price": "float64",
            }
        )
        account_df["balance usd"] = account_df["balance"] * account_df["price"]
        total = account_df["balance usd"].sum()
        account_df["percentage"] = (account_df["balance usd"] / total) * 100
        st.dataframe(account_df)

        st.metric("Total", f"${total}")
        st.altair_chart(
            alt.Chart(account_df)
            .mark_arc()
            .encode(
                theta="percentage",
                color="symbol",
                tooltip=["balance usd", "symbol"],
            )
        )
    # with st.spinner("Loading expenses..."):
    #     current_expenses_data = get_current_expenses_data()
    #     subscriptions_data = get_subscriptions()

    #     st.header(f"{calendar.month_name[datetime.now().month]} Expenses")

    #     current_expenses_df = pd.DataFrame(current_expenses_data)
    #     total_monthly_expenses = current_expenses_df["Total"].sum()
    #     st.subheader(f"Total: €{total_monthly_expenses}")
    #     st.bar_chart(current_expenses_df[["Date", "Total"]].set_index("Date"))
    #     with st.expander("Expand", expanded=False):
    #         st.dataframe(current_expenses_df)
    #     subscriptions_df = pd.DataFrame(subscriptions_data)
    #     monthly_subscriptions = subscriptions_df[
    #         subscriptions_df["Billing period"] == "monthly"
    #     ]
    #     st.header("Subscriptions")
    #     total_monthly_subscriptions = monthly_subscriptions["Solo Value"].sum()
    #     st.subheader(f"Total: €{total_monthly_subscriptions}")
    #     with st.expander("Expand", expanded=False):
    #         st.dataframe(subscriptions_df)


if __name__ == "__main__":
    main()
