"""JSON authentication and account recovery endpoints."""

import logging
from uuid import UUID

from flask import Blueprint, current_app, g, jsonify, request
from flask_wtf.csrf import generate_csrf
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import db
from app.extensions import limiter
from app.models import AuthToken, User
from app.security import require_auth
from app.services.auth_service import (
    EMAIL_VERIFICATION,
    LOGIN_OTP,
    PASSWORD_MAX_LENGTH,
    PASSWORD_RESET,
    AccountInputError,
    authenticate,
    clear_auth_cookie,
    create_account,
    create_session,
    current_auth_session,
    consume_otp,
    find_valid_otp,
    issue_auth_token,
    issue_login_otp,
    normalize_email,
    normalized_datetime,
    otp_cooldown_remaining,
    revoke_session,
    revoke_user_sessions,
    serialize_user,
    set_auth_cookie,
    utc_now,
    validate_email_request,
    validate_password,
    validate_registration,
    verify_email,
)
from app.services.password_service import hash_password
from app.services.email_service import EmailDeliveryError, send_account_token

logger = logging.getLogger(__name__)
auth = Blueprint("auth", __name__)


def error_response(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status


def _require_email_delivery_configuration():
    if current_app.config.get("AUTH_EMAIL_SENDER") is not None:
        return None
    if not current_app.config.get("RESEND_API_KEY") or not (
        current_app.config.get("MAIL_DEFAULT_SENDER")
        or current_app.config.get("MAIL_FROM")
    ):
        return error_response(
            "email_delivery_unavailable",
            "Email delivery is not configured. Contact the administrator.",
            503,
        )
    return None


def _deliver_auth_token(user, purpose, raw_token):
    try:
        send_account_token(user, purpose, raw_token)
    except EmailDeliveryError as error:
        logger.error("Account email delivery failed (%s).", type(error).__name__)
        return False
    return True


def _otp_cooldown_response():
    return jsonify(
        {"message": "If the account needs verification, a code will be sent to its email."}
    ), 202


def _login_otp_response(challenge_id, email):
    return jsonify(
        {
            "message": "A sign-in code was sent to your email address.",
            "challenge_id": challenge_id,
            "email": email,
        }
    ), 202


def _valid_challenge_id(value):
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
    except ValueError:
        return False
    return True


@auth.get("/csrf")
def get_csrf_token():
    """Provide a session-bound token for same-origin JSON mutations."""
    response = jsonify({"csrf_token": generate_csrf()})
    response.headers["Cache-Control"] = "no-store"
    return response


@auth.post("/register")
@limiter.limit("5 per minute")
def register():
    payload = request.get_json(silent=True)
    try:
        data = validate_registration(payload)
        if payload.get("confirm_password") != data["password"]:
            raise AccountInputError("Passwords do not match.")
    except AccountInputError as error:
        return error_response("validation_error", str(error), 400)

    config_error = _require_email_delivery_configuration()
    if config_error:
        return config_error

    try:
        user, code = create_account(payload)
        if user is None:
            db.session.rollback()
            return error_response(
                "email_already_registered",
                "An account with this email already exists. Sign in or reset its password.",
                409,
            )
        if not _deliver_auth_token(user, EMAIL_VERIFICATION, code):
            db.session.rollback()
            return error_response(
                "email_delivery_failed",
                "Your account could not be created because the verification email was not delivered. Please try again.",
                503,
            )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response(
            "email_already_registered",
            "An account with this email already exists. Sign in or reset its password.",
            409,
        )
    except Exception:
        db.session.rollback()
        logger.exception("Account registration failed.")
        return error_response(
            "registration_failed",
            "The account could not be created. Please try again.",
            500,
        )

    return jsonify(
        {
            "message": "A 6-digit verification code was sent to your email address.",
            "email": user.email,
        }
    ), 202


@auth.post("/verification-requests")
@limiter.limit("3 per hour")
def request_verification():
    try:
        email = validate_email_request(request.get_json(silent=True))
    except AccountInputError as error:
        return error_response("validation_error", str(error), 400)
    config_error = _require_email_delivery_configuration()
    if config_error:
        return config_error

    user = db.session.execute(
        select(User).where(User.email == email).with_for_update()
    ).scalar_one_or_none()
    if user is not None and user.is_active and user.email_verified_at is None:
        remaining = otp_cooldown_remaining(user, EMAIL_VERIFICATION)
        if remaining:
            return _otp_cooldown_response()
        try:
            code = issue_auth_token(user, EMAIL_VERIFICATION)
            if not _deliver_auth_token(user, EMAIL_VERIFICATION, code):
                db.session.rollback()
                return error_response(
                    "email_delivery_failed",
                    "The verification code could not be delivered. Please try again later.",
                    503,
                )
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception("Verification code request failed.")
            return error_response(
                "verification_request_failed",
                "The verification code could not be sent. Please try again.",
                500,
            )
    return jsonify(
        {"message": "If the account needs verification, a code will be sent to its email."}
    ), 202


@auth.post("/email-verifications")
@limiter.limit("10 per hour")
def complete_email_verification():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("validation_error", "A JSON request body is required.", 400)
    try:
        email = normalize_email(payload.get("email"))
    except AccountInputError as error:
        return error_response("validation_error", str(error), 400)
    code = payload.get("code")
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        return error_response("validation_error", "Enter the 6-digit verification code.", 400)

    user = verify_email(email, code)
    if user is None:
        return error_response(
            "invalid_or_expired_code",
            "The verification code is incorrect, expired, or no longer valid.",
            400,
        )
    auth_session, raw_session = create_session(user)
    response = jsonify(
        {"message": "Email verified.", "user": serialize_user(user)}
    )
    return set_auth_cookie(response, raw_session, auth_session)


@auth.post("/login")
@auth.post("/otp/send")
@limiter.limit("10 per minute")
def login():
    """Verify the password and start the second-factor login challenge."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("validation_error", "A JSON request body is required.", 400)
    try:
        email = normalize_email(payload.get("email"))
    except AccountInputError as error:
        return error_response("validation_error", str(error), 400)

    password = payload.get("password")
    if not isinstance(password, str) or not password or len(password) > PASSWORD_MAX_LENGTH:
        return error_response("validation_error", "Enter a valid password.", 400)
    remember_me = payload.get("remember_me", False)
    if not isinstance(remember_me, bool):
        return error_response("validation_error", "Remember me must be a boolean.", 400)

    user = authenticate(email, password)
    if user is None:
        return error_response(
            "invalid_credentials",
            "Email or password is incorrect, or the account is not ready.",
            401,
        )

    if user.email_verified_at is None:
        return error_response(
            "email_not_verified",
            "Verify your email before signing in. You can request a new verification code.",
            403,
        )

    config_error = _require_email_delivery_configuration()
    if config_error:
        return config_error

    user = db.session.execute(
        select(User).where(User.id == user.id).with_for_update()
    ).scalar_one()
    remaining = otp_cooldown_remaining(user, LOGIN_OTP)
    if remaining:
        active_token = db.session.execute(
            select(AuthToken)
            .where(
                AuthToken.user_id == user.id,
                AuthToken.purpose == LOGIN_OTP,
                AuthToken.used_at.is_(None),
            )
            .order_by(AuthToken.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if (
            active_token is not None
            and normalized_datetime(active_token.expires_at) > utc_now()
            and active_token.attempts < current_app.config["AUTH_OTP_MAX_ATTEMPTS"]
        ):
            active_token.remember_me = remember_me
            db.session.commit()
            return _login_otp_response(active_token.id, user.email)
        return jsonify(
            {
                "error": {
                    "code": "otp_cooldown",
                    "message": "Please wait before requesting another sign-in code.",
                    "retry_after": remaining,
                }
            }
        ), 429

    try:
        challenge_id, code = issue_login_otp(user, remember_me)
        if not _deliver_auth_token(user, LOGIN_OTP, code):
            db.session.rollback()
            return error_response(
                "email_delivery_failed",
                "The sign-in code could not be delivered. Please try again later.",
                503,
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Login code request failed.")
        return error_response(
            "login_code_request_failed",
            "The sign-in code could not be sent. Please try again.",
            500,
        )

    return _login_otp_response(challenge_id, user.email)


@auth.post("/otp/resend")
@limiter.limit("10 per hour")
def resend_login_otp():
    payload = request.get_json(silent=True)
    challenge_id = payload.get("challenge_id") if isinstance(payload, dict) else None
    generic_message = {
        "message": "If this sign-in request is still valid, a code will be sent."
    }
    if not _valid_challenge_id(challenge_id):
        return jsonify(generic_message), 202

    token = db.session.execute(
        select(AuthToken).where(
            AuthToken.id == challenge_id,
            AuthToken.purpose == LOGIN_OTP,
        )
    ).scalar_one_or_none()
    if token is None or token.used_at is not None:
        return jsonify(generic_message), 202

    user = db.session.execute(
        select(User).where(User.id == token.user_id).with_for_update()
    ).scalar_one_or_none()
    if (
        user is None
        or not user.is_active
        or user.email_verified_at is None
    ):
        return jsonify(generic_message), 202

    config_error = _require_email_delivery_configuration()
    if config_error:
        return config_error

    if otp_cooldown_remaining(user, LOGIN_OTP):
        return jsonify(generic_message), 202

    try:
        new_challenge_id, code = issue_login_otp(user, token.remember_me)
        if not _deliver_auth_token(user, LOGIN_OTP, code):
            db.session.rollback()
            return error_response(
                "email_delivery_failed",
                "The sign-in code could not be delivered. Please try again later.",
                503,
            )
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception("Login code resend failed.")
        return error_response(
            "login_code_request_failed",
            "The sign-in code could not be sent. Please try again.",
            500,
        )

    return _login_otp_response(new_challenge_id, user.email)


@auth.post("/otp/verify")
@limiter.limit("10 per hour")
def verify_login_otp():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("validation_error", "A JSON request body is required.", 400)
    challenge_id = payload.get("challenge_id")
    code = payload.get("code")
    if not _valid_challenge_id(challenge_id) or not (
        isinstance(code, str) and len(code) == 6 and code.isdigit()
    ):
        return error_response("validation_error", "Enter the 6-digit sign-in code.", 400)

    token, status = find_valid_otp(
        None, code, LOGIN_OTP, token_id=challenge_id
    )
    if (
        token is None
        or status != "valid"
        or not token.user.is_active
        or token.user.email_verified_at is None
        or not consume_otp(token)
    ):
        return error_response(
            "invalid_or_expired_code",
            "The sign-in code is incorrect, expired, or no longer valid.",
            400,
        )

    old_session = current_auth_session()
    if old_session is not None:
        revoke_session(old_session)
    auth_session, raw_session = create_session(token.user, token.remember_me)
    response = jsonify({"user": serialize_user(token.user)})
    return set_auth_cookie(response, raw_session, auth_session)


@auth.get("/me")
@require_auth
def get_current_user():
    return jsonify({"user": serialize_user(g.current_user)})


@auth.post("/logout")
def logout():
    revoke_session(current_auth_session())
    return clear_auth_cookie(jsonify({"message": "Signed out."}))


@auth.post("/password-reset-requests")
@limiter.limit("3 per hour")
def request_password_reset():
    try:
        email = validate_email_request(request.get_json(silent=True))
    except AccountInputError as error:
        return error_response("validation_error", str(error), 400)
    config_error = _require_email_delivery_configuration()
    if config_error:
        return config_error

    user = db.session.execute(
        select(User).where(User.email == email).with_for_update()
    ).scalar_one_or_none()
    if user is not None and user.is_active and user.email_verified_at is not None:
        remaining = otp_cooldown_remaining(user, PASSWORD_RESET)
        if not remaining:
            try:
                code = issue_auth_token(user, PASSWORD_RESET)
                if not _deliver_auth_token(user, PASSWORD_RESET, code):
                    db.session.rollback()
                    return error_response(
                        "email_delivery_failed",
                        "The password reset code could not be delivered. Please try again later.",
                        503,
                    )
                db.session.commit()
            except Exception:
                db.session.rollback()
                logger.exception("Password reset code request failed.")
                return error_response(
                    "password_reset_request_failed",
                    "The password reset code could not be sent. Please try again.",
                    500,
                )
    return jsonify(
        {"message": "If an eligible account exists, a password reset code will be sent."}
    ), 202


@auth.post("/password-resets")
@limiter.limit("10 per hour")
def reset_password():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("validation_error", "A JSON request body is required.", 400)
    try:
        email = normalize_email(payload.get("email"))
    except AccountInputError as error:
        return error_response("validation_error", str(error), 400)
    code = payload.get("code")
    if not isinstance(code, str) or len(code) != 6 or not code.isdigit():
        return error_response("validation_error", "Enter the 6-digit reset code.", 400)
    try:
        password = validate_password(payload.get("password"))
    except AccountInputError as error:
        return error_response("validation_error", str(error), 400)
    if payload.get("confirm_password") != password:
        return error_response("validation_error", "Passwords do not match.", 400)

    token, token_status = find_valid_otp(email, code, PASSWORD_RESET)
    if token is None or token_status != "valid" or not token.user.is_active:
        return error_response(
            "invalid_or_expired_code",
            "The password reset code is incorrect, expired, or no longer valid.",
            400,
        )
    if not consume_otp(token):
        return error_response(
            "invalid_or_expired_code",
            "The password reset code is incorrect, expired, or no longer valid.",
            400,
        )
    user = token.user
    user.password_hash = hash_password(password)
    revoke_user_sessions(user)
    db.session.commit()
    return clear_auth_cookie(jsonify({"message": "Password reset. Sign in with your new password."}))
