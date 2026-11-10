from datetime import timedelta
import json
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app import db
from app.models import AuthSession, AuthToken, Business, BusinessMembership, User
from app.services.auth_service import (
    EMAIL_VERIFICATION,
    LOGIN_OTP,
    PASSWORD_RESET,
    create_session,
    utc_now,
)

AUTH_URL = "/api/v1/auth"
PASSWORD = "a-very-long-test-password"


def register_account(client, csrf_headers, email="owner@example.com", **overrides):
    payload = {
        "name": "Business Owner",
        "email": email,
        "password": PASSWORD,
        "confirm_password": PASSWORD,
        "business_name": "Example Business",
    }
    payload.update(overrides)
    return client.post(f"{AUTH_URL}/register", headers=csrf_headers, json=payload)


def verify_account(client, csrf_headers, email, code):
    return client.post(
        f"{AUTH_URL}/email-verifications",
        headers=csrf_headers,
        json={"email": email, "code": code},
    )


def create_verified_account(client, csrf_headers, sent_account_emails, email="owner@example.com"):
    response = register_account(client, csrf_headers, email=email)
    assert response.status_code == 202
    address, purpose, code = sent_account_emails.pop()
    assert address == email
    assert purpose == EMAIL_VERIFICATION
    return code


def request_password_code(client, csrf_headers, email="owner@example.com"):
    return client.post(
        f"{AUTH_URL}/password-reset-requests",
        headers=csrf_headers,
        json={"email": email},
    )


def test_registration_verification_login_session_and_logout(
    app, client, csrf_headers, sent_account_emails
):
    response = register_account(client, csrf_headers)

    assert response.status_code == 202
    assert "code" not in response.get_json()
    assert len(sent_account_emails) == 1
    email, purpose, code = sent_account_emails.pop()
    assert email == "owner@example.com"
    assert purpose == EMAIL_VERIFICATION
    assert len(code) == 6 and code.isdigit()

    with app.app_context():
        token = db.session.execute(select(AuthToken)).scalar_one()
        assert token.token_hash != code
        assert token.attempts == 0
        assert abs(
            (token.expires_at.replace(tzinfo=None) - token.created_at.replace(tzinfo=None))
            - timedelta(minutes=10)
        ) < timedelta(seconds=1)

    verified = verify_account(client, csrf_headers, email, code)
    assert verified.status_code == 200
    assert verified.get_json()["user"]["businesses"][0]["role"] == "owner"
    assert "HttpOnly" in verified.headers["Set-Cookie"]
    assert "SameSite=Lax" in verified.headers["Set-Cookie"]
    assert "Max-Age=" not in verified.headers["Set-Cookie"]
    assert client.get(f"{AUTH_URL}/me").status_code == 200
    assert verify_account(client, csrf_headers, email, code).status_code == 400

    assert client.post(f"{AUTH_URL}/logout", headers=csrf_headers).status_code == 200
    assert client.get(f"{AUTH_URL}/me").status_code == 401
    with app.app_context():
        session = db.session.execute(select(AuthSession)).scalar_one()
        assert session.revoked_at is not None

    login = client.post(
        f"{AUTH_URL}/login",
        headers=csrf_headers,
        json={"email": "OWNER@example.com", "password": PASSWORD, "remember_me": True},
    )
    assert login.status_code == 202
    assert "Set-Cookie" not in login.headers
    challenge_id = login.get_json()["challenge_id"]
    login_email, purpose, login_code = sent_account_emails.pop()
    assert login_email == email
    assert purpose == LOGIN_OTP
    with app.app_context():
        token = db.session.get(AuthToken, challenge_id)
        assert token.token_hash != login_code
        assert token.remember_me is True

    completed = client.post(
        f"{AUTH_URL}/otp/verify",
        headers=csrf_headers,
        json={"challenge_id": challenge_id, "code": login_code},
    )
    assert completed.status_code == 200
    assert "Max-Age=" in completed.headers["Set-Cookie"]
    assert "HttpOnly" in completed.headers["Set-Cookie"]
    assert completed.get_json()["user"]["email"] == email


