from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.deps import get_db
from app.core.db import Base
from app.core.security import get_password_hash
from app.main import app
from app.models.promo_campaign import PromoCampaign
from app.models.promo_code import PromoCode, PromoType
from app.models.user import User
from app.utils.time import now_msk


@pytest.fixture()
def db_session(tmp_path):
    database_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite+pysqlite:///{database_path}", future=True)
    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def seed_data(db_session):
    admin = User(
        email="admin@example.com",
        username="admin",
        hashed_password=get_password_hash("admin123"),
        is_active=True,
        is_admin=True,
    )
    user = User(
        email="user@example.com",
        username="user",
        hashed_password=get_password_hash("user123"),
        is_active=True,
        is_admin=False,
    )
    stranger = User(
        email="stranger@example.com",
        username="stranger",
        hashed_password=get_password_hash("stranger123"),
        is_active=True,
        is_admin=False,
    )
    now = now_msk()
    active_campaign = PromoCampaign(
        name="active campaign",
        is_active=True,
        starts_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=30),
    )
    expired_campaign = PromoCampaign(
        name="expired campaign",
        is_active=True,
        starts_at=now - timedelta(days=30),
        expires_at=now - timedelta(days=1),
    )
    db_session.add_all(
        [admin, user, stranger, active_campaign, expired_campaign]
    )
    db_session.flush()

    generic_promo = PromoCode(
        campaign_id=active_campaign.id,
        code="GENERIC100",
        description="generic promo",
        promo_type=PromoType.generic,
        bonus_points=100,
        is_active=True,
        starts_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=10),
        max_activations=5,
        per_user_limit=1,
    )
    personal_promo = PromoCode(
        campaign_id=active_campaign.id,
        target_user_id=user.id,
        code="PERSONAL500",
        description="personal promo",
        promo_type=PromoType.personal,
        bonus_points=500,
        is_active=True,
        starts_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=10),
        max_activations=5,
        per_user_limit=2,
    )
    inactive_promo = PromoCode(
        campaign_id=active_campaign.id,
        code="INACTIVE50",
        description="inactive promo",
        promo_type=PromoType.generic,
        bonus_points=50,
        is_active=False,
        starts_at=now - timedelta(days=1),
        expires_at=now + timedelta(days=10),
        max_activations=5,
        per_user_limit=1,
    )
    expired_campaign_promo = PromoCode(
        campaign_id=expired_campaign.id,
        code="OLD10",
        description="expired campaign promo",
        promo_type=PromoType.generic,
        bonus_points=10,
        is_active=True,
        starts_at=now - timedelta(days=30),
        expires_at=now + timedelta(days=10),
        max_activations=5,
        per_user_limit=1,
    )
    db_session.add_all(
        [generic_promo, personal_promo, inactive_promo, expired_campaign_promo]
    )
    db_session.commit()

    return {
        "admin": admin,
        "user": user,
        "stranger": stranger,
        "active_campaign": active_campaign,
        "expired_campaign": expired_campaign,
        "generic_promo": generic_promo,
        "personal_promo": personal_promo,
        "inactive_promo": inactive_promo,
        "expired_campaign_promo": expired_campaign_promo,
    }


@pytest.fixture()
def auth_headers(client):
    def _make(email: str, password: str):
        response = client.post(
            "/api/auth/jwt/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _make
