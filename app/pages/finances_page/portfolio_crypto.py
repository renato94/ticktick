from typing import List
import streamlit as st
import pandas as pd
import httpx
from dateutil import parser
from datetime import datetime
from backend.api.models.crypto import ExchangeSymbols
from config import BASE_API_URL
import calendar
from icecream import ic
import altair as alt
import plotly.graph_objects as go
import plotly.express as px
import trendln


def get_crypto_data():
    r_data = httpx.get(BASE_API_URL + "crypto/all", timeout=10)
    r_json = r_data.json()
    return r_json


def get_crypto_account():
    account = st.session_state.get("account", None)
    if account is None:
        r_data = httpx.get(BASE_API_URL + "crypto/account", timeout=10)
        account = r_data.json()
        st.session_state["account"] = account
    return st.session_state["account"]


def get_all_symbols() -> List[ExchangeSymbols]:
    r_data = httpx.get(BASE_API_URL + "crypto/all_symbols", timeout=30)
    r_json = r_data.json()
    return [ExchangeSymbols(**e) for e in r_json]


def get_crypto_klines_data(exchange, symbol, pair, interval, start_date, end_date):
    r_data = httpx.get(
        BASE_API_URL + "crypto/klines",
        timeout=100,
        params={
            "exchange": exchange,
            "symbol": symbol,
            "pair": pair,
            "interval": interval,
            "start_at": start_date,
            "end_at": end_date,
        },
    )
    r_json = r_data.json()
    if r_json:
        return pd.read_json(r_json)
    return None

def get_trades():
    # get trades from st.session_state
    trades = st.session_state.get("trades", None)
    if trades is None:
        r_data = httpx.get(BASE_API_URL + "crypto/trades", timeout=10)
        r_json = r_data.json()
        trades = r_json
        st.session_state["trades"] = trades
    return trades

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


# plot all holdings klines in a single chart using line charts using plotty
def get_wallet_klines(crypto_accounts):
    for k, v in crypto_accounts.items():
        for symbol_name in crypto_accounts[k]:

            if "klines" in crypto_accounts[k][symbol_name]:

                x = []
                y = []
                for t in crypto_accounts[k][symbol_name]["trades"]:
                    if t["type"] == "BUY":
                        t_time = parser.parse(t["time"]).timestamp()
                        klines = crypto_accounts[k][symbol_name]["klines"]
                        klines_time = crypto_accounts[k][symbol_name]["klines"][
                            "time"
                        ].apply(lambda x: datetime.fromtimestamp(x))
                        closest_time = klines_time.iloc[
                            (klines_time - datetime.fromtimestamp(t_time))
                            .abs()
                            .argsort()[0]
                        ]
                        # get close time at closest time
                        close_closest_time = klines[klines["time"] == closest_time][
                            "close"
                        ]

                        x.append(close_closest_time)
                        y.append(0)

                # plot candlestick chart
                fig = go.Figure(
                    data=[
                        go.Candlestick(
                            x=crypto_accounts[k][symbol_name]["klines"]["time"].apply(
                                lambda x: datetime.fromtimestamp(x)
                            ),
                            open=crypto_accounts[k][symbol_name]["klines"]["open"],
                            high=crypto_accounts[k][symbol_name]["klines"]["high"],
                            low=crypto_accounts[k][symbol_name]["klines"]["low"],
                            close=crypto_accounts[k][symbol_name]["klines"]["close"],
                            line=dict(width=1),
                            increasing_line_color="cyan",
                            decreasing_line_color="gray",
                        ),
                        go.Scatter(x=x, mode="markers", name="trades"),
                    ]
                )
                # add the trades to the chart
                # the y should be equal to the close time and the x should be the time of the trade
                # for each trade fetch the time of the trade and get the closest time in the klines

            st.plotly_chart(fig, theme="streamlit", use_container_width=True)


