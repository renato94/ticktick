from database import Base
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
    id = Column(Integer, primary_key=True, index=True)
    exchange_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)


class Order(Base):
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, nullable=False)
    symbol = Column(String, nullable=False)
    ammount = Column(Double, nullable=False)
    side = Column(String, nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False)
    price = Column(Double, nullable=False)
    fee = Column(Double, nullable=False)


class Exchange(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    secret_key = Column(String, nullable=False)
    passphrase = Column(String, nullable=True)


class Interval(Base):
    id = Column(Integer, primary_key=True, index=True)
    exchange_id = Column(Integer, nullable=False)
    interval = Column(String, nullable=False)


class Symbol(Base):
    id = Column(Integer, primary_key=True, index=True)
    exchange_id = Column(Integer, nullable=False)
    symbol = Column(String, nullable=False)


class Kline(Base):
    __tablename__ = "kline"

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
