import base64
from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
import json
import logging
import time
from enum import Enum
from typing import List
from fastapi import HTTPException

import httpx
from abc import ABC, abstractmethod
from backend.api.crypto_manager.account import Account, Balance, Trade
from backend.api.models.crypto import Kline, Symbol

from backend.config import CRYPTO_RANK_API_KEY, CRYPTO_RANK_BASE_ENDPOINT

import logging

logger = logging.getLogger(__name__)


class ExchangeClient(ABC):
    def __init__(
        self,
        id: int,
        api_key: str,
        api_secret: str,
        base_url: str,
        passphrase: str = None,
    ):
        self.id = id
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = str(base_url)
        self.passphrase = passphrase
        self.client = httpx.Client()

    @abstractmethod
    def prepare_headers(self, *args, **kwargs):
        pass

    def get(self, endpoint, headers: dict, params=None):
        return self.client.request(
            "GET", self.base_url + endpoint, params=params, headers=headers
        )

    def post(self, endpoint, headers: dict, params=None, json=None):
        return self.client.request(
            "POST",
            self.base_url + endpoint,
            params=params,
            headers=headers,
            json=json,
        )

    def map_interval(self, interval: str):
        for k in self.KLINE_INTERVALS:
            if k.value == interval:
                return k.name

    def calculate_expected_klines(self, start_date, end_date, interval) -> int:
        delta = datetime.fromtimestamp(start_date) - datetime.fromtimestamp(end_date)
        total_seconds = delta.total_seconds()
        logger.info(f"total_seconds {total_seconds}")
        expected_klines = delta.total_seconds() / 60
        match self.map_interval(interval):
            case GENERAL_KLINE_INTERVALS.ONE_HOUR.value:
                ek = expected_klines / 60
            case GENERAL_KLINE_INTERVALS.FOUR_HOURS.value:
                ek = expected_klines / 240
            case GENERAL_KLINE_INTERVALS.ONE_DAY.value:
                ek = expected_klines / 1440
            case GENERAL_KLINE_INTERVALS.ONE_WEEK.value:
                ek = expected_klines / 10080
            case _:
                raise HTTPException(400, "Invalid Interval")
        return int(ek)


class GENERAL_KLINE_INTERVALS(Enum):
    ONE_MINUTE = "ONE_MINUTE"
    FIVE_MINUTES = "FIVE_MINUTES"
    FIFTHEEN_MINUTES = "FIFTHEEN_MINUTES"
    THIRTHY_MINUTEs = "THIRTHY_MINUTEs"
    ONE_HOUR = "ONE_HOUR"
    FOUR_HOURS = "FOUR_HOURS"
    ONE_DAY = "ONE_DAY"
    ONE_WEEK = "ONE_WEEK"
    ONE_MONTH = "ONE_MONTH"


