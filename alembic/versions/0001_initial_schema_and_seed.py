"""initial schema and seed

Revision ID: 0001_initial
Revises: None
Create Date: 2026-04-23 00:00:00
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

MOSCOW_TZ = timezone(timedelta(hours=3))


def upgrade() -> None:
    bind = op.get_bind()

    promo_type_db = postgresql.ENUM(
        "generic",
        "personal",
        name="promo_type",
    )
    promo_history_action_db = postgresql.ENUM(
        "created",
        "updated",
        "disabled",
        name="promo_history_action",
    )

    promo_type_db.create(bind, checkfirst=True)
    promo_history_action_db.create(bind, checkfirst=True)

    promo_type = postgresql.ENUM(
        "generic",
        "personal",
        name="promo_type",
        create_type=False,
    )
    promo_history_action = postgresql.ENUM(
        "created",
        "updated",
        "disabled",
        name="promo_history_action",
        create_type=False,
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=150), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "is_admin", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(
        op.f("ix_users_username"), "users", ["username"], unique=True
    )

    op.create_table(
        "promo_campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_promo_campaigns_name"),
        "promo_campaigns",
        ["name"],
        unique=False,
    )

    op.create_table(
        "promo_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("target_user_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("promo_type", promo_type, nullable=False),
        sa.Column("bonus_points", sa.Integer(), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_activations", sa.Integer(), nullable=True),
        sa.Column(
            "per_user_limit", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["promo_campaigns.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(
        op.f("ix_promo_codes_campaign_id"),
        "promo_codes",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_promo_codes_code"), "promo_codes", ["code"], unique=True
    )
    op.create_index(
        op.f("ix_promo_codes_promo_type"),
        "promo_codes",
        ["promo_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_promo_codes_target_user_id"),
        "promo_codes",
        ["target_user_id"],
        unique=False,
    )

    op.create_table(
        "promo_activations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("promo_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_bonus_points", sa.Integer(), nullable=False),
        sa.Column(
            "promo_code_snapshot", sa.String(length=100), nullable=False
        ),
        sa.Column("promo_description_snapshot", sa.Text(), nullable=True),
        sa.Column("promo_type_snapshot", sa.String(length=20), nullable=False),
        sa.Column(
            "campaign_name_snapshot", sa.String(length=255), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["promo_campaigns.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["promo_id"], ["promo_codes.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_promo_activations_activated_at"),
        "promo_activations",
        ["activated_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_promo_activations_campaign_id"),
        "promo_activations",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_promo_activations_promo_id"),
        "promo_activations",
        ["promo_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_promo_activations_user_id"),
        "promo_activations",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "promo_code_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("promo_id", sa.Uuid(), nullable=False),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("action", promo_history_action, nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("before_payload", sa.JSON(), nullable=True),
        sa.Column("after_payload", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["changed_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["promo_id"], ["promo_codes.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_promo_code_history_changed_at"),
        "promo_code_history",
        ["changed_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_promo_code_history_changed_by_user_id"),
        "promo_code_history",
        ["changed_by_user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_promo_code_history_promo_id"),
        "promo_code_history",
        ["promo_id"],
        unique=False,
    )

    users = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("email", sa.String()),
        sa.column("username", sa.String()),
        sa.column("hashed_password", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("is_admin", sa.Boolean()),
    )
    campaigns = sa.table(
        "promo_campaigns",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("starts_at", sa.DateTime(timezone=True)),
        sa.column("expires_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    promos = sa.table(
        "promo_codes",
        sa.column("id", sa.Uuid()),
        sa.column("campaign_id", sa.Uuid()),
        sa.column("target_user_id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("promo_type", promo_type),
        sa.column("bonus_points", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
        sa.column("starts_at", sa.DateTime(timezone=True)),
        sa.column("expires_at", sa.DateTime(timezone=True)),
        sa.column("max_activations", sa.Integer()),
        sa.column("per_user_limit", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    promo_history = sa.table(
        "promo_code_history",
        sa.column("id", sa.Uuid()),
        sa.column("promo_id", sa.Uuid()),
        sa.column("changed_by_user_id", sa.Uuid()),
        sa.column("action", promo_history_action),
        sa.column("changed_at", sa.DateTime(timezone=True)),
        sa.column("before_payload", sa.JSON()),
        sa.column("after_payload", sa.JSON()),
    )

    now_value = datetime(2026, 4, 23, 12, 0, tzinfo=MOSCOW_TZ)
    next_year = datetime(2027, 4, 23, 12, 0, tzinfo=MOSCOW_TZ)
    last_year = datetime(2025, 4, 23, 12, 0, tzinfo=MOSCOW_TZ)

    admin_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    active_campaign_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    expired_campaign_id = uuid.UUID("10000000-0000-0000-0000-000000000002")
    generic_promo_id = uuid.UUID("20000000-0000-0000-0000-000000000001")
    personal_promo_id = uuid.UUID("20000000-0000-0000-0000-000000000002")
    inactive_promo_id = uuid.UUID("20000000-0000-0000-0000-000000000003")

    op.bulk_insert(
        users,
        [
            {
                "id": admin_id,
                "email": "admin@example.com",
                "username": "admin",
                "hashed_password": "$2b$12$K6iVNQ6LT0yBx9DS98OWxeawM9ZRxnVTBwRQfiNi2pmxqUF5JBya6",
                "is_active": True,
                "is_admin": True,
            },
            {
                "id": user_id,
                "email": "user@example.com",
                "username": "user",
                "hashed_password": "$2b$12$rXkZMxFAWNx41ZB3o7YRzeRvLrU7oQKS4nr6YDx43kp5P4lXkFPEy",
                "is_active": True,
                "is_admin": False,
            },
        ],
    )

    op.bulk_insert(
        campaigns,
        [
            {
                "id": active_campaign_id,
                "name": "welcome campaign",
                "is_active": True,
                "starts_at": now_value - timedelta(days=7),
                "expires_at": next_year,
                "created_at": now_value,
                "updated_at": now_value,
            },
            {
                "id": expired_campaign_id,
                "name": "old campaign",
                "is_active": True,
                "starts_at": last_year - timedelta(days=30),
                "expires_at": last_year,
                "created_at": last_year,
                "updated_at": last_year,
            },
        ],
    )

    op.bulk_insert(
        promos,
        [
            {
                "id": generic_promo_id,
                "campaign_id": active_campaign_id,
                "target_user_id": None,
                "code": "WELCOME100",
                "description": "бонус для всех активных пользователей",
                "promo_type": "generic",
                "bonus_points": 100,
                "is_active": True,
                "starts_at": now_value - timedelta(days=7),
                "expires_at": next_year,
                "max_activations": 100,
                "per_user_limit": 1,
                "created_at": now_value,
                "updated_at": now_value,
            },
            {
                "id": personal_promo_id,
                "campaign_id": active_campaign_id,
                "target_user_id": user_id,
                "code": "PERSONAL500",
                "description": "персональный бонус для demo user",
                "promo_type": "personal",
                "bonus_points": 500,
                "is_active": True,
                "starts_at": now_value - timedelta(days=1),
                "expires_at": next_year,
                "max_activations": 2,
                "per_user_limit": 2,
                "created_at": now_value,
                "updated_at": now_value,
            },
            {
                "id": inactive_promo_id,
                "campaign_id": active_campaign_id,
                "target_user_id": None,
                "code": "PAUSED50",
                "description": "деактивированный промокод для негативных сценариев",
                "promo_type": "generic",
                "bonus_points": 50,
                "is_active": False,
                "starts_at": now_value - timedelta(days=7),
                "expires_at": next_year,
                "max_activations": 50,
                "per_user_limit": 1,
                "created_at": now_value,
                "updated_at": now_value,
            },
        ],
    )

    op.bulk_insert(
        promo_history,
        [
            {
                "id": uuid.UUID("30000000-0000-0000-0000-000000000001"),
                "promo_id": generic_promo_id,
                "changed_by_user_id": admin_id,
                "action": "created",
                "changed_at": now_value,
                "before_payload": None,
                "after_payload": {
                    "code": "WELCOME100",
                    "promo_type": "generic",
                    "bonus_points": 100,
                    "is_active": True,
                    "per_user_limit": 1,
                },
            },
            {
                "id": uuid.UUID("30000000-0000-0000-0000-000000000002"),
                "promo_id": personal_promo_id,
                "changed_by_user_id": admin_id,
                "action": "created",
                "changed_at": now_value,
                "before_payload": None,
                "after_payload": {
                    "code": "PERSONAL500",
                    "promo_type": "personal",
                    "bonus_points": 500,
                    "is_active": True,
                    "per_user_limit": 2,
                    "target_user_id": str(user_id),
                },
            },
            {
                "id": uuid.UUID("30000000-0000-0000-0000-000000000003"),
                "promo_id": inactive_promo_id,
                "changed_by_user_id": admin_id,
                "action": "created",
                "changed_at": now_value,
                "before_payload": None,
                "after_payload": {
                    "code": "PAUSED50",
                    "promo_type": "generic",
                    "bonus_points": 50,
                    "is_active": False,
                    "per_user_limit": 1,
                },
            },
        ],
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index(
        op.f("ix_promo_code_history_promo_id"), table_name="promo_code_history"
    )
    op.drop_index(
        op.f("ix_promo_code_history_changed_by_user_id"),
        table_name="promo_code_history",
    )
    op.drop_index(
        op.f("ix_promo_code_history_changed_at"),
        table_name="promo_code_history",
    )
    op.drop_table("promo_code_history")

    op.drop_index(
        op.f("ix_promo_activations_user_id"), table_name="promo_activations"
    )
    op.drop_index(
        op.f("ix_promo_activations_promo_id"), table_name="promo_activations"
    )
    op.drop_index(
        op.f("ix_promo_activations_campaign_id"),
        table_name="promo_activations",
    )
    op.drop_index(
        op.f("ix_promo_activations_activated_at"),
        table_name="promo_activations",
    )
    op.drop_table("promo_activations")

    op.drop_index(
        op.f("ix_promo_codes_target_user_id"), table_name="promo_codes"
    )
    op.drop_index(op.f("ix_promo_codes_promo_type"), table_name="promo_codes")
    op.drop_index(op.f("ix_promo_codes_code"), table_name="promo_codes")
    op.drop_index(op.f("ix_promo_codes_campaign_id"), table_name="promo_codes")
    op.drop_table("promo_codes")

    op.drop_index(
        op.f("ix_promo_campaigns_name"), table_name="promo_campaigns"
    )
    op.drop_table("promo_campaigns")

    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    postgresql.ENUM(name="promo_history_action").drop(bind, checkfirst=True)
    postgresql.ENUM(name="promo_type").drop(bind, checkfirst=True)
