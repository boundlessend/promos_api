from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/token", auto_error=False
)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """возвращает текущего пользователя"""

    if not token:
        raise UnauthorizedError("требуется bearer токен")

    payload = decode_token(token)
    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError("в токене отсутствует subject")

    user = db.execute(
        select(User).where(User.id == UUID(subject))
    ).scalar_one_or_none()
    if not user or not user.is_active:
        raise UnauthorizedError("пользователь не найден или отключен")
    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """проверяет права администратора"""

    if not user.is_admin:
        raise ForbiddenError()
    return user
