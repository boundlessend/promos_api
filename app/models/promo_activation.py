import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base
from app.utils.time import now_msk


class PromoActivation(Base):
    """активация промокода"""

    __tablename__ = "promo_activations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    promo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("promo_codes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("promo_campaigns.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_msk, nullable=False, index=True
    )
    applied_bonus_points: Mapped[int] = mapped_column(Integer, nullable=False)
    promo_code_snapshot: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    promo_description_snapshot: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    promo_type_snapshot: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    campaign_name_snapshot: Mapped[str] = mapped_column(
        String(255), nullable=False
    )

    user = relationship("User", back_populates="activations")
    promo = relationship("PromoCode", back_populates="activations")
    campaign = relationship("PromoCampaign")
