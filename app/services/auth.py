from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.models.user import User


def authenticate_user(db: Session, email: str, password: str) -> User:
    """проверяет логин и пароль"""

    user = db.execute(
        select(User).where(User.email == email)
    ).scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("неверный email или пароль")
    if not user.is_active:
        raise UnauthorizedError("пользователь отключен")
    return user


def login_user(db: Session, email: str, password: str) -> str:
    """выдает токен пользователю"""

    user = authenticate_user(db, email, password)
    return create_access_token(str(user.id))
