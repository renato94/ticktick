import trendln
from icecream import ic
import pandas as pd

# this will serve as an example for security or index closing prices, or low and high prices
import yfinance as yf  # requires yfinance - pip install yfinance
import matplotlib.pyplot as plt  # requires matplotlib - pip install matplotlib

tick = yf.Ticker("^GSPC")  # S&P500
# load historical market data
hist = pd.read_csv(
    "kucoin_BTC-USDT_ONE_HOUR_2023-08-01_2024-01-31.csv", sep=",", index_col=["time"]
)
ic(len(hist))
hist.rename(
    columns={
        "close": "Close",
        "high": "High",
        "time": "Time",
        "low": "Low",
        "open": "Open",
        "volume": "Volume",
    },
    inplace=True,
)
ic(hist.columns)

# hist = tick.history(period="max", rounding=True)
# (extremaIdxs_0, pmin, mintrend, minwindows), (
#     extremaIdxs_1,
#     pmax,
#     maxtrend,
#     maxwindows,
# ) = trendln.calc_support_resistance(hist[-100].Close, accuracy=4)
# ic(extremaIdxs_0, pmin, mintrend, minwindows)
# ic(extremaIdxs_1, pmax, maxtrend, maxwindows)
fig = trendln.plot_support_resistance(
    hist.Close, accuracy=4
)  # requires matplotlib - pip install matplotlib
plt.savefig("suppres.svg", format="svg")
plt.show()
plt.clf()  # clear figure
