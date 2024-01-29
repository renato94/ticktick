from pydantic import BaseModel

class Balance:
    symbol: str
    balance: float
    price: float
    

class Account(BaseModel):
    exchange: str