def test_registration_rejects_duplicates_invalid_email_and_invalid_password(
    client, csrf_headers, sent_account_emails
):
    create_verified_account(client, csrf_headers, sent_account_emails)

    duplicate = register_account(client, csrf_headers, email="OWNER@example.com")
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "email_already_registered"

    invalid_email = register_account(client, csrf_headers, email="not-an-email")
    assert invalid_email.status_code == 400
    invalid_password = register_account(
        client, csrf_headers, email="short@example.com", password="short"
    )
    assert invalid_password.status_code == 400
    mismatched_password = register_account(
        client,
        csrf_headers,
        email="mismatch@example.com",
        confirm_password="different-password",
    )
    assert mismatched_password.status_code == 400


def test_registration_delivery_failure_rolls_back_account(
    app, client, csrf_headers
):
    from app.services.email_service import EmailDeliveryError

    def reject_delivery(*_args):
        raise EmailDeliveryError("transport unavailable")

    app.config["AUTH_EMAIL_SENDER"] = reject_delivery
    response = register_account(client, csrf_headers)
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "email_delivery_failed"
    assert "code" not in response.get_json()

    with app.app_context():
        assert db.session.execute(select(User)).scalars().all() == []
        assert db.session.execute(select(AuthToken)).scalars().all() == []


def test_account_otp_uses_resend_api_and_html_template(app, monkeypatch):
    from app.services import email_service

    captured = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        captured["message"] = json.loads(request.data.decode("utf-8"))
        return Response()

    monkeypatch.setattr(email_service, "urlopen", fake_urlopen)
    app.config.update(
        AUTH_EMAIL_SENDER=None,
        RESEND_API_KEY="test-resend-key",
        MAIL_FROM="noreply@example.test",
    )

    with app.app_context():
        email_service.send_account_token(
            SimpleNamespace(email="owner@example.test", display_name="Business Owner"),
            LOGIN_OTP,
            "012345",
        )

    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["authorization"] == "Bearer test-resend-key"
    assert captured["timeout"] == 15
    assert captured["message"]["to"] == ["owner@example.test"]
    assert captured["message"]["from"] == "STEER <noreply@example.test>"
    assert "012345" in captured["message"]["html"]
    assert "expires in <strong>10 minutes</strong>" in captured["message"]["html"]


