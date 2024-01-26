import base64
import hashlib
import hmac
import time

import httpx
from abc import ABC, abstractmethod


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


class MexcClient(ExchangeClient):
    class KLINE_INTERVALS(self,enum.Enum):
        ONE_MINUTE="1m"
        FIVE_MINUTES= "5m"
        "15m" ="15 minute"
        "30m"= "30 minute"
        "60m" ="60 minute"
        "4h"= "4 hour"
        "1d"= "1 day"
        "1w" ="1 week"
        "1M"= "1 month"
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
        signature = hmac.new(self.api_secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
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

    def get_symbol_kline(self):
        pass


class KuCoinClient(ExchangeClient):
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

    def get_symbol_kline(self):
        pass
