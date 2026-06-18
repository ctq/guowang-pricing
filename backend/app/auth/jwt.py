from datetime import datetime, timedelta, timezone
from os import environ

import jwt

SECRET = environ.get("JWT_SECRET")
if not SECRET:
    raise RuntimeError("JWT_SECRET environment variable must be set")

ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 7


def create_token(openid: str) -> str:
    payload = {
        "openid": openid,
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
