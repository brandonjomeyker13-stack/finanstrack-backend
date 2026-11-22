import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from jwt import InvalidTokenError

from app.core.config import settings

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return _ph.verify(hashed_password, password)
    except (VerifyMismatchError, InvalidHash):
        return False


def create_access_token(usuario_id: str) -> str:
    expira = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": usuario_id, "exp": expira},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except InvalidTokenError as exc:
        raise InvalidTokenError("token inválido") from exc


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()
