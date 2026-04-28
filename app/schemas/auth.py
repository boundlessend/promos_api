from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.schemas.common import DateTimeMoscowMixin, ORMModel


class LoginRequest(BaseModel):
    """запрос на логин"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "email": "admin@example.com",
                "password": "admin123",
            }
        },
    )

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
