from pydantic import BaseModel
from backend.api.database import Base
from sqlalchemy import (
    Column,
    Integer,
    String,
    TIMESTAMP,
    Boolean,
    text,
    Double,
    ForeignKey,
)
from sqlalchemy.orm import relationship


# finance related models
class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    exchange_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, nullable=False)
    symbol = Column(String, nullable=False)
    ammount = Column(Double, nullable=False)
    side = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False)
    price = Column(Double, nullable=False)
    fee = Column(Double, nullable=False)


class Exchange(Base):
    __tablename__ = "exchanges"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    secret_key = Column(String, nullable=False)
    passphrase = Column(String, nullable=True)
    base_url = Column(String, nullable=True)


class ExchangeBase(BaseModel):
    name: str
    api_key: str
    secret_key: str
    passphrase: str
    base_url: str

    class Config:
        orm_mode = True


class Interval(Base):
    __tablename__ = "intervals"

    id = Column(Integer, primary_key=True, index=True)
    exchange_id = Column(Integer, nullable=False)
    interval = Column(String, nullable=False)


class IntervalBase(BaseModel):
    interval: str

    class Config:
        orm_mode = True


class Symbol(Base):
    __tablename__ = "symbols"
    id = Column(Integer, primary_key=True, index=True)
    exchange_id = Column(Integer, nullable=False)
    symbol = Column(String, nullable=False)
    base_asset = Column(String, nullable=False)


class SymbolBase(BaseModel):
    symbol: str
    base_asset: str

    class Config:
        orm_mode = True


class Kline(Base):
    __tablename__ = "klines"

    id = Column(Integer, primary_key=True, nullable=False)
    symbol_id = Column(Integer, nullable=False)
    interval_id = Column(Integer, nullable=False)
    time = Column(String, nullable=False)
    open = Column(Double, nullable=False)
    high = Column(Double, nullable=False)
    low = Column(Double, nullable=False)
    close = Column(Double, nullable=False)
    volume = Column(Double, nullable=False)
    quote_asset_volume = Column(Double, nullable=True)

    # save the kline data in the database
    # we can use this data to backtest the strategy
    # and also use it to display the chart
    # we can also use it to calculate the indicators


class KlinesBase(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    class Config:
        orm_mode = True
