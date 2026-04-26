from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_user
from app.core.db import get_db
from app.models.promo_code import PromoType
from app.models.user import User
from app.schemas.promo import (
    PromoActivationRead,
    PromoCreate,
    PromoRead,
    PromoReadDetailed,
    PromoUpdate,
)
from app.services.promo_service import (
    activate_promo,
    create_promo,
    disable_promo,
    get_promo_or_404,
    get_visible_promo,
    list_all_activations,
    list_my_activations,
    list_promos,
    update_promo,
)

router = APIRouter(prefix="/promos", tags=["promos"])


@router.post("", response_model=PromoRead, status_code=status.HTTP_201_CREATED)
def create_promo_endpoint(
    payload: PromoCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> PromoRead:
    """создает промокод"""

    promo = create_promo(db, payload, admin)
    return PromoRead.model_validate(promo)


@router.patch(
    "/{promo_id}", response_model=PromoRead, status_code=status.HTTP_200_OK
)
def update_promo_endpoint(
    promo_id: UUID,
    payload: PromoUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> PromoRead:
    """обновляет промокод"""

    promo = get_promo_or_404(db, promo_id)
    promo = update_promo(db, promo, payload, admin)
    return PromoRead.model_validate(promo)


@router.post(
    "/{promo_id}/disable",
    response_model=PromoRead,
    status_code=status.HTTP_200_OK,
)
def disable_promo_endpoint(
    promo_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> PromoRead:
    """отключает промокод"""

    promo = get_promo_or_404(db, promo_id)
    promo = disable_promo(db, promo, admin)
    return PromoRead.model_validate(promo)


@router.get(
    "/activations/my",
    response_model=list[PromoActivationRead],
    status_code=status.HTTP_200_OK,
)
def list_my_activations_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PromoActivationRead]:
    """возвращает активации текущего пользователя"""

    activations = list_my_activations(db, user)
    return [PromoActivationRead.model_validate(item) for item in activations]


@router.get(
    "/activations",
    response_model=list[PromoActivationRead],
    status_code=status.HTTP_200_OK,
)
def list_all_activations_endpoint(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> list[PromoActivationRead]:
    """возвращает все активации"""

    activations = list_all_activations(db)
    return [PromoActivationRead.model_validate(item) for item in activations]


@router.get("", response_model=list[PromoRead], status_code=status.HTTP_200_OK)
def list_promos_endpoint(
    promo_type: PromoType | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    campaign_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[PromoRead]:
    """возвращает список промокодов"""

    promos = list_promos(
        db,
        user,
        promo_type=promo_type,
        is_active=is_active,
        campaign_id=campaign_id,
    )
    return [PromoRead.model_validate(promo) for promo in promos]


@router.get(
    "/{promo_id}",
    response_model=PromoReadDetailed,
    status_code=status.HTTP_200_OK,
)
def get_promo_endpoint(
    promo_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PromoReadDetailed:
    """возвращает промокод"""

    promo = get_visible_promo(db, promo_id, user)
    history = sorted(
        getattr(promo, "history_entries", []),
        key=lambda item: item.changed_at,
        reverse=True,
    )
    payload = PromoReadDetailed.model_validate(promo)
    if user.is_admin:
        payload.history = [item for item in history]
    return payload


@router.post(
    "/{promo_id}/activate",
    response_model=PromoActivationRead,
    status_code=status.HTTP_201_CREATED,
)
def activate_promo_endpoint(
    promo_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PromoActivationRead:
    """активирует промокод"""

    activation = activate_promo(db, promo_id, user)
    return PromoActivationRead.model_validate(activation)
