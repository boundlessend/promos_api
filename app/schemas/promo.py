from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.promo_code import PromoType
from app.models.promo_code_history import PromoHistoryAction
from app.schemas.common import DateTimeMoscowMixin, ORMModel
from app.utils.time import ensure_moscow_tz


class PromoBase(BaseModel):
    """базовая схема промокода"""

    model_config = ConfigDict(extra="forbid")

    campaign_id: UUID
    code: str = Field(min_length=1, max_length=100)
    description: str | None = None
    promo_type: PromoType
    bonus_points: int
    is_active: bool = True
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    max_activations: int | None = None
    per_user_limit: int = 1
    target_user_id: UUID | None = None

    @field_validator("bonus_points", "per_user_limit")
    @classmethod
    def validate_positive_ints(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("значение должно быть больше нуля")
        return value

    @field_validator("max_activations")
    @classmethod
    def validate_max_activations(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("max_activations должно быть больше нуля")
        return value

    @field_validator("starts_at", "expires_at", mode="before")
    @classmethod
    def normalize_dates(cls, value):
        if value is None:
            return value
        if isinstance(value, datetime):
            return ensure_moscow_tz(value)
        return value

    @model_validator(mode="after")
    def validate_business_rules(self):
        if (
            self.starts_at
            and self.expires_at
            and self.starts_at > self.expires_at
        ):
            raise ValueError("starts_at не может быть позже expires_at")
        if self.promo_type == PromoType.personal and not self.target_user_id:
            raise ValueError("для personal промокода нужен target_user_id")
        if (
            self.promo_type == PromoType.generic
            and self.target_user_id is not None
        ):
            raise ValueError(
                "для generic промокода target_user_id должен быть пустым"
            )
        if (
            self.max_activations is not None
            and self.max_activations < self.per_user_limit
        ):
            raise ValueError(
                "max_activations не может быть меньше per_user_limit"
            )
        return self


class PromoCreate(PromoBase):
    """создание промокода"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "campaign_id": "10000000-0000-0000-0000-000000000001",
                "code": "SUMMER500",
                "description": "бонус для летней кампании",
                "promo_type": "generic",
                "bonus_points": 500,
                "is_active": True,
                "starts_at": "2026-06-01T00:00:00+03:00",
                "expires_at": "2026-08-31T23:59:59+03:00",
                "max_activations": 1000,
                "per_user_limit": 1,
                "target_user_id": None,
            }
        },
    )


class PromoUpdate(BaseModel):
    """обновление промокода"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "description": "обновленное описание",
                "bonus_points": 600,
                "per_user_limit": 2,
                "expires_at": "2026-09-15T23:59:59+03:00",
            }
        },
    )

    campaign_id: UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    promo_type: PromoType | None = None
    bonus_points: int | None = None
    is_active: bool | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    max_activations: int | None = None
    per_user_limit: int | None = None
    target_user_id: UUID | None = None

    @field_validator("bonus_points", "per_user_limit")
    @classmethod
    def validate_positive_ints(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("значение должно быть больше нуля")
        return value

    @field_validator("max_activations")
    @classmethod
    def validate_max_activations(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("max_activations должно быть больше нуля")
        return value

    @field_validator("starts_at", "expires_at", mode="before")
    @classmethod
    def normalize_dates(cls, value):
        if value is None:
            return value
        if isinstance(value, datetime):
            return ensure_moscow_tz(value)
        return value


class PromoRead(DateTimeMoscowMixin, ORMModel):
    """ответ промокода"""

    id: UUID
    campaign_id: UUID
    target_user_id: UUID | None
    code: str
    description: str | None
    promo_type: str
    bonus_points: int
    is_active: bool
    starts_at: datetime | None
    expires_at: datetime | None
    max_activations: int | None
    per_user_limit: int
    created_at: datetime
    updated_at: datetime


class PromoHistoryRead(DateTimeMoscowMixin, ORMModel):
    """запись истории промокода"""

    id: UUID
    promo_id: UUID
    changed_by_user_id: UUID
    action: PromoHistoryAction
    changed_at: datetime
    before_payload: dict[str, Any] | None
    after_payload: dict[str, Any] | None


class PromoReadDetailed(PromoRead):
    """детальный ответ промокода"""

    history: list[PromoHistoryRead] = Field(default_factory=list)


class PromoActivationRead(DateTimeMoscowMixin, ORMModel):
    """ответ активации"""

    id: UUID
    user_id: UUID
    promo_id: UUID
    campaign_id: UUID
    activated_at: datetime
    applied_bonus_points: int
    promo_code_snapshot: str
    promo_description_snapshot: str | None
    promo_type_snapshot: str
    campaign_name_snapshot: str