def test_invalid_registration_is_validated_before_email_configuration(client, csrf_headers):
    response = client.post(
        f"{AUTH_URL}/register",
        headers=csrf_headers,
        json={"email": "invalid"},
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "validation_error"


def test_unverified_account_cannot_login_and_can_resend_code(
    client, csrf_headers, sent_account_emails
):
    register_account(client, csrf_headers)
    sent_account_emails.pop()
    login = client.post(
        f"{AUTH_URL}/login",
        headers=csrf_headers,
        json={"email": "owner@example.com", "password": PASSWORD},
    )
    assert login.status_code == 403
    assert login.get_json()["error"]["code"] == "email_not_verified"
    assert client.get(f"{AUTH_URL}/me").status_code == 401

    response = client.post(
        f"{AUTH_URL}/verification-requests",
        headers=csrf_headers,
        json={"email": "owner@example.com"},
    )
    assert response.status_code == 202
    assert "code" not in response.get_json()


def test_wrong_otp_attempts_are_limited_and_valid_otp_becomes_unusable(
    app, client, csrf_headers, sent_account_emails
):
    code = create_verified_account(client, csrf_headers, sent_account_emails)
    for _ in range(app.config["AUTH_OTP_MAX_ATTEMPTS"]):
        response = verify_account(client, csrf_headers, "owner@example.com", "000000" if code != "000000" else "000001")
        assert response.status_code == 400
        assert code not in response.get_data(as_text=True)

    assert verify_account(client, csrf_headers, "owner@example.com", code).status_code == 400
    with app.app_context():
        token = db.session.execute(select(AuthToken)).scalar_one()
        assert token.attempts == app.config["AUTH_OTP_MAX_ATTEMPTS"]


def test_expired_otp_is_rejected(client, app, csrf_headers, sent_account_emails):
    code = create_verified_account(client, csrf_headers, sent_account_emails)
    with app.app_context():
        token = db.session.execute(select(AuthToken)).scalar_one()
        token.expires_at = (utc_now() - timedelta(seconds=1)).replace(tzinfo=None)
        db.session.commit()

    assert verify_account(client, csrf_headers, "owner@example.com", code).status_code == 400


def test_otp_cooldown_resend_rotates_code_and_rejects_old_code(
    client, app, csrf_headers, sent_account_emails
):
    old_code = create_verified_account(client, csrf_headers, sent_account_emails)
    cooldown = client.post(
        f"{AUTH_URL}/verification-requests",
        headers=csrf_headers,
        json={"email": "owner@example.com"},
    )
    assert cooldown.status_code == 202
    assert "code" not in cooldown.get_json()

    with app.app_context():
        token = db.session.execute(select(AuthToken)).scalar_one()
        token.created_at = (utc_now() - timedelta(seconds=app.config["AUTH_OTP_RESEND_SECONDS"] + 1)).replace(tzinfo=None)
        db.session.commit()

    resent = client.post(
        f"{AUTH_URL}/verification-requests",
        headers=csrf_headers,
        json={"email": "owner@example.com"},
    )
    assert resent.status_code == 202
    _, purpose, new_code = sent_account_emails.pop()
    assert purpose == EMAIL_VERIFICATION
    assert new_code != old_code
    assert verify_account(client, csrf_headers, "owner@example.com", old_code).status_code == 400
    assert verify_account(client, csrf_headers, "owner@example.com", new_code).status_code == 200


def test_password_reset_otp_purpose_attempts_and_old_session_revocation(
    client, app, csrf_headers, sent_account_emails
):
    verify_code = create_verified_account(client, csrf_headers, sent_account_emails)
    assert verify_account(client, csrf_headers, "owner@example.com", verify_code).status_code == 200
    login = client.post(
        f"{AUTH_URL}/login",
        headers=csrf_headers,
        json={"email": "owner@example.com", "password": PASSWORD},
    )
    assert login.status_code == 202
    login_challenge = login.get_json()["challenge_id"]
    _, purpose, login_code = sent_account_emails.pop()
    assert purpose == LOGIN_OTP
    login = client.post(
        f"{AUTH_URL}/otp/verify",
        headers=csrf_headers,
        json={"challenge_id": login_challenge, "code": login_code},
    )
    assert login.status_code == 200
    old_session_cookie = login.headers["Set-Cookie"].split(";", 1)[0].split("=", 1)[1]

    assert request_password_code(client, csrf_headers).status_code == 202
    email, purpose, reset_code = sent_account_emails.pop()
    assert email == "owner@example.com"
    assert purpose == PASSWORD_RESET
    assert verify_account(client, csrf_headers, email, reset_code).status_code == 400

    mismatch = client.post(
        f"{AUTH_URL}/password-resets",
        headers=csrf_headers,
        json={
            "email": email,
            "code": reset_code,
            "password": "a-different-long-password",
            "confirm_password": "not-the-same-password",
        },
    )
    assert mismatch.status_code == 400
    assert client.get(f"{AUTH_URL}/me").status_code == 200

    reset_payload = {
        "email": email,
        "code": reset_code,
        "password": "a-different-long-password",
        "confirm_password": "a-different-long-password",
    }
    reset = client.post(f"{AUTH_URL}/password-resets", headers=csrf_headers, json=reset_payload)
    assert reset.status_code == 200
    assert client.get(f"{AUTH_URL}/me").status_code == 401
    assert client.post(f"{AUTH_URL}/password-resets", headers=csrf_headers, json=reset_payload).status_code == 400

    client.set_cookie("dpbm_auth", old_session_cookie)
    assert client.get(f"{AUTH_URL}/me").status_code == 401
    wrong_password = client.post(
        f"{AUTH_URL}/login",
        headers=csrf_headers,
        json={"email": email, "password": PASSWORD},
    )
    assert wrong_password.status_code == 401

    with app.app_context():
        login_token = db.session.execute(
            select(AuthToken)
            .where(AuthToken.purpose == LOGIN_OTP)
            .order_by(AuthToken.created_at.desc())
        ).scalars().first()
        login_token.created_at = (
            utc_now() - timedelta(seconds=app.config["AUTH_OTP_RESEND_SECONDS"] + 1)
        ).replace(tzinfo=None)
        db.session.commit()

    new_password_login = client.post(
        f"{AUTH_URL}/login",
        headers=csrf_headers,
        json={"email": email, "password": "a-different-long-password"},
    )
    assert new_password_login.status_code == 202
    new_challenge = new_password_login.get_json()["challenge_id"]
    _, purpose, new_login_code = sent_account_emails.pop()
    assert purpose == LOGIN_OTP
    completed_login = client.post(
        f"{AUTH_URL}/otp/verify",
        headers=csrf_headers,
        json={"challenge_id": new_challenge, "code": new_login_code},
    )
    assert completed_login.status_code == 200

    with app.app_context():
        token = db.session.execute(
            select(AuthToken)
            .where(AuthToken.purpose == PASSWORD_RESET)
            .order_by(AuthToken.created_at.desc())
        ).scalars().first()
        assert token.used_at is not None
        assert token.token_hash != reset_code


def test_password_reset_otp_expiry_and_attempt_limit(
    client, app, csrf_headers, sent_account_emails
):
    code = create_verified_account(client, csrf_headers, sent_account_emails)
    verify_account(client, csrf_headers, "owner@example.com", code)
    assert request_password_code(client, csrf_headers).status_code == 202
    _, _, reset_code = sent_account_emails.pop()

    wrong_code = "111111" if reset_code != "111111" else "222222"
    for _ in range(app.config["AUTH_OTP_MAX_ATTEMPTS"]):
        response = client.post(
            f"{AUTH_URL}/password-resets",
            headers=csrf_headers,
            json={
                "email": "owner@example.com",
                "code": wrong_code,
                "password": "a-different-long-password",
                "confirm_password": "a-different-long-password",
            },
        )
        assert response.status_code == 400

    blocked = client.post(
        f"{AUTH_URL}/password-resets",
        headers=csrf_headers,
        json={
            "email": "owner@example.com",
            "code": reset_code,
            "password": "a-different-long-password",
            "confirm_password": "a-different-long-password",
        },
    )
    assert blocked.status_code == 400

    with app.app_context():
        token = db.session.execute(
            select(AuthToken).where(AuthToken.purpose == PASSWORD_RESET)
        ).scalars().first()
        token.created_at = (utc_now() - timedelta(seconds=app.config["AUTH_OTP_RESEND_SECONDS"] + 1)).replace(tzinfo=None)
        db.session.commit()
    assert request_password_code(client, csrf_headers).status_code == 202
    _, _, expired_code = sent_account_emails.pop()
    with app.app_context():
        token = db.session.execute(
            select(AuthToken)
            .where(
                AuthToken.purpose == PASSWORD_RESET,
                AuthToken.used_at.is_(None),
            )
            .order_by(AuthToken.created_at.desc())
        ).scalars().first()
        token.expires_at = (utc_now() - timedelta(seconds=1)).replace(tzinfo=None)
        db.session.commit()
    expired = client.post(
        f"{AUTH_URL}/password-resets",
        headers=csrf_headers,
        json={
            "email": "owner@example.com",
            "code": expired_code,
            "password": "a-different-long-password",
            "confirm_password": "a-different-long-password",
        },
    )
    assert expired.status_code == 400


def test_verification_and_otp_generation_endpoints_are_rate_limited():
    from app import create_app

    limited_app = create_app(
        {
            "APP_ENV": "testing",
            "SECRET_KEY": "otp-rate-limit-test-secret-that-is-long-enough",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "TESTING": True,
            "RATELIMIT_ENABLED": True,
        }
    )
    client = limited_app.test_client()
    csrf_token = client.get(f"{AUTH_URL}/csrf").get_json()["csrf_token"]
    headers = {"X-CSRFToken": csrf_token}

    for _ in range(3):
        response = client.post(
            f"{AUTH_URL}/verification-requests",
            headers=headers,
            json={"email": "owner@example.com"},
        )
        assert response.status_code == 503
    assert client.post(
        f"{AUTH_URL}/verification-requests",
        headers=headers,
        json={"email": "owner@example.com"},
    ).status_code == 429

    for _ in range(10):
        response = client.post(
            f"{AUTH_URL}/email-verifications",
            headers=headers,
            json={"email": "invalid", "code": "000000"},
        )
        assert response.status_code == 400
    assert client.post(
        f"{AUTH_URL}/email-verifications",
        headers=headers,
        json={"email": "invalid", "code": "000000"},
    ).status_code == 429


def test_login_rejects_wrong_password_and_supports_session_cookie(
    client, app, csrf_headers, sent_account_emails
):
    code = create_verified_account(client, csrf_headers, sent_account_emails)
    verify_account(client, csrf_headers, "owner@example.com", code)
    wrong = client.post(
        f"{AUTH_URL}/login",
        headers=csrf_headers,
        json={"email": "owner@example.com", "password": "wrong-password"},
    )
    assert wrong.status_code == 401
    assert wrong.get_json()["error"]["code"] == "invalid_credentials"

    remember_login = client.post(
        f"{AUTH_URL}/login",
        headers=csrf_headers,
        json={"email": "owner@example.com", "password": PASSWORD, "remember_me": True},
    )
    assert remember_login.status_code == 202
    challenge_id = remember_login.get_json()["challenge_id"]
    _, purpose, login_code = sent_account_emails.pop()
    assert purpose == LOGIN_OTP
    remember_login = client.post(
        f"{AUTH_URL}/otp/verify",
        headers=csrf_headers,
        json={"challenge_id": challenge_id, "code": login_code},
    )
    assert remember_login.status_code == 200
    assert "Max-Age=" in remember_login.headers["Set-Cookie"]
    assert "HttpOnly" in remember_login.headers["Set-Cookie"]
    assert "SameSite=Lax" in remember_login.headers["Set-Cookie"]
    with app.app_context():
        session = db.session.execute(
            select(AuthSession).order_by(AuthSession.created_at.desc())
        ).scalars().first()
        assert session.remember_me is True


def test_login_can_start_new_challenge_after_successful_otp(
    client, csrf_headers, sent_account_emails
):
    verification_code = create_verified_account(client, csrf_headers, sent_account_emails)
    assert verify_account(
        client, csrf_headers, "owner@example.com", verification_code
    ).status_code == 200

    for _ in range(2):
        started = client.post(
            f"{AUTH_URL}/login",
            headers=csrf_headers,
            json={"email": "owner@example.com", "password": PASSWORD},
        )
        assert started.status_code == 202
        challenge_id = started.get_json()["challenge_id"]
        _, purpose, code = sent_account_emails.pop()
        assert purpose == LOGIN_OTP
        completed = client.post(
            f"{AUTH_URL}/otp/verify",
            headers=csrf_headers,
            json={"challenge_id": challenge_id, "code": code},
        )
        assert completed.status_code == 200


def test_login_otp_attempts_and_resend_rotate_the_challenge(
    app, client, csrf_headers, sent_account_emails
):
    verification_code = create_verified_account(client, csrf_headers, sent_account_emails)
    assert verify_account(
        client, csrf_headers, "owner@example.com", verification_code
    ).status_code == 200

    started = client.post(
        f"{AUTH_URL}/otp/send",
        headers=csrf_headers,
        json={"email": "owner@example.com", "password": PASSWORD},
    )
    assert started.status_code == 202
    old_challenge = started.get_json()["challenge_id"]
    _, purpose, old_code = sent_account_emails.pop()
    assert purpose == LOGIN_OTP

    invalid_resend = client.post(
        f"{AUTH_URL}/otp/resend",
        headers=csrf_headers,
        json={"challenge_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert invalid_resend.status_code == 202
    assert "challenge_id" not in invalid_resend.get_json()

    wrong_code = "111111" if old_code != "111111" else "222222"
    for _ in range(app.config["AUTH_OTP_MAX_ATTEMPTS"]):
        response = client.post(
            f"{AUTH_URL}/otp/verify",
            headers=csrf_headers,
            json={"challenge_id": old_challenge, "code": wrong_code},
        )
        assert response.status_code == 400
    assert client.post(
        f"{AUTH_URL}/otp/verify",
        headers=csrf_headers,
        json={"challenge_id": old_challenge, "code": old_code},
    ).status_code == 400

    with app.app_context():
        token = db.session.get(AuthToken, old_challenge)
        token.created_at = (
            utc_now() - timedelta(seconds=app.config["AUTH_OTP_RESEND_SECONDS"] + 1)
        ).replace(tzinfo=None)
        db.session.commit()

    resent = client.post(
        f"{AUTH_URL}/otp/resend",
        headers=csrf_headers,
        json={"challenge_id": old_challenge},
    )
    assert resent.status_code == 202
    new_challenge = resent.get_json()["challenge_id"]
    assert new_challenge != old_challenge
    _, purpose, new_code = sent_account_emails.pop()
    assert purpose == LOGIN_OTP
    assert client.post(
        f"{AUTH_URL}/otp/verify",
        headers=csrf_headers,
        json={"challenge_id": old_challenge, "code": old_code},
    ).status_code == 400
    completed = client.post(
        f"{AUTH_URL}/otp/verify",
        headers=csrf_headers,
        json={"challenge_id": new_challenge, "code": new_code},
    )
    assert completed.status_code == 200


def test_csrf_and_auth_security_headers(client):
    missing_csrf = client.post(f"{AUTH_URL}/login", json={"email": "owner@example.com"})
    assert missing_csrf.status_code == 400
    assert missing_csrf.get_json()["error"]["code"] == "csrf_failed"

    csrf = client.get(f"{AUTH_URL}/csrf")
    assert csrf.status_code == 200
    assert csrf.headers["Cache-Control"] == "no-store"
    assert csrf.headers["X-Content-Type-Options"] == "nosniff"
    assert csrf.headers["X-Frame-Options"] == "DENY"
    assert csrf.headers["Referrer-Policy"] == "no-referrer"


def test_business_access_requires_active_membership_and_role(app, client):
    with app.app_context():
        user = User(
            email="member@example.com",
            display_name="Member",
            password_hash="unused",
            email_verified_at=utc_now(),
        )
        business = Business(name="Member business")
        membership = BusinessMembership(
            business=business, user=user, role="manager", status="active"
        )
        other_business = Business(name="Other business")
        db.session.add_all([user, business, membership, other_business])
        db.session.commit()
        _, raw_session_token = create_session(user)
        business_id = business.id
        other_business_id = other_business.id

    client.set_cookie("dpbm_auth", raw_session_token)
    assert client.get(f"/test-business/{business_id}").status_code == 200
    assert client.get(f"/test-business/{other_business_id}").status_code == 404
    assert client.get(f"/test-owner-business/{business_id}").status_code == 403


def test_inactive_membership_and_expired_session_are_denied(app, client):
    with app.app_context():
        user = User(
            email="suspended@example.com",
            display_name="Suspended",
            password_hash="unused",
            email_verified_at=utc_now(),
        )
        business = Business(name="Suspended business")
        db.session.add_all([user, business])
        db.session.flush()
        membership = BusinessMembership(
            business=business, user=user, role="owner", status="suspended"
        )
        db.session.add(membership)
        db.session.commit()
        session, raw_session_token = create_session(user)
        business_id = business.id
        session.expires_at = utc_now() - timedelta(seconds=1)
        db.session.commit()

    client.set_cookie("dpbm_auth", raw_session_token)
    assert client.get(f"/test-suspended-business/{business_id}").status_code == 401


def test_registration_rate_limit_is_enforced():
    from app import create_app

    limited_app = create_app(
        {
            "APP_ENV": "testing",
            "SECRET_KEY": "rate-limit-test-secret-that-is-32-bytes",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "TESTING": True,
            "RATELIMIT_ENABLED": True,
        }
    )
    with limited_app.app_context():
        db.create_all()

    client = limited_app.test_client()
    csrf_token = client.get(f"{AUTH_URL}/csrf").get_json()["csrf_token"]
    headers = {"X-CSRFToken": csrf_token}
    for _ in range(5):
        response = client.post(f"{AUTH_URL}/register", headers=headers, json={"name": ""})
        assert response.status_code == 400
    assert client.post(
        f"{AUTH_URL}/register", headers=headers, json={"name": ""}
    ).status_code == 429

    with limited_app.app_context():
        db.session.remove()
        db.drop_all()


def test_production_rejects_smtp_without_tls(monkeypatch):
    from app import create_app

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "a-production-secret-key-that-is-long-enough")
    monkeypatch.setenv("RESEND_API_KEY", "test-resend-key")

    with pytest.raises(RuntimeError, match="SMTP delivery must use TLS"):
        create_app(
            {
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "RATELIMIT_STORAGE_URI": "redis://localhost:6379/0",
                "MAIL_SERVER": "smtp.example.test",
                "MAIL_FROM": "noreply@example.test",
                "MAIL_USE_TLS": False,
                "PUBLIC_APP_URL": "https://business.example.test",
            }
        )
