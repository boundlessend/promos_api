from app.models.promo_code import PromoCode, PromoType


def test_user_sees_only_available_promos(client, seed_data, auth_headers):
    response = client.get(
        "/api/promos", headers=auth_headers("user@example.com", "user123")
    )

    assert response.status_code == 200
    codes = {item["code"] for item in response.json()}
    assert "GENERIC100" in codes
    assert "PERSONAL500" in codes
    assert "INACTIVE50" not in codes
    assert "OLD10" not in codes


def test_user_cannot_see_another_users_personal_promo(
    client, seed_data, auth_headers
):
    response = client.get(
        f"/api/promos/{seed_data['personal_promo'].id}",
        headers=auth_headers("stranger@example.com", "stranger123"),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "promo_not_found"


def test_activate_generic_promo_success(client, seed_data, auth_headers):
    headers = auth_headers("user@example.com", "user123")
    response = client.post(
        f"/api/promos/{seed_data['generic_promo'].id}/activate",
        headers=headers,
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["applied_bonus_points"] == 100
    assert payload["promo_code_snapshot"] == "GENERIC100"

    my_activations = client.get("/api/promos/activations/my", headers=headers)
    assert my_activations.status_code == 200
    assert len(my_activations.json()) == 1


def test_activate_personal_promo_by_wrong_user_fails(
    client, seed_data, auth_headers
):
    response = client.post(
        f"/api/promos/{seed_data['personal_promo'].id}/activate",
        headers=auth_headers("stranger@example.com", "stranger123"),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "promo_for_another_user"


def test_activate_beyond_per_user_limit_fails(client, seed_data, auth_headers):
    headers = auth_headers("user@example.com", "user123")
    first = client.post(
        f"/api/promos/{seed_data['generic_promo'].id}/activate",
        headers=headers,
    )
    second = client.post(
        f"/api/promos/{seed_data['generic_promo'].id}/activate",
        headers=headers,
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "promo_per_user_limit_exceeded"


def test_activate_promo_in_expired_campaign_fails(
    client, seed_data, auth_headers
):
    response = client.post(
        f"/api/promos/{seed_data['expired_campaign_promo'].id}/activate",
        headers=auth_headers("user@example.com", "user123"),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "campaign_expired"


def test_admin_can_create_and_disable_promo(client, seed_data, auth_headers):
    headers = auth_headers("admin@example.com", "admin123")
    create_response = client.post(
        "/api/promos",
        headers=headers,
        json={
            "campaign_id": str(seed_data["active_campaign"].id),
            "code": "ADMIN200",
            "description": "created by admin",
            "promo_type": "generic",
            "bonus_points": 200,
            "is_active": True,
            "starts_at": None,
            "expires_at": None,
            "max_activations": 10,
            "per_user_limit": 1,
            "target_user_id": None,
        },
    )
    assert create_response.status_code == 201, create_response.text

    promo_id = create_response.json()["id"]
    disable_response = client.post(
        f"/api/promos/{promo_id}/disable", headers=headers
    )

    assert disable_response.status_code == 200
    assert disable_response.json()["is_active"] is False


def test_admin_cannot_change_critical_fields_after_activation(
    client, db_session, seed_data, auth_headers
):
    headers = auth_headers("user@example.com", "user123")
    activate_response = client.post(
        f"/api/promos/{seed_data['personal_promo'].id}/activate",
        headers=headers,
    )
    assert activate_response.status_code == 201

    admin_headers = auth_headers("admin@example.com", "admin123")
    patch_response = client.patch(
        f"/api/promos/{seed_data['personal_promo'].id}",
        headers=admin_headers,
        json={"promo_type": "generic", "target_user_id": None},
    )

    assert patch_response.status_code == 409
    assert (
        patch_response.json()["error"]["code"]
        == "promo_immutable_after_activation"
    )


def test_invalid_dates_on_campaign_create_returns_422(
    client, seed_data, auth_headers
):
    response = client.post(
        "/api/promo-campaigns",
        headers=auth_headers("admin@example.com", "admin123"),
        json={
            "name": "broken",
            "is_active": True,
            "starts_at": "2026-05-10T10:00:00+03:00",
            "expires_at": "2026-05-01T10:00:00+03:00",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_admin_sees_history_in_promo_details(client, seed_data, auth_headers):
    headers = auth_headers("admin@example.com", "admin123")
    create_response = client.post(
        "/api/promos",
        headers=headers,
        json={
            "campaign_id": str(seed_data["active_campaign"].id),
            "code": "HISTORY10",
            "description": "history promo",
            "promo_type": "generic",
            "bonus_points": 10,
            "is_active": True,
            "starts_at": None,
            "expires_at": None,
            "max_activations": 5,
            "per_user_limit": 1,
            "target_user_id": None,
        },
    )
    assert create_response.status_code == 201
    promo_id = create_response.json()["id"]

    detail_response = client.get(f"/api/promos/{promo_id}", headers=headers)
    assert detail_response.status_code == 200
    assert len(detail_response.json()["history"]) == 1
    assert detail_response.json()["history"][0]["action"] == "created"


def test_admin_cannot_update_promo_with_duplicate_code(
    client, seed_data, auth_headers
):
    headers = auth_headers("admin@example.com", "admin123")
    create_response = client.post(
        "/api/promos",
        headers=headers,
        json={
            "campaign_id": str(seed_data["active_campaign"].id),
            "code": "UNIQUE700",
            "description": "created by admin",
            "promo_type": "generic",
            "bonus_points": 200,
            "is_active": True,
            "starts_at": None,
            "expires_at": None,
            "max_activations": 10,
            "per_user_limit": 1,
            "target_user_id": None,
        },
    )
    assert create_response.status_code == 201, create_response.text

    promo_id = create_response.json()["id"]
    update_response = client.patch(
        f"/api/promos/{promo_id}",
        headers=headers,
        json={"code": "GENERIC100"},
    )

    assert update_response.status_code == 409
    assert (
        update_response.json()["error"]["code"] == "promo_code_already_exists"
    )


def test_activate_promo_does_not_fail_on_row_lock_query(
    client, seed_data, auth_headers
):
    response = client.post(
        f"/api/promos/{seed_data['personal_promo'].id}/activate",
        headers=auth_headers("user@example.com", "user123"),
    )

    assert response.status_code == 201
    assert response.json()["promo_code_snapshot"] == "PERSONAL500"
