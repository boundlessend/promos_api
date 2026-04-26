from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_user
from app.core.db import get_db
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignRead, CampaignUpdate
from app.services.promo_service import (
    create_campaign,
    get_campaign_or_404,
    list_campaigns,
    update_campaign,
)

router = APIRouter(prefix="/promo-campaigns", tags=["promo-campaigns"])


@router.post(
    "", response_model=CampaignRead, status_code=status.HTTP_201_CREATED
)
def create_campaign_endpoint(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> CampaignRead:
    """создает кампанию"""

    campaign = create_campaign(db, payload)
    return CampaignRead.model_validate(campaign)


@router.patch(
    "/{campaign_id}",
    response_model=CampaignRead,
    status_code=status.HTTP_200_OK,
)
def update_campaign_endpoint(
    campaign_id: UUID,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
) -> CampaignRead:
    """обновляет кампанию"""

    campaign = get_campaign_or_404(db, campaign_id)
    campaign = update_campaign(db, campaign, payload)
    return CampaignRead.model_validate(campaign)


@router.get(
    "", response_model=list[CampaignRead], status_code=status.HTTP_200_OK
)
def list_campaigns_endpoint(
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CampaignRead]:
    """возвращает список кампаний"""

    campaigns = list_campaigns(db, user, is_active=is_active)
    return [CampaignRead.model_validate(campaign) for campaign in campaigns]