class MexcClient(ExchangeClient):
    class KLINE_INTERVALS(Enum):
        ONE_MINUTE = "1m"
        FIVE_MINUTES = "5m"
        FIFTHEEN_MINUTES = "15m"
        THIRTHY_MINUTEs = "30m"
        ONE_HOUR = "60m"
        FOUR_HOURS = "4h"
        ONE_DAY = "1d"
        ONE_WEEK = "1W"
        ONE_MONTH = "1M"

    def parse_mexc_account(self, df):
        account = Account(exchange="mexc")
        for i, row in df.iterrows():
            symbol = row["Crypto"].replace("USDT", "")
            if row["Transaction Type"] == "Spot Trading":
                trade = Trade(
                    time=row["Creation Time(UTC+1)"],
                    type="BUY" if row["Direction"] == "Inflow" else "SELL",
                    symbol=symbol,
                    filled_ammount=row["Quantity"],
                )
                if symbol in account.balances.keys():
                    account.balances[symbol].trades.append(trade)
                else:
                    account.balances[symbol] = Balance(symbol=symbol, trades=[trade])
        return account

    def prepare_headers(self):
        headers = {"Content-Type": "application/json", "X-MEXC-APIKEY": self.api_key}
        return headers

    def post_signed_request(self, timestamp: str, params=dict):
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        query_string = self.api_key + timestamp + query_string
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def get_signature_request(self, query_string=str):
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def get_all_symbols(self):
        headers = self.prepare_headers()
        r = self.get("/api/v3/defaultSymbols", headers=headers)
        r_json = r.json()
        results = {}
        for symbol_raw in r_json["data"]:
            symbol, base_asset = self.parse_mexc_symbol(symbol_raw)

            results[symbol] = base_asset
        return results

    def parse_mexc_symbol(self, symbol_raw):
        bases = ["BTC", "ETH", "USDT", "USDC", "USDK", "BNB", "BUSD", "DAI", "TUSD"]
        for base in bases:
            if base in symbol_raw:
                return symbol_raw.strip(base), base

    def get_account_summary(self):
        endpoint = "/api/v3/account"
        headers = self.prepare_headers()
        timestamp = str(int(time.time() * 1000))
        query_string = f"timestamp={timestamp}"
        signature = self.get_signature_request(query_string=query_string)
        params = {"timestamp": timestamp, "signature": signature}
        r = self.get(endpoint, headers=headers, params=params)
        return r.json()

    def get_all_orders(self):
        endpoint = "/api/v3/allOrders"
        headers = self.prepare_headers()
        timestamp = str(int(time.time() * 1000))
        query_string = f"timestamp={timestamp}"
        signature = self.get_signature_request(query_string=query_string)
        params = {"timestamp": timestamp, "signature": signature}
        r = self.get(endpoint, headers=headers, params=params)
        return r.json()

    def get_symbol_kline(
        self, symbol, interval, expected_klines, start_at, end_at
    ) -> List[Kline] | None:
        endpoint = "/api/v3/klines"
        """
        Parameters:
            Name	Type	Mandatory	Description
            symbol	string	YES	
            interval	ENUM	YES	ENUM: Kline Interval
            startTime	long	NO	
            endTime	long	NO	
            limit	integer	NO	Default 500; max 1000.
        """
        interval = self.map_interval(interval)
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_at * 1000,
            "endTime": end_at * 1000,
        }
        headers = self.prepare_headers()
        r = self.get(endpoint, headers=headers, params=params)
        r_json = r.json()
        logger.info(r_json)
        if r.status_code != 200:
            return []
        klines = []

        for kline in r_json:
            klines.append(
                Kline(
                    time=kline[0] / 1000,  # timestamp
                    open=kline[1],
                    high=kline[2],
                    low=kline[3],
                    close=kline[4],
                    volume=kline[5],
                )
            )
        return klines

    def get_symbol_price(self, symbols=List[str]):
        symbols = [f"{symbol}USDT" for symbol in symbols]
        endpoint = "/api/v3/ticker/price"
        headers = self.prepare_headers()
        r = self.get(endpoint, headers=headers, params={"symbols": "all"})
        r_json = r.json()
        return r_json

    def get_trades(self, symbol: str):
        endpoint = "/api/v3/trades"
        headers = self.prepare_headers()
        r = self.get(endpoint, headers=headers, params={"symbol": symbol})
        r_json = r.json()
        return r_json

    def build_symbol_pair(self, symbol: Symbol):
        return f"{symbol.symbol}{symbol.base_asset}"


