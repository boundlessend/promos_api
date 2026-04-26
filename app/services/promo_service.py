from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.models.promo_activation import PromoActivation
from app.models.promo_campaign import PromoCampaign
from app.models.promo_code import PromoCode, PromoType
from app.models.promo_code_history import PromoCodeHistory, PromoHistoryAction
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignUpdate
from app.schemas.promo import PromoCreate, PromoUpdate
from app.utils.time import (
    ensure_moscow_tz,
    is_not_expired,
    is_started,
    now_msk,
)

IMMUTABLE_AFTER_ACTIVATIONS_FIELDS = {
    "promo_type",
    "target_user_id",
    "campaign_id",
}


def get_field_value(payload: Any, field: str, current_value: Any) -> Any:
    """возвращает новое значение с учетом partial update"""

    if (
        hasattr(payload, "model_fields_set")
        and field in payload.model_fields_set
    ):
        return getattr(payload, field)
    return current_value


def model_to_dict(instance: PromoCode | PromoCampaign) -> dict[str, Any]:
    """собирает снимок модели для истории"""

    data: dict[str, Any] = {}
    for column in instance.__table__.columns:  # type: ignore[attr-defined]
        value = getattr(instance, column.name)
        if isinstance(value, datetime):
            data[column.name] = ensure_moscow_tz(value).isoformat()
        elif hasattr(value, "value"):
            data[column.name] = value.value
        else:
            data[column.name] = (
                str(value) if isinstance(value, UUID) else value
            )
    return data


def create_history_entry(
    db: Session,
    *,
    promo: PromoCode,
    changed_by: User,
    action: PromoHistoryAction,
    before_payload: dict[str, Any] | None,
    after_payload: dict[str, Any] | None,
) -> PromoCodeHistory:
    """сохраняет запись истории промокода"""

    entry = PromoCodeHistory(
        promo_id=promo.id,
        changed_by_user_id=changed_by.id,
        action=action,
        before_payload=before_payload,
        after_payload=after_payload,
    )
    db.add(entry)
    return entry


def campaign_is_available(
    campaign: PromoCampaign, current_time: datetime | None = None
) -> bool:
    """проверяет доступность кампании"""

    current_time = current_time or now_msk()
    return (
        campaign.is_active
        and is_started(campaign.starts_at, current_time)
        and is_not_expired(campaign.expires_at, current_time)
    )


def promo_is_available(
    promo: PromoCode, current_time: datetime | None = None
) -> bool:
    """проверяет доступность промокода"""

    current_time = current_time or now_msk()
    return (
        promo.is_active
        and is_started(promo.starts_at, current_time)
        and is_not_expired(promo.expires_at, current_time)
    )


def get_campaign_or_404(db: Session, campaign_id: UUID) -> PromoCampaign:
    """возвращает кампанию или ошибку"""

    campaign = db.execute(
        select(PromoCampaign).where(PromoCampaign.id == campaign_id)
    ).scalar_one_or_none()
    if campaign is None:
        raise NotFoundError(
            "campaign_not_found",
            "кампания не найдена",
            {"campaign_id": str(campaign_id)},
        )
    return campaign


def get_promo_or_404(
    db: Session, promo_id: UUID, with_history: bool = False
) -> PromoCode:
    """возвращает промокод или ошибку"""

    query = (
        select(PromoCode)
        .options(
            joinedload(PromoCode.campaign), joinedload(PromoCode.target_user)
        )
        .where(PromoCode.id == promo_id)
    )
    if with_history:
        query = query.options(selectinload(PromoCode.history_entries))
    promo = db.execute(query).unique().scalar_one_or_none()
    if promo is None:
        raise NotFoundError(
            "promo_not_found",
            "промокод не найден",
            {"promo_id": str(promo_id)},
        )
    return promo


def validate_campaign_dates_on_update(
    existing: PromoCampaign, payload: CampaignUpdate
) -> None:
    """валидирует даты обновления кампании"""

    starts_at = get_field_value(payload, "starts_at", existing.starts_at)
    expires_at = get_field_value(payload, "expires_at", existing.expires_at)
    if starts_at and expires_at and starts_at > expires_at:
        raise BadRequestError(
            "invalid_campaign_dates",
            "starts_at не может быть позже expires_at",
        )


