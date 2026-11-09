from app.core.config import settings
from app.core.security import create_email_verification_token
from app.core.rate_limit import login_rate_limiter
from app.services import auth_service


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["database"]["ready"] is True


def test_register_login_me(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"full_name": "  Reza  ", "email": "REZA@Gmail.com", "password": "S!N7mQ2x",
              "password_confirmation": "S!N7mQ2x"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "reza@gmail.com"
    assert body["user"]["full_name"] == "Reza"

    dup = client.post("/api/v1/auth/register", json={"full_name": "R", "email": "reza@gmail.com", "password": "x" * 8})
    assert dup.status_code in (409, 422)

    bad = client.post("/api/v1/auth/login", json={"email": "reza@gmail.com", "password": "salah1234"})
    assert bad.status_code == 401
    assert bad.json()["code"] == "INVALID_CREDENTIALS"

    ok = client.post("/api/v1/auth/login", json={"email": "Reza@gmail.com", "password": "S!N7mQ2x"})
    assert ok.status_code == 200
    token = ok.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "reza@gmail.com"

    form = client.post("/api/v1/auth/token", data={"username": "reza@gmail.com", "password": "S!N7mQ2x"})
    assert form.status_code == 200


def test_register_validation_message(client):
    r = client.post(
        "/api/v1/auth/register",
        json={"full_name": "A B", "email": "a@b.com", "password": "S!N7mQ2x", "password_confirmation": "beda12345"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"
    assert "Konfirmasi password" in r.json()["detail"]


def test_requires_token(client):
    r = client.get("/api/v1/receipts")
    assert r.status_code == 401
    assert r.json()["code"] == "NOT_AUTHENTICATED"
    r = client.get("/api/v1/receipts", headers={"Authorization": "Bearer palsu"})
    assert r.json()["code"] == "INVALID_TOKEN"


def test_update_profile_and_password(client, auth):
    r = client.patch("/api/v1/users/me", json={"full_name": "Nama Baru"}, headers=auth)
    assert r.json()["full_name"] == "Nama Baru"
    r = client.post(
        "/api/v1/users/me/password",
        json={"current_password": "salah", "new_password": "passwordbaru"},
        headers=auth,
    )
    assert r.status_code == 400
    r = client.post(
        "/api/v1/users/me/password",
        json={"current_password": "S!N7mQ2x", "new_password": "V!N8pR3z"},
        headers=auth,
    )
    assert r.status_code == 200


def test_login_is_rate_limited_by_email_and_ip(client):
    email = "limited@example.com"
    for attempt in range(5):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "salah-sekali"},
        )
        assert r.status_code == 401

    limited = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "salah-sekali"},
    )
    assert limited.status_code == 429
    assert limited.json()["code"] == "TOO_MANY_REQUESTS"
    assert "Retry-After" in limited.headers


def test_email_verification_blocks_login_until_verified(client, monkeypatch):
    monkeypatch.setattr(settings, "REQUIRE_EMAIL_VERIFICATION", True)

    registered = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Pengguna Verifikasi",
            "email": "verify-stage@example.com",
            "password": "S!N7mQ2x",
        },
    )
    assert registered.status_code == 201
    assert registered.json()["email_verification_required"] is True
    user_id = registered.json()["user"]["id"]

    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "verify-stage@example.com", "password": "S!N7mQ2x"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "EMAIL_NOT_VERIFIED"

    token = create_email_verification_token(user_id)
    verified = client.get("/api/v1/auth/verify-email", params={"token": token})
    assert verified.status_code == 200

    allowed = client.post(
        "/api/v1/auth/login",
        json={"email": "verify-stage@example.com", "password": "S!N7mQ2x"},
    )
    assert allowed.status_code == 200


def test_forgot_password_token_is_single_use(client, monkeypatch):
    login_rate_limiter.reset()
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Pengguna Reset",
            "email": "reset-stage@example.com",
            "password": "passwordlama123",
        },
    )
    assert registered.status_code == 201

    captured = {}

    def capture_reset_email(user, token):
        captured["token"] = token
        return True

    monkeypatch.setattr(auth_service, "send_password_reset_email", capture_reset_email)
    requested = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "reset-stage@example.com"},
    )
    assert requested.status_code == 200
    assert captured["token"]

    reset = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": captured["token"],
            "new_password": "passwordbaru123",
            "new_password_confirmation": "passwordbaru123",
        },
    )
    assert reset.status_code == 200

    reused = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": captured["token"],
            "new_password": "passwordketiga123",
        },
    )
    assert reused.status_code == 400
    assert reused.json()["code"] == "INVALID_RESET_TOKEN"

    old_password = client.post(
        "/api/v1/auth/login",
        json={"email": "reset-stage@example.com", "password": "passwordlama123"},
    )
    assert old_password.status_code == 401

    new_password = client.post(
        "/api/v1/auth/login",
        json={"email": "reset-stage@example.com", "password": "passwordbaru123"},
    )
    assert new_password.status_code == 200


