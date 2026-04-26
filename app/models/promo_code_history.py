import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.db import Base
from app.utils.time import now_msk


class PromoHistoryAction(str, enum.Enum):
    """тип изменения промокода"""

    created = "created"
    updated = "updated"
    disabled = "disabled"


class PromoCodeHistory(Base):
    """история изменений промокода"""

    __tablename__ = "promo_code_history"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    promo_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("promo_codes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    changed_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    action: Mapped[PromoHistoryAction] = mapped_column(
        Enum(PromoHistoryAction, name="promo_history_action"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_msk, nullable=False, index=True
    )
    before_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )
    after_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
    )

    promo = relationship("PromoCode", back_populates="history_entries")
    changed_by_user = relationship(
        "User", back_populates="promo_history_entries"
    )
