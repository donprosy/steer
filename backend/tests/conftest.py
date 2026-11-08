import pytest

from app import create_app, db
from app.security import require_business_role


@pytest.fixture
def sent_account_emails():
    return []


@pytest.fixture
def app(sent_account_emails):
    application = create_app(
        {
            "APP_ENV": "testing",
            "SECRET_KEY": "test-secret-key-that-is-at-least-32-bytes",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "TESTING": True,
            "WTF_CSRF_ENABLED": True,
            "RATELIMIT_ENABLED": False,
            "MAIL_SERVER": "smtp.example.test",
            "MAIL_FROM": "noreply@example.test",
            "AUTH_EMAIL_SENDER": lambda email, purpose, token: sent_account_emails.append(
                (email, purpose, token)
            ),
        }
    )

    @application.get("/test-business/<business_id>")
    @require_business_role("owner", "manager")
    def protected_business(business_id):
        return {"business_id": business_id}

    @application.get("/test-owner-business/<business_id>")
    @require_business_role("owner")
    def protected_owner_business(business_id):
        return {"business_id": business_id}

    @application.get("/test-suspended-business/<business_id>")
    @require_business_role("owner")
    def protected_suspended_business(business_id):
        return {"business_id": business_id}

    with application.app_context():
        db.create_all()
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def csrf_headers(client):
    token = client.get("/api/v1/auth/csrf").get_json()["csrf_token"]
    return {"X-CSRFToken": token}