def test_password_policy_rejects_common_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Pengguna Lemah",
            "email": "weak-password@example.com",
            "password": "rahasia123",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "terlalu umum" in response.json()["detail"]


def test_password_strength_endpoint_returns_level(client):
    weak = client.post(
        "/api/v1/auth/password-strength",
        json={"password": "12345678"},
    )
    assert weak.status_code == 200
    assert weak.json()["level"] == "weak"

    strong = client.post(
        "/api/v1/auth/password-strength",
        json={"password": "S!N7mQ2x#L9"},
    )
    assert strong.status_code == 200
    assert strong.json()["score"] >= 4
    assert strong.json()["level"] in ("good", "strong")


def test_security_audit_events(client, auth):
    failed = client.post(
        "/api/v1/auth/login",
        json={"email": "audit@example.com", "password": "Salah123!"},
        headers={"user-agent": "Audit-Client/1.0"},
    )
    assert failed.status_code == 401

    changed_password = client.post(
        "/api/v1/users/me/password",
        json={"current_password": "salah", "new_password": "V!N8pR3z"},
        headers={**auth, "user-agent": "Audit-Client/1.0"},
    )
    assert changed_password.status_code == 400

    changed_password = client.post(
        "/api/v1/users/me/password",
        json={"current_password": "S!N7mQ2x", "new_password": "V!N8pR3z"},
        headers={**auth, "user-agent": "Audit-Client/1.0"},
    )
    assert changed_password.status_code == 200

    relogged = client.post(
        "/api/v1/auth/login",
        json={"email": "test_security_audit_events@example.com", "password": "V!N8pR3z"},
    )
    assert relogged.status_code == 200
    auth = {"Authorization": f"Bearer {relogged.json()['access_token']}"}

    updated_email = client.patch(
        "/api/v1/users/me",
        json={"email": "audit-updated@example.com"},
        headers={**auth, "user-agent": "Audit-Client/1.0"},
    )
    assert updated_email.status_code == 200

    events_response = client.get(
        "/api/v1/auth/security-events",
        headers=auth,
    )
    assert events_response.status_code == 200
    events = events_response.json()
    event_types = {event["event_type"] for event in events}
    assert "PASSWORD_CHANGE_FAILED" in event_types
    assert "PASSWORD_CHANGED" in event_types
    assert "EMAIL_UPDATED" in event_types


def test_refresh_session_logout_and_password_revocation(client):
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Pengguna Token",
            "email": "token-stage@example.com",
            "password": "S!N7mQ2x#K4",
        },
    )
    assert registered.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "token-stage@example.com", "password": "S!N7mQ2x#K4"},
    )
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]
    access_token = login.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {access_token}"}

    sessions = client.get("/api/v1/auth/sessions", headers=auth_header)
    assert sessions.status_code == 200
    assert len(sessions.json()) >= 1

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refreshed.status_code == 200
    new_refresh_token = refreshed.json()["refresh_token"]
    assert new_refresh_token != refresh_token

    reused = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert reused.status_code == 401
    assert reused.json()["code"] == "INVALID_REFRESH_TOKEN"

    logged_out = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_refresh_token},
        headers=auth_header,
    )
    assert logged_out.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "token-stage@example.com", "password": "S!N7mQ2x#K4"},
    )
    assert login.status_code == 200
    refresh_token = login.json()["refresh_token"]
    access_token = login.json()["access_token"]
    auth_header = {"Authorization": f"Bearer {access_token}"}

    changed = client.post(
        "/api/v1/users/me/password",
        json={"current_password": "S!N7mQ2x#K4", "new_password": "V!N8pR3z#K9"},
        headers=auth_header,
    )
    assert changed.status_code == 200

    revoked = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert revoked.status_code == 401

    revoked_access = client.get("/api/v1/auth/me", headers=auth_header)
    assert revoked_access.status_code == 401
