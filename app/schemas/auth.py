from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.schemas.common import DateTimeMoscowMixin, ORMModel


class LoginRequest(BaseModel):
    """запрос на логин"""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """ответ с токеном"""

    access_token: str
    token_type: str = "bearer"


class UserRead(DateTimeMoscowMixin, ORMModel):
    """схема пользователя"""

    id: UUID
    email: EmailStr
    username: str
    is_active: bool
    is_admin: bool
