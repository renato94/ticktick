from pydantic import BaseModel
from typing import Dict, List


class Trade(BaseModel):
    time: str
    type: str
    symbol: str
    fee: float
    filled_ammount: float
    avg_price: float


class Balance(BaseModel):
    trades: List[Trade]
    balance: float = 0.0


class Account(BaseModel):
    exchange: str
    balances: Dict[str, Balance] = {}
