import base64
from dataclasses import dataclass
import hashlib
import hmac
import time
from enum import Enum
from typing import List

import httpx
from abc import ABC, abstractmethod

from api.config import CRYPTO_RANK_API_KEY, CRYPTO_RANK_BASE_ENDPOINT
from icecream import ic


class ExchangeClient(ABC):
    def __init__(
        self, api_key: str, api_secret: str, base_url: str, passphrase: str = None
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.passphrase = passphrase
        self.client = httpx.Client()

    @abstractmethod
    def prepare_headers(self, *args, **kwargs):
        pass

    def get(self, endpoint, headers: dict, params=None):
        ic(params)
        return self.client.request(
            "GET", str(self.base_url) + endpoint, params=params, headers=headers
        )

    def post(self, endpoint, headers: dict, params=None, json=None):
        return self.client.request(
            "POST",
            str(self.base_url) + endpoint,
            params=params,
            headers=headers,
            json=json,
        )

    def map_interval(self, interval: str):
        ic(self.KLINE_INTERVALS.__dict__[interval].value)
        ic(interval)
        return self.KLINE_INTERVALS.__dict__[interval].value


@dataclass
class Kline:
    time: int
    open: float
    close: float
    high: float
    low: float
    volume: float


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
        return r.json()

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
        self, symbol, interval, start_at, end_at, *, params=None
    ) -> List[Kline]:
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
            "startTime": start_at,
            "endTime": end_at,
        }
        ic(params)
        headers = self.prepare_headers()
        r = self.get(endpoint, headers=headers, params=params)
        r_json = r.json()
        ic(r_json)

        if r.status_code != 200:
            return []
        klines = []

        for kline in r_json:
            klines.append(
                Kline(
                    time=kline[0],
                    open=kline[1],
                    high=kline[2],
                    low=kline[3],
                    close=kline[4],
                    volume=kline[5],
                )
            )
        return klines


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

    def prepare_headers(self, endpoint, params=None):
        now = int(time.time() * 1000)
        str_to_sign = str(now) + "GET" + endpoint
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
        return r_json

    def get_all_orders(self):
        return {}

    def get_account_summary(self):
        """get holdings and balance"""
        endpoint = "/api/v1/accounts"
        headers = self.prepare_headers(endpoint)
        r_data = self.get(endpoint, headers=headers)
        r_json = r_data.json()
        return r_json

    def get_symbol_kline(
        self,
        symbol: str,
        interval: str,
        start_at: int = None,
        end_at: int = None,
    ) -> List[Kline]:
        endpoint = "/api/v1/market/candles"
        headers = self.prepare_headers(endpoint)
        r_data = self.get(
            endpoint,
            headers=headers,
            params={
                "symbol": symbol,
                "type": self.map_interval(interval),
                "startAt": start_at,
                "endAt": end_at,
            },
        )
        r_json = r_data.json()
        klines = []
        if "data" not in r_json.keys():
            return []
        for kline in r_json["data"]:
            klines.append(
                Kline(
                    time=kline[0],
                    open=kline[1],
                    close=kline[2],
                    high=kline[3],
                    low=kline[4],
                    volume=kline[5],
                )
            )
        return klines


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