def create_campaign(db: Session, payload: CampaignCreate) -> PromoCampaign:
    """создает кампанию"""

    campaign = PromoCampaign(**payload.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def update_campaign(
    db: Session, campaign: PromoCampaign, payload: CampaignUpdate
) -> PromoCampaign:
    """обновляет кампанию"""

    validate_campaign_dates_on_update(campaign, payload)
    for field in payload.model_fields_set:
        setattr(campaign, field, getattr(payload, field))
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def list_campaigns(
    db: Session, user: User, is_active: bool | None = None
) -> list[PromoCampaign]:
    """возвращает список кампаний"""

    current_time = now_msk()
    query: Select[tuple[PromoCampaign]] = select(PromoCampaign).order_by(
        PromoCampaign.created_at.desc()
    )
    if user.is_admin:
        if is_active is not None:
            query = query.where(PromoCampaign.is_active == is_active)
        return list(db.execute(query).scalars().all())

    query = query.where(PromoCampaign.is_active.is_(True))
    campaigns = list(db.execute(query).scalars().all())
    return [
        campaign
        for campaign in campaigns
        if campaign_is_available(campaign, current_time)
    ]


def validate_promo_refs(
    db: Session,
    payload: PromoCreate | PromoUpdate,
    existing: PromoCode | None = None,
) -> tuple[PromoCampaign, User | None]:
    """валидирует связанные сущности промокода"""

    campaign_id = get_field_value(
        payload, "campaign_id", existing.campaign_id if existing else None
    )
    if campaign_id is None:
        raise BadRequestError("campaign_required", "campaign_id обязателен")
    campaign = get_campaign_or_404(db, campaign_id)

    target_user_id = get_field_value(
        payload,
        "target_user_id",
        existing.target_user_id if existing else None,
    )
    promo_type = get_field_value(
        payload, "promo_type", existing.promo_type if existing else None
    )

    target_user = None
    if promo_type == PromoType.personal:
        if target_user_id is None:
            raise BadRequestError(
                "target_user_required",
                "для personal промокода нужен target_user_id",
            )
        target_user = db.execute(
            select(User).where(User.id == target_user_id)
        ).scalar_one_or_none()
        if target_user is None:
            raise NotFoundError(
                "target_user_not_found",
                "пользователь для персонального промокода не найден",
                {"target_user_id": str(target_user_id)},
            )
    else:
        if target_user_id is not None:
            raise BadRequestError(
                "invalid_target_user",
                "для generic промокода target_user_id должен быть пустым",
            )
    return campaign, target_user


def validate_promo_update_business_rules(
    db: Session, promo: PromoCode, payload: PromoUpdate
) -> None:
    """валидирует обновление промокода"""

    starts_at = get_field_value(payload, "starts_at", promo.starts_at)
    expires_at = get_field_value(payload, "expires_at", promo.expires_at)
    promo_type = get_field_value(payload, "promo_type", promo.promo_type)
    target_user_id = get_field_value(
        payload, "target_user_id", promo.target_user_id
    )
    max_activations = get_field_value(
        payload, "max_activations", promo.max_activations
    )
    per_user_limit = get_field_value(
        payload, "per_user_limit", promo.per_user_limit
    )

    if starts_at and expires_at and starts_at > expires_at:
        raise BadRequestError(
            "invalid_promo_dates", "starts_at не может быть позже expires_at"
        )
    if promo_type == PromoType.personal and target_user_id is None:
        raise BadRequestError(
            "target_user_required",
            "для personal промокода нужен target_user_id",
        )
    if promo_type == PromoType.generic and target_user_id is not None:
        raise BadRequestError(
            "invalid_target_user",
            "для generic промокода target_user_id должен быть пустым",
        )
    if (
        max_activations is not None
        and per_user_limit is not None
        and max_activations < per_user_limit
    ):
        raise BadRequestError(
            "invalid_limits",
            "max_activations не может быть меньше per_user_limit",
        )

    total_activations = db.execute(
        select(func.count(PromoActivation.id)).where(
            PromoActivation.promo_id == promo.id
        )
    ).scalar_one()
    if max_activations is not None and total_activations > max_activations:
        raise ConflictError(
            "promo_history_conflict",
            "нельзя уменьшить max_activations ниже уже совершенных активаций",
            {
                "current_activations": total_activations,
                "requested_max_activations": max_activations,
            },
        )

    per_user_counts = db.execute(
        select(PromoActivation.user_id, func.count(PromoActivation.id))
        .where(PromoActivation.promo_id == promo.id)
        .group_by(PromoActivation.user_id)
    ).all()
    max_user_count = max((count for _, count in per_user_counts), default=0)
    if per_user_limit is not None and max_user_count > per_user_limit:
        raise ConflictError(
            "promo_history_conflict",
            "нельзя уменьшить per_user_limit ниже уже совершенных активаций пользователя",
            {
                "current_max_user_activations": max_user_count,
                "requested_per_user_limit": per_user_limit,
            },
        )

    if total_activations > 0:
        changes = payload.model_dump(exclude_unset=True)
        forbidden_changes = {}
        for field in IMMUTABLE_AFTER_ACTIVATIONS_FIELDS:
            if field in changes and changes[field] != getattr(promo, field):
                forbidden_changes[field] = {
                    "before": getattr(promo, field),
                    "after": changes[field],
                }
        if forbidden_changes:
            raise ConflictError(
                "promo_immutable_after_activation",
                "нельзя менять критичные поля промокода после активаций",
                {"fields": forbidden_changes},
            )


def create_promo(
    db: Session, payload: PromoCreate, changed_by: User
) -> PromoCode:
    """создает промокод"""

    validate_promo_refs(db, payload)
    promo = PromoCode(**payload.model_dump())
    db.add(promo)
    db.flush()
    create_history_entry(
        db,
        promo=promo,
        changed_by=changed_by,
        action=PromoHistoryAction.created,
        before_payload=None,
        after_payload=model_to_dict(promo),
    )
    db.commit()
    db.refresh(promo)
    return promo


def update_promo(
    db: Session, promo: PromoCode, payload: PromoUpdate, changed_by: User
) -> PromoCode:
    """обновляет промокод"""

    validate_promo_update_business_rules(db, promo, payload)
    validate_promo_refs(db, payload, promo)
    before_payload = model_to_dict(promo)
    for field in payload.model_fields_set:
        setattr(promo, field, getattr(payload, field))
    db.add(promo)
    db.flush()
    create_history_entry(
        db,
        promo=promo,
        changed_by=changed_by,
        action=PromoHistoryAction.updated,
        before_payload=before_payload,
        after_payload=model_to_dict(promo),
    )
    db.commit()
    db.refresh(promo)
    return promo


def disable_promo(
    db: Session, promo: PromoCode, changed_by: User
) -> PromoCode:
    """отключает промокод"""

    before_payload = model_to_dict(promo)
    promo.is_active = False
    db.add(promo)
    db.flush()
    create_history_entry(
        db,
        promo=promo,
        changed_by=changed_by,
        action=PromoHistoryAction.disabled,
        before_payload=before_payload,
        after_payload=model_to_dict(promo),
    )
    db.commit()
    db.refresh(promo)
    return promo


def list_promos(
    db: Session,
    user: User,
    *,
    promo_type: PromoType | None = None,
    is_active: bool | None = None,
    campaign_id: UUID | None = None,
) -> list[PromoCode]:
    """возвращает список промокодов"""

    query = (
        select(PromoCode)
        .options(joinedload(PromoCode.campaign))
        .order_by(PromoCode.created_at.desc())
    )
    if campaign_id is not None:
        query = query.where(PromoCode.campaign_id == campaign_id)
    if promo_type is not None:
        query = query.where(PromoCode.promo_type == promo_type)

    if user.is_admin:
        if is_active is not None:
            query = query.where(PromoCode.is_active == is_active)
        return list(db.execute(query).unique().scalars().all())

    query = query.where(PromoCode.is_active.is_(True))
    promos = list(db.execute(query).unique().scalars().all())
    current_time = now_msk()
    visible: list[PromoCode] = []
    for promo in promos:
        if not campaign_is_available(promo.campaign, current_time):
            continue
        if not promo_is_available(promo, current_time):
            continue
        if (
            promo.promo_type == PromoType.generic
            or promo.target_user_id == user.id
        ):
            visible.append(promo)
    return visible


def get_visible_promo(db: Session, promo_id: UUID, user: User) -> PromoCode:
    """возвращает промокод с учетом прав"""

    promo = get_promo_or_404(db, promo_id, with_history=user.is_admin)
    if user.is_admin:
        return promo

    if not campaign_is_available(promo.campaign) or not promo_is_available(
        promo
    ):
        raise NotFoundError(
            "promo_not_found",
            "промокод недоступен",
            {"promo_id": str(promo_id)},
        )
    if (
        promo.promo_type == PromoType.personal
        and promo.target_user_id != user.id
    ):
        raise NotFoundError(
            "promo_not_found",
            "промокод недоступен",
            {"promo_id": str(promo_id)},
        )
    return promo


def validate_activation(
    promo: PromoCode, user: User, current_time: datetime
) -> None:
    """валидирует активацию промокода"""

    if not campaign_is_available(promo.campaign, current_time):
        if not promo.campaign.is_active:
            raise ConflictError(
                "campaign_inactive",
                "кампания неактивна",
                {"campaign_id": str(promo.campaign_id)},
            )
        if not is_started(promo.campaign.starts_at, current_time):
            raise ConflictError(
                "campaign_not_started",
                "кампания еще не началась",
                {"campaign_id": str(promo.campaign_id)},
            )
        raise ConflictError(
            "campaign_expired",
            "кампания истекла",
            {"campaign_id": str(promo.campaign_id)},
        )

    if not promo_is_available(promo, current_time):
        if not promo.is_active:
            raise ConflictError(
                "promo_inactive",
                "промокод неактивен",
                {"promo_id": str(promo.id)},
            )
        if not is_started(promo.starts_at, current_time):
            raise ConflictError(
                "promo_not_started",
                "промокод еще не начался",
                {"promo_id": str(promo.id)},
            )
        raise ConflictError(
            "promo_expired", "промокод истек", {"promo_id": str(promo.id)}
        )

    if (
        promo.promo_type == PromoType.personal
        and promo.target_user_id != user.id
    ):
        raise ConflictError(
            "promo_for_another_user",
            "этот персональный промокод выдан другому пользователю",
            {
                "promo_id": str(promo.id),
                "target_user_id": str(promo.target_user_id),
            },
        )


def activate_promo(db: Session, promo_id: UUID, user: User) -> PromoActivation:
    """активирует промокод"""

    current_time = now_msk()
    promo = (
        db.execute(
            select(PromoCode)
            .options(joinedload(PromoCode.campaign))
            .where(PromoCode.id == promo_id)
            .with_for_update()
        )
        .unique()
        .scalar_one_or_none()
    )
    if promo is None:
        raise NotFoundError(
            "promo_not_found",
            "промокод не найден",
            {"promo_id": str(promo_id)},
        )

    validate_activation(promo, user, current_time)

    total_activations = db.execute(
        select(func.count(PromoActivation.id)).where(
            PromoActivation.promo_id == promo.id
        )
    ).scalar_one()
    if (
        promo.max_activations is not None
        and total_activations >= promo.max_activations
    ):
        raise ConflictError(
            "promo_max_activations_exceeded",
            "достигнут общий лимит активаций промокода",
            {
                "promo_id": str(promo.id),
                "max_activations": promo.max_activations,
            },
        )

    user_activations = db.execute(
        select(func.count(PromoActivation.id)).where(
            PromoActivation.promo_id == promo.id,
            PromoActivation.user_id == user.id,
        )
    ).scalar_one()
    if user_activations >= promo.per_user_limit:
        raise ConflictError(
            "promo_per_user_limit_exceeded",
            "достигнут лимит активаций промокода на пользователя",
            {
                "promo_id": str(promo.id),
                "per_user_limit": promo.per_user_limit,
            },
        )

    activation = PromoActivation(
        user_id=user.id,
        promo_id=promo.id,
        campaign_id=promo.campaign_id,
        applied_bonus_points=promo.bonus_points,
        promo_code_snapshot=promo.code,
        promo_description_snapshot=promo.description,
        promo_type_snapshot=promo.promo_type.value,
        campaign_name_snapshot=promo.campaign.name,
    )
    db.add(activation)
    db.commit()
    db.refresh(activation)
    return activation


def list_my_activations(db: Session, user: User) -> list[PromoActivation]:
    """возвращает активации текущего пользователя"""

    query = (
        select(PromoActivation)
        .where(PromoActivation.user_id == user.id)
        .order_by(PromoActivation.activated_at.desc())
    )
    return list(db.execute(query).scalars().all())


def list_all_activations(db: Session) -> list[PromoActivation]:
    """возвращает все активации"""

    query = select(PromoActivation).order_by(
        PromoActivation.activated_at.desc()
    )
    return list(db.execute(query).scalars().all())
