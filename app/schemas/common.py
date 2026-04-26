from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer

from app.utils.time import ensure_moscow_tz


class ORMModel(BaseModel):
    """базовая схема для orm"""

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class DateTimeMoscowMixin(BaseModel):
    """миксин сериализации времени москвы"""

    @field_serializer(
        "created_at",
        "updated_at",
        "starts_at",
        "expires_at",
        "activated_at",
        "changed_at",
        check_fields=False,
    )
    def serialize_dt(self, value: datetime | None, _info) -> str | None:
        if value is None:
            return None
        return ensure_moscow_tz(value).isoformat()


class ErrorDetail(BaseModel):
    """полезная нагрузка ошибки"""

    code: str
    message: str
    context: dict[str, Any]


class ErrorResponse(BaseModel):
    """схема ответа ошибки"""

    error: ErrorDetail


class UUIDPath(BaseModel):
    """схема uuid пути"""

    id: UUID
