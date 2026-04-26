import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base
from app.utils.time import now_msk


class PromoType(str, enum.Enum):
    """тип промокода"""

    generic = "generic"
    personal = "personal"


class PromoCode(Base):
    """промокод"""

    __tablename__ = "promo_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("promo_campaigns.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    promo_type: Mapped[PromoType] = mapped_column(
        Enum(PromoType, name="promo_type"), nullable=False, index=True
    )
    bonus_points: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    starts_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    max_activations: Mapped[int | None] = mapped_column(Integer, nullable=True)
    per_user_limit: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_msk, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=now_msk,
        onupdate=now_msk,
        nullable=False,
    )

    campaign = relationship("PromoCampaign", back_populates="promos")
    target_user = relationship(
        "User", back_populates="assigned_promos", foreign_keys=[target_user_id]
    )
    activations = relationship("PromoActivation", back_populates="promo")
    history_entries = relationship("PromoCodeHistory", back_populates="promo")
