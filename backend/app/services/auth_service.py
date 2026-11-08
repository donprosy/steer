"""Account, token, session, and business membership operations."""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from flask import current_app, g, request
from sqlalchemy import select, update
from app import db
from app.models import AuthSession, AuthToken, Business, BusinessMembership, User
from app.services.password_service import (
    hash_password,
    password_hash_needs_rehash,
    verify_password,
)

EMAIL_VERIFICATION = "email_verification"
PASSWORD_RESET = "password_reset"
LOGIN_OTP = "login_otp"
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
SESSION_COOKIE_PATH = "/"


class AccountInputError(ValueError):
    """Raised for invalid account fields safe to report to the user."""


def utc_now():
    return datetime.now(timezone.utc)


def normalized_datetime(value):
    """Make SQLite's naive UTC datetimes comparable to aware UTC values."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_email(value):
    from email_validator import EmailNotValidError, validate_email

    if not isinstance(value, str) or len(value) > 254:
        raise AccountInputError("Enter a valid email address.")
    try:
        return validate_email(value.strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError as error:
        raise AccountInputError("Enter a valid email address.") from error


def validate_password(value):
    if not isinstance(value, str) or not (
        PASSWORD_MIN_LENGTH <= len(value) <= PASSWORD_MAX_LENGTH
    ):
        raise AccountInputError(
            f"Password must be between {PASSWORD_MIN_LENGTH} and "
            f"{PASSWORD_MAX_LENGTH} characters."
        )
    return value


def validate_display_name(value, field_name, maximum):
    if not isinstance(value, str):
        raise AccountInputError(f"Enter a valid {field_name.lower()}.")
    value = value.strip()
    if not value or len(value) > maximum:
        raise AccountInputError(
            f"{field_name} must be between 1 and {maximum} characters."
        )
    return value


def validate_registration(payload):
    if not isinstance(payload, dict):
        raise AccountInputError("A JSON request body is required.")
    return {
        "display_name": validate_display_name(payload.get("name"), "Name", 120),
        "email": normalize_email(payload.get("email")),
        "password": validate_password(payload.get("password")),
        "business_name": validate_display_name(
            payload.get("business_name"), "Business name", 160
        ),
    }


def validate_email_request(payload):
    if not isinstance(payload, dict):
        raise AccountInputError("A JSON request body is required.")
    return normalize_email(payload.get("email"))


def token_digest(raw_token):
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def otp_digest(code):
    return hmac.new(
        current_app.config["SECRET_KEY"].encode("utf-8"),
        code.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


def database_datetime(value):
    """Return a UTC datetime compatible with the database's stored representation."""
    if db.session.get_bind().dialect.name == "sqlite":
        return value.replace(tzinfo=None)
    return value


def generate_otp():
    return f"{secrets.randbelow(1_000_000):06d}"


def issue_auth_token(user, purpose):
    _, raw_token = _create_auth_token(user, purpose)
    return raw_token


def issue_login_otp(user, remember_me=False):
    token, raw_token = _create_auth_token(user, LOGIN_OTP, remember_me)
    return token.id, raw_token


def _create_auth_token(user, purpose, remember_me=False):
    raw_token = generate_otp()
    now = utc_now()
    db.session.execute(
        update(AuthToken)
        .where(
            AuthToken.user_id == user.id,
            AuthToken.purpose == purpose,
            AuthToken.used_at.is_(None),
        )
        .values(used_at=database_datetime(now))
    )
    expires_at = now + timedelta(minutes=current_app.config["AUTH_OTP_MINUTES"])
    token = AuthToken(
        user=user,
        purpose=purpose,
        token_hash=otp_digest(raw_token),
        expires_at=expires_at,
        remember_me=remember_me,
    )
    db.session.add(token)
    db.session.flush()
    return token, raw_token


