from datetime import timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.utils.time import now_msk

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """проверяет пароль"""

    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """хеширует пароль"""

    return pwd_context.hash(password)


def create_access_token(
    subject: str, expires_delta: timedelta | None = None
) -> str:
    """создает jwt токен"""

    expire = now_msk() + (
        expires_delta
        or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(
        payload, settings.secret_key, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> dict[str, Any]:
    """декодирует jwt токен"""

    return jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
