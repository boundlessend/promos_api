from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.schemas.common import DateTimeMoscowMixin, ORMModel
from app.utils.time import ensure_moscow_tz


class CampaignBase(BaseModel):
    """базовая схема кампании"""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    is_active: bool = True
    starts_at: datetime | None = None
    expires_at: datetime | None = None

    @field_validator("starts_at", "expires_at", mode="before")
    @classmethod
    def normalize_dates(cls, value):
        if value is None:
            return value
        if isinstance(value, datetime):
            return ensure_moscow_tz(value)
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.starts_at
            and self.expires_at
            and self.starts_at > self.expires_at
        ):
            raise ValueError("starts_at не может быть позже expires_at")
        return self


class CampaignCreate(CampaignBase):
    """создание кампании"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "summer 2026",
                "is_active": True,
                "starts_at": "2026-06-01T00:00:00+03:00",
                "expires_at": "2026-08-31T23:59:59+03:00",
            }
        },
    )


class CampaignUpdate(BaseModel):
    """обновление кампании"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "summer 2026 extended",
                "expires_at": "2026-09-15T23:59:59+03:00",
                "is_active": True,
            }
        },
    )

    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None

    @field_validator("starts_at", "expires_at", mode="before")
    @classmethod
    def normalize_dates(cls, value):
        if value is None:
            return value
        if isinstance(value, datetime):
            return ensure_moscow_tz(value)
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.starts_at
            and self.expires_at
            and self.starts_at > self.expires_at
        ):
            raise ValueError("starts_at не может быть позже expires_at")
        return self


class CampaignRead(DateTimeMoscowMixin, ORMModel):
    """ответ кампании"""

    id: UUID
    name: str
    is_active: bool
    starts_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