def load_crypto_portfolio():
    st.header("Portfolio")
    # st.header("Crypto")

    # crypto_data = get_crypto_data()
    # # remove cryptos already sold
    # crypto_data = {k: v for k, v in crypto_data.items() if not v["sold euro"]}
    # plot_holdings(crypto_data)
    trades = get_trades()
    min_date = datetime.now()

    # st.write(trades)
    crypto_accounts = get_crypto_account()
    ic(crypto_accounts)
    for k, v in crypto_accounts.items():
        for symbol_name in crypto_accounts[k]:
            crypto_accounts[k][symbol_name]["exchange"] = k
            crypto_accounts[k][symbol_name]["symbol"] = symbol_name
            crypto_accounts[k][symbol_name]["exchange_symbol"] = (
                symbol_name + "USDT" if k == "mexc" else symbol_name + "-USDT"
            )
            if symbol_name in trades[k]["balances"]:
                symbol_trades = trades[k]["balances"][symbol_name]["trades"]
                crypto_accounts[k][symbol_name]["trades"] = symbol_trades
                start_date = parser.parse(symbol_trades[0]["time"]) - pd.Timedelta(
                    days=1
                )
                if start_date < min_date:
                    min_date = start_date

                crypto_accounts[k][symbol_name]["start_date"] = start_date
                crypto_accounts[k][symbol_name]["end_date"] = datetime.now()

    crypto_symbols: List[ExchangeSymbols] = get_all_symbols()
    args_dict = dict()
    for s in crypto_symbols:
        args_dict[s.exchange] = {}
        args_dict[s.exchange]["symbols"] = s.symbols
        args_dict[s.exchange]["intervals"] = s.intervals

    def update_symbols_and_intervals():
        st.session_state["symbols"] = [
            s.symbol for s in args_dict[st.session_state["exchange"]]["symbols"]
        ]
        # st.session_state["pairs"] = args_dict[st.session_state["exchange"]]["pairs"]
        st.session_state["intervals"] = args_dict[st.session_state["exchange"]][
            "intervals"
        ]
        st.session_state["pairs"] = []
        ic(st.session_state["symbols"])
        ic(st.session_state["intervals"])

    def update_pairs(default_symbol=None):
        pairs = []
        for s in crypto_symbols:
            if s.exchange == st.session_state["exchange"]:
                for sp in s.symbols:
                    if "symbol" not in st.session_state.keys():
                        st.session_state["symbol"] = default_symbol
                    if sp.symbol == st.session_state["symbol"]:
                        st.session_state["pairs"] = sp.pairs

        ic(st.session_state["pairs"])

    exchange_option = st.selectbox(
        "Exchange",
        list(args_dict.keys()),
        key="exchange",
        on_change=update_symbols_and_intervals,
    )
    update_symbols_and_intervals()
    default_symbol = st.session_state["symbols"][0]
    update_pairs(default_symbol)

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        symbol_option = st.selectbox(
            "Symbol",
            st.session_state["symbols"],
            key="symbol",
            index=5,
            on_change=update_pairs,
        )
    with col2:
        pair_option = st.selectbox(
            "Pair", st.session_state["pairs"], key="pair", index=0
        )
    with col3:
        interval = st.selectbox(
            "interval",
            st.session_state["intervals"],
        )

    default_start_time = datetime.now() - pd.Timedelta(days=30)
    col1, col2 = st.columns([1, 1])
    with col1:
        start_time = st.date_input("start time", default_start_time)
    with col2:
        end_time = st.date_input("end time", max_value=datetime.now())

    submitted = st.button("Submit")
    if submitted:
        start_date = int(datetime.combine(start_time, datetime.min.time()).timestamp())
        end_date = int(datetime.combine(end_time, datetime.min.time()).timestamp())

        df = get_crypto_klines_data(
            exchange_option, symbol_option, pair_option, interval, start_date, end_date
        )
        if df is None:
            st.error("No data found")
            return
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=df["time"].apply(lambda x: datetime.fromtimestamp(x)),
                    open=df["open"],
                    high=df["high"],
                    low=df["low"],
                    close=df["close"],
                    line=dict(width=1),
                    increasing_line_color="cyan",
                    decreasing_line_color="gray",
                ),
            ]
        )
        # get trades for symbol
        if exchange_option in crypto_accounts:
            # means symbol is in the account
            symbol_trades = crypto_accounts[exchange_option][symbol_option]["trades"]

            # aggregate trades by timedelta
            def aggregate_trades(trades, timedelta):
                trades_df = pd.DataFrame(trades)
                trades_df["time"] = pd.to_datetime(trades_df["time"])
                trades_df = trades_df.set_index("time")
                trades_df = trades_df.resample(timedelta).sum(numeric_only=True)
                return trades_df

            trades_df = aggregate_trades(symbol_trades, "1H")
            st.metric("Total trades", f"${len(trades_df)}")

            # drop all trades where filled_ammout == 0
            trades_df = trades_df[trades_df["filled_ammount"] != 0]

            st.dataframe(trades_df)
            df = df.astype(
                {
                    "time": "int",
                    "open": "float64",
                    "high": "float64",
                    "low": "float64",
                    "close": "float64",
                }
            )
            # calculate closest kline to trade
            point_x = []
            point_y = []
            # ic(df['time'])
            for t in trades_df.index:
                ic(int(t.timestamp()))
                closest_time = df["time"].iloc[
                    (df["time"] - int(t.timestamp())).abs().argsort()[0]
                ]
                ic(closest_time)

                closest_close = df[df["time"] == closest_time]["close"].values[0]
                ic(closest_close)
                point_x.append(closest_time)
                point_y.append(closest_close)
            ic([datetime.fromtimestamp(pt) for pt in point_x])
            ic(point_y)
                
            fig.add_trace(
                go.Scatter(
                    x=[datetime.fromtimestamp(pt) for pt in point_x],
                    y=point_y,
                    mode="markers",
                    marker=dict(color="red", size=8),
                )
            )

        st.plotly_chart(fig, theme="streamlit", use_container_width=True)
        hist = df["close"].apply(lambda x: float(x))
        indexes = df["time"].values
        ic(type(hist), type(indexes))
        window = 10
        
        fig = trendln.plot_support_resistance(
            hist,  # as per h for calc_support_resistance
            # x-axis data formatter turning numeric indexes to display output
            # e.g. ticker.FuncFormatter(func) otherwise just display numeric indexes
            numbest=2,  # number of best support and best resistance lines to display
            fromwindows=True,  # draw numbest best from each window, otherwise draw numbest across whole range
            pctbound=0.1,  # bound trend line based on this maximum percentage of the data range above the high or below the low
            extmethod=trendln.METHOD_NUMDIFF,
            method=trendln.METHOD_NSQUREDLOGN,
            window=window,
            errpct=0.005,
            hough_prob_iter=10,
            sortError=False,
            accuracy=20,
        )
        st.plotly_chart(fig, theme="streamlit", use_container_width=True)

        mins, maxs = trendln.calc_support_resistance(
            hist,
            accuracy=20,
        )
        (minimaIdxs, pmin, mintrend, minwindows), (
            maximaIdxs,
            pmax,
            maxtrend,
            maxwindows,
        ) = (mins, maxs)
        ic(minimaIdxs, pmin, mintrend, minwindows)
        ic(maximaIdxs, pmax, maxtrend, maxwindows)

        # plot the minimum and maximum trend lines

        # st.plotly_chart(fig, theme="streamlit", use_container_width=True)
        # minimaIdxs - sorted list of indexes to the local minima
        # pmin - [slope, intercept] of average best fit line through all local minima points
        # mintrend - sorted list containing (points, result) for local minima trend lines
        # points - list of indexes to points in trend line
        # result - (slope, intercept, SSR, slopeErr, interceptErr, areaAvg)
        # slope - slope of best fit trend line
        # intercept - y-intercept of best fit trend line
        # SSR - sum of squares due to regression
        # slopeErr - standard error of slope
        # interceptErr - standard error of intercept
        # areaAvg - Reimann sum area of difference between best fit trend line
        #   and actual data points averaged per time unit
        # minwindows - list of windows each containing mintrend for that window

        # maximaIdxs - sorted list of indexes to the local maxima
        # pmax - [slope, intercept] of average best fit line through all local maxima points
        # maxtrend - sorted list containing (points, result) for local maxima trend lines
        # see for mintrend above

        # maxwindows - list of windows each containing maxtrend for that window
        # crypto_klines_df = pd.DataFrame(crypto_klines_data)
        # st.dataframe(crypto_klines_df)
        # st.line_chart(crypto_klines_df[["open", "close"]].set_index("open"))

    # st.dataframe(account_df)

    # st.metric("Total", f"${total}")
    # st.altair_chart(
    #     alt.Chart(account_df)
    #     .mark_arc()
    #     .encode(
    #         theta="percentage",
    #         color="symbol",
    #         tooltip=["balance usd", "symbol"],
    #     )
    # )
