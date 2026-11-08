"""Flask application factory."""

import os
import secrets
import warnings

from dotenv import load_dotenv
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError

db = SQLAlchemy()


def create_app(test_config=None):
    """Create and configure the application."""
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    test_config = test_config or {}
    app_environment = os.environ.get("APP_ENV", test_config.get("APP_ENV", "development")).strip().lower()
    secret_key = os.environ.get("SECRET_KEY", test_config.get("SECRET_KEY"))
    if not secret_key or secret_key == "replace-this-local-development-secret":
        if app_environment in {"production", "prod"}:
            raise RuntimeError("SECRET_KEY must be configured with a strong random value.")
        secret_key = secrets.token_urlsafe(48)
        warnings.warn(
            "SECRET_KEY is missing or still a placeholder; using an ephemeral development key. "
            "Sessions and CSRF tokens will not survive a restart.",
            RuntimeWarning,
            stacklevel=2,
        )

    app.config.from_mapping(
        APP_ENV=app_environment,
        SECRET_KEY=secret_key,
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", "sqlite:///don_prosy.db"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_COOKIE_NAME="dpbm_csrf",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=app_environment in {"production", "prod"},
        WTF_CSRF_ENABLED=True,
        WTF_CSRF_TIME_LIMIT=3600,
        AUTH_COOKIE_NAME=(
            "__Host-dpbm_auth"
            if app_environment in {"production", "prod"}
            else "dpbm_auth"
        ),
        AUTH_COOKIE_SECURE=app_environment in {"production", "prod"},
        AUTH_SESSION_HOURS=12,
        AUTH_REMEMBER_DAYS=30,
        AUTH_OTP_MINUTES=10,
        AUTH_OTP_RESEND_SECONDS=60,
        AUTH_OTP_MAX_ATTEMPTS=5,
        PUBLIC_APP_URL=os.environ.get("PUBLIC_APP_URL", "http://localhost:5173"),
        MAIL_SERVER=os.environ.get("MAIL_SERVER"),
        MAIL_PORT=int(os.environ.get("MAIL_PORT", "587")),
        MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
        MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
        MAIL_USE_TLS=_env_bool("MAIL_USE_TLS", True),
        MAIL_USE_SSL=_env_bool("MAIL_USE_SSL", False),
        MAIL_DEFAULT_SENDER=(
            os.environ.get("MAIL_DEFAULT_SENDER")
            or os.environ.get("MAIL_FROM")
        ),
        MAIL_SENDER_NAME=os.environ.get(
            "MAIL_SENDER_NAME", "STEER"
        ),
        MAIL_FROM=os.environ.get("MAIL_FROM"),
        RESEND_API_KEY=os.environ.get("RESEND_API_KEY"),
        RATELIMIT_STORAGE_URI=os.environ.get("RATELIMIT_STORAGE_URI", "memory://"),
        RATELIMIT_ENABLED=app_environment != "testing",
    )

    app.config.update(test_config)

    _validate_security_configuration(app)
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)

    from app.extensions import csrf, limiter, migrate

    csrf.init_app(app)
    limiter.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401
    from app.routes import api

    app.register_blueprint(api, url_prefix="/api/v1")

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        return {
            "error": {
                "code": "csrf_failed",
                "message": "The security token is missing or expired. Refresh and try again.",
            }
        }, 400

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.path.startswith("/api/v1/auth/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    return app


def _validate_security_configuration(app):
    """Reject production configurations that would weaken auth guarantees."""
    if app.config["APP_ENV"] in {"production", "prod"}:
        secret_key = app.config.get("SECRET_KEY", "")
        if len(secret_key) < 32 or secret_key == "replace-this-local-development-secret":
            raise RuntimeError("Production SECRET_KEY must be a strong random value.")
        if app.config.get("RATELIMIT_STORAGE_URI", "memory://").startswith("memory://"):
            raise RuntimeError(
                "Production rate limiting requires shared storage; configure "
                "RATELIMIT_STORAGE_URI."
            )
        if not app.config.get("RESEND_API_KEY") or not (
            app.config.get("MAIL_DEFAULT_SENDER") or app.config.get("MAIL_FROM")
        ):
            raise RuntimeError(
                "Production authentication email requires RESEND_API_KEY and MAIL_DEFAULT_SENDER."
            )
        if app.config.get("MAIL_SERVER"):
            if app.config.get("MAIL_USE_TLS") == app.config.get("MAIL_USE_SSL"):
                raise RuntimeError(
                    "SMTP delivery must use TLS (STARTTLS) or implicit SSL, but not both."
                )
            if bool(app.config.get("MAIL_USERNAME")) != bool(
                app.config.get("MAIL_PASSWORD")
            ):
                raise RuntimeError(
                    "Configure both MAIL_USERNAME and MAIL_PASSWORD, or neither when SMTP authentication is not required."
                )
        if not app.config.get("PUBLIC_APP_URL", "").startswith("https://"):
            raise RuntimeError("Production PUBLIC_APP_URL must use HTTPS.")


def _env_bool(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
