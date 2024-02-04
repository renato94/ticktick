import enum
from pydantic import BaseModel
from typing import Dict, List


class TradeType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class Trade(BaseModel):
    time: str
    type: TradeType
    symbol: str
    filled_ammount: float
    fee: float = 0.0


class Balance(BaseModel):
    trades: List[Trade]
    balance: float = 0.0


class Account(BaseModel):
    exchange: str
    balances: Dict[str, Balance] = {}