def find_valid_otp(email, code, purpose, token_id=None):
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        return None, "invalid"
    if token_id is not None:
        token = db.session.execute(
            select(AuthToken).where(
                AuthToken.id == token_id,
                AuthToken.purpose == purpose,
                AuthToken.used_at.is_(None),
            )
        ).scalar_one_or_none()
    else:
        user = db.session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if user is None:
            return None, "invalid"
        token = db.session.execute(
            select(AuthToken)
            .where(
                AuthToken.user_id == user.id,
                AuthToken.purpose == purpose,
                AuthToken.used_at.is_(None),
            )
            .order_by(AuthToken.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
    if token is None:
        return None, "invalid"
    now = utc_now()
    if normalized_datetime(token.expires_at) <= now:
        return None, "invalid"
    if token.attempts >= current_app.config["AUTH_OTP_MAX_ATTEMPTS"]:
        return None, "invalid"
    if not hmac.compare_digest(token.token_hash, otp_digest(code)):
        result = db.session.execute(
            update(AuthToken)
            .where(
                AuthToken.id == token.id,
                AuthToken.used_at.is_(None),
                AuthToken.expires_at > database_datetime(now),
                AuthToken.attempts < current_app.config["AUTH_OTP_MAX_ATTEMPTS"],
            )
            .values(attempts=AuthToken.attempts + 1)
        )
        db.session.commit()
        if result.rowcount != 1:
            return None, "invalid"
        return None, "invalid"
    return token, "valid"


def otp_cooldown_remaining(user, purpose):
    token = db.session.execute(
        select(AuthToken)
        .where(AuthToken.user_id == user.id, AuthToken.purpose == purpose)
        .order_by(AuthToken.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if token is None:
        return 0
    available_at = normalized_datetime(token.created_at) + timedelta(
        seconds=current_app.config["AUTH_OTP_RESEND_SECONDS"]
    )
    return max(0, int((available_at - utc_now()).total_seconds() + 0.999))


def consume_otp(token):
    now = utc_now()
    result = db.session.execute(
        update(AuthToken)
        .where(
            AuthToken.id == token.id,
            AuthToken.used_at.is_(None),
            AuthToken.expires_at > database_datetime(now),
            AuthToken.attempts < current_app.config["AUTH_OTP_MAX_ATTEMPTS"],
        )
        .values(used_at=database_datetime(now))
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        return False
    token.used_at = now
    return True


def create_account(payload):
    data = validate_registration(payload)
    existing = db.session.execute(
        select(User.id).where(User.email == data["email"])
    ).scalar_one_or_none()
    if existing is not None:
        return None, None

    user = User(
        email=data["email"],
        display_name=data["display_name"],
        password_hash=hash_password(data["password"]),
    )
    business = Business(name=data["business_name"])
    membership = BusinessMembership(
        id=str(uuid.uuid4()), business=business, user=user, role="owner", status="active"
    )
    db.session.add_all([user, business, membership])
    raw_token = issue_auth_token(user, EMAIL_VERIFICATION)
    db.session.flush()
    return user, raw_token


def verify_email(email, code):
    token, status = find_valid_otp(email, code, EMAIL_VERIFICATION)
    if token is None or status != "valid" or not consume_otp(token):
        return None
    now = utc_now()
    token.user.email_verified_at = now
    db.session.commit()
    return token.user


def authenticate(email, password):
    user = db.session.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        verify_password(_dummy_password_hash(), password)
        return None
    valid_password = verify_password(user.password_hash, password)
    if not valid_password or not user.is_active:
        return None
    if password_hash_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.session.commit()
    return user


_DUMMY_HASH = None


def _dummy_password_hash():
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password(secrets.token_urlsafe(24))
    return _DUMMY_HASH


def create_session(user, remember_me=False):
    raw_token = secrets.token_urlsafe(32)
    lifetime = (
        timedelta(days=current_app.config["AUTH_REMEMBER_DAYS"])
        if remember_me
        else timedelta(hours=current_app.config["AUTH_SESSION_HOURS"])
    )
    auth_session = AuthSession(
        user=user,
        token_hash=token_digest(raw_token),
        expires_at=utc_now() + lifetime,
        remember_me=remember_me,
    )
    db.session.add(auth_session)
    db.session.commit()
    return auth_session, raw_token


def revoke_session(auth_session):
    if auth_session is not None and auth_session.revoked_at is None:
        auth_session.revoked_at = utc_now()
        db.session.commit()


def revoke_user_sessions(user):
    now = utc_now()
    for auth_session in user.auth_sessions:
        if auth_session.revoked_at is None:
            auth_session.revoked_at = now


def current_auth_session():
    if hasattr(g, "auth_session"):
        return g.auth_session

    raw_token = request.cookies.get(current_app.config["AUTH_COOKIE_NAME"])
    if not raw_token or len(raw_token) > 256:
        g.auth_session = None
        return None

    auth_session = db.session.execute(
        select(AuthSession).where(
            AuthSession.token_hash == token_digest(raw_token),
            AuthSession.revoked_at.is_(None),
        )
    ).scalar_one_or_none()
    if (
        auth_session is None
        or normalized_datetime(auth_session.expires_at) <= utc_now()
        or not auth_session.user.is_active
        or auth_session.user.email_verified_at is None
    ):
        g.auth_session = None
        return None

    if (utc_now() - normalized_datetime(auth_session.last_seen_at)).total_seconds() > 300:
        auth_session.last_seen_at = utc_now()
        db.session.commit()
    g.auth_session = auth_session
    return auth_session


def auth_cookie_settings():
    return {
        "key": current_app.config["AUTH_COOKIE_NAME"],
        "httponly": True,
        "secure": current_app.config["AUTH_COOKIE_SECURE"],
        "samesite": "Lax",
        "path": SESSION_COOKIE_PATH,
    }


def set_auth_cookie(response, raw_token, auth_session):
    options = auth_cookie_settings()
    if auth_session.remember_me:
        max_age = max(
            0, int((normalized_datetime(auth_session.expires_at) - utc_now()).total_seconds())
        )
        response.set_cookie(
            options["key"], raw_token, max_age=max_age, **{k: v for k, v in options.items() if k != "key"}
        )
    else:
        response.set_cookie(
            options["key"], raw_token, **{k: v for k, v in options.items() if k != "key"}
        )
    return response


def clear_auth_cookie(response):
    options = auth_cookie_settings()
    response.delete_cookie(
        options["key"],
        path=options["path"],
        secure=options["secure"],
        httponly=options["httponly"],
        samesite=options["samesite"],
    )
    return response


def serialize_user(user):
    memberships = [
        {
            "business_id": membership.business_id,
            "business_name": membership.business.name,
            "role": membership.role,
        }
        for membership in user.memberships
        if membership.status == "active" and membership.business.status == "active"
    ]
    return {
        "id": user.id,
        "name": user.display_name,
        "email": user.email,
        "system_role": user.system_role,
        "businesses": memberships,
    }


def membership_for_user(user, business_id):
    return next(
        (
            membership
            for membership in user.memberships
            if membership.business_id == business_id
            and membership.status == "active"
            and membership.business.status == "active"
        ),
        None,
    )