class KuCoinClient(ExchangeClient):
    class KLINE_INTERVALS(Enum):
        ONE_MINUTE = "1min"
        FIVE_MINUTES = "5min"
        FIFTHEEN_MINUTES = "15min"
        THIRTHY_MINUTEs = "30min"
        ONE_HOUR = "1hour"
        FOUR_HOURS = "4hour"
        ONE_DAY = "1day"
        ONE_WEEK = "1week"

    def parse_kucoin_account(self, df):
        account = Account(exchange="kucoin")
        for i, row in df.iterrows():
            symbol = row["Symbol"].replace("-USDT", "").replace("-USDC", "")
            trade = Trade(
                time=row["Order Time(UTC+01:00)"],
                type=row["Side"],
                symbol=symbol,
                fee=row["Fee"],
                filled_ammount=row["Filled Amount"],
                avg_price=row["Avg. Filled Price"],
            )
            if symbol in account.balances.keys():
                account.balances[symbol].trades.append(trade)
            else:
                account.balances[symbol] = Balance(symbol=symbol, trades=[trade])
        return account

    def prepare_headers(self, endpoint, params=None):
        now = int(time.time() * 1000)
        str_to_sign = str(now) + "GET" + endpoint
        if params:
            str_to_sign += "?" + "&".join([f"{k}={v}" for k, v in params.items()])
        signature = base64.b64encode(
            hmac.new(
                self.api_secret.encode("utf-8"),
                str_to_sign.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        )

        passphrase = base64.b64encode(
            hmac.new(
                self.api_secret.encode("utf-8"),
                self.passphrase.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        )
        headers = {
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(now),
            "KC-API-KEY": self.api_key,
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": "2",
        }

        return headers

    def get_all_symbols(self):
        headers = self.prepare_headers("/api/v1/symbols")
        r_data = self.get("/api/v2/symbols", headers=headers)
        r_json = r_data.json()
        results = {}
        for symbol in r_json["data"]:
            results[symbol["baseCurrency"]] = symbol["quoteCurrency"]
        return results

    def parse_kucoin_symbol(self, symbol_raw):
        logger.info(symbol_raw)
        return symbol_raw.split("-")[0], symbol_raw.split("-")[1]

    def get_all_orders(self):
        return {}

    def get_account_summary(self):
        """get holdings and balance"""
        endpoint = "/api/v1/accounts"
        headers = self.prepare_headers(endpoint)
        r_data = self.get(endpoint, headers=headers)
        r_json = r_data.json()
        return r_json

    def get_symbol_price(self, symbols: List[str]):
        endpoint = "/api/v1/prices"
        headers = self.prepare_headers(endpoint)
        params = {"base": "USD", "currencies": ",".join(symbols)}
        r_data = self.get(endpoint, headers=headers, params=params)
        r_json = r_data.json()
        return r_json

    def get_symbol_kline(
        self,
        symbol: str,
        interval: str,
        start_at: int = None,
        end_at: int = None,
    ) -> List[dict]:
        # kucoin retuns at most 1500 klines per request
        params = {}
        # calculate the expected number of klines
        logger.info(f"start_at {datetime.fromtimestamp(start_at)}")
        logger.info(f"end_at {datetime.fromtimestamp(end_at)}")
        expected_klines = self.calculate_expected_klines(
            start_date=start_at,
            end_date=end_at,
            interval=interval,
        )
        logger.info(f"expected_klines {expected_klines}")
        if expected_klines > 1500:
            # paginate requests
            number_of_pages = int(expected_klines // 1500)
        else:
            number_of_pages = 1

        klines = []
        logger.info(number_of_pages)
        logger.info(expected_klines)
        for page in range(1, number_of_pages + 1):
            data = None
            endpoint = "/api/v1/market/candles"
            headers = self.prepare_headers(endpoint)

            params["currentPage"] = page
            params["pageSize"] = 1500
            params["symbol"] = symbol
            params["type"] = interval
            params["startAt"] = end_at
            params["endAt"] = start_at

            r_data = self.get(
                endpoint,
                headers=headers,
                params=params,
            )
            r_json = r_data.json()
            logger.info(f"status code kucoin: {r_data.status_code}")
            logger.info(f"response code kucoin: {r_json['code']}")

            if "data" not in r_json.keys():
                continue

            data = r_json.pop("data")
            logger.info(f"len data: {len(data)}")

            for kline in data:
                klines.append(
                    {
                        "time": kline[0],
                        "open": kline[1],
                        "close": kline[2],
                        "high": kline[3],
                        "low": kline[4],
                        "volume": kline[5],
                    }
                )
            logger.info(len(klines))
        return klines

    def get_trades(self):
        endpoint = "/api/v1/fills"
        params = {"status": "done"}
        headers = self.prepare_headers(endpoint, params=params)

        r = self.get(endpoint, headers=headers, params=params)
        r_json = r.json()
        return r_json

    def build_symbol_pair(self, symbol: Symbol):
        return f"{symbol.symbol}-{symbol.base_asset}"


class CryptoRankClient:
    def get_symbols(self, symbols):
        r = httpx.get(
            CRYPTO_RANK_BASE_ENDPOINT + "currencies",
            params={
                "api_key": CRYPTO_RANK_API_KEY,
                "symbols": ",".join(symbols),
                "state": "active",
            },
        )
        return r.json()

    def get_symbols_by_ids(self, ids):
        r = httpx.get(
            CRYPTO_RANK_BASE_ENDPOINT + "currencies",
            params={
                "api_key": CRYPTO_RANK_API_KEY,
                "ids": ",".join(ids),
                "state": "active",
            },
        )
        return r.json()
