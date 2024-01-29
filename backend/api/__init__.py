import jwt
from datetime import datetime, timedelta, timezone
from backend.config import ALGORITHM, SECRET_KEY
from fastapi import Request
from icecream import ic

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=35)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(request: Request):
    authorization: str = request.headers.get("Authorization")
    token = authorization.split("Bearer ")[1].strip()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        ic("valid token")
        return payload
    except jwt.PyJWTError:
        return None
