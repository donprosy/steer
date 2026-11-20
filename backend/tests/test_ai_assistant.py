from unittest.mock import patch
import urllib.error

from app import db
from app.models import AiConversation, AiMessage, Business, BusinessMembership, Expense, User
from app.services.auth_service import create_session, utc_now
from app.services.ai_service import AiProviderError, call_ai_provider


def create_business_session(app, client, role="owner", email="ai-owner@example.test"):
    with app.app_context():
        user = User(
            email=email,
            display_name="AI Owner",
            password_hash="unused",
            email_verified_at=utc_now(),
        )
        business = Business(name="AI Test Business")
        membership = BusinessMembership(business=business, user=user, role=role, status="active")
        db.session.add_all([user, business, membership])
        db.session.flush()
        _, token = create_session(user)
        business_id = business.id
        db.session.commit()
    client.set_cookie("dpbm_auth", token)
    return business_id


def test_ai_missing_provider_and_database_backed_insights(app, client, csrf_headers):
    business_id = create_business_session(app, client)
    app.config.update(
        AI_API_KEY=None,
        AI_BASE_URL=None,
        AI_MODEL=None,
    )

    chat = client.post(
        f"/api/v1/businesses/{business_id}/assistant/chat",
        headers=csrf_headers,
        json={"message": "What is my profit?", "period": "this_month"},
    )
    assert chat.status_code == 503
    assert chat.get_json()["error"]["code"] == "ai_not_configured"

    insights = client.get(
        f"/api/v1/businesses/{business_id}/assistant/insights?period=this_month"
    )
    assert insights.status_code == 200
    payload = insights.get_json()
    assert payload["insights"]["financial_summary"]["net_profit"] == "0.00"
    assert payload["insights"]["low_stock_products"] == []


def test_ai_mocked_chat_usage_conversation_history_and_idempotency(app, client, csrf_headers):
    business_id = create_business_session(app, client)
    app.config.update(
        AI_API_KEY="test-key",
        AI_BASE_URL="https://provider.example.test",
        AI_MODEL="test-model",
        AI_API_FORMAT="openai_chat",
        AI_CHAT_PATH="/chat/completions",
        AI_PLAN_LIMITS={"starter": 100},
    )

    with patch(
        "app.routes.assistant.call_ai_provider",
        return_value={
            "content": "Your net profit is ₦0.00 for this month.",
            "input_tokens": 42,
            "output_tokens": 10,
        },
    ) as provider:
        first = client.post(
            f"/api/v1/businesses/{business_id}/assistant/chat",
            headers=csrf_headers,
            json={
                "message": "What is my net profit?",
                "period": "this_month",
                "request_id": "repeat-safe-request",
            },
        )
        assert first.status_code == 201
        conversation_id = first.get_json()["conversation"]["id"]
        assert first.get_json()["usage"]["reply_count"] == 1

        repeated = client.post(
            f"/api/v1/businesses/{business_id}/assistant/chat",
            headers=csrf_headers,
            json={
                "conversation_id": conversation_id,
                "message": "What is my net profit?",
                "period": "this_month",
                "request_id": "repeat-safe-request",
            },
        )
        assert repeated.status_code == 200
        assert repeated.get_json()["idempotent"] is True
        assert provider.call_count == 1

    detail = client.get(
        f"/api/v1/businesses/{business_id}/assistant/conversations/{conversation_id}"
    )
    assert detail.status_code == 200
    messages = detail.get_json()["conversation"]["messages"]
    assert [item["role"] for item in messages] == ["user", "assistant"]

    usage = client.get(f"/api/v1/businesses/{business_id}/assistant/usage")
    assert usage.status_code == 200
    assert usage.get_json()["usage"]["reply_count"] == 1
    assert usage.get_json()["usage"]["remaining"] == 99


def test_ai_usage_limit_conversation_ownership_and_tenant_isolation(app, client, csrf_headers):
    business_id = create_business_session(app, client)
    app.config.update(
        AI_API_KEY="test-key",
        AI_BASE_URL="https://provider.example.test",
        AI_MODEL="test-model",
        AI_DEFAULT_PLAN_KEY="starter",
        AI_PLAN_LIMITS={"starter": 0},
    )

    created = client.post(
        f"/api/v1/businesses/{business_id}/assistant/conversations",
        headers=csrf_headers,
        json={"title": "Owner only"},
    )
    assert created.status_code == 201
    conversation_id = created.get_json()["conversation"]["id"]

    exhausted = client.post(
        f"/api/v1/businesses/{business_id}/assistant/chat",
        headers=csrf_headers,
        json={"conversation_id": conversation_id, "message": "Analyze profit"},
    )
    assert exhausted.status_code == 429

    with app.app_context():
        other_business = Business(name="Other AI Business")
        db.session.add(other_business)
        db.session.commit()
        other_business_id = other_business.id

    assert client.get(
        f"/api/v1/businesses/{other_business_id}/assistant/conversations"
    ).status_code == 404
    assert client.get(
        f"/api/v1/businesses/{business_id}/assistant/conversations/not-a-conversation"
    ).status_code == 404


def test_ai_input_validation_and_empty_records(app, client, csrf_headers):
    business_id = create_business_session(app, client)
    invalid = client.post(
        f"/api/v1/businesses/{business_id}/assistant/chat",
        headers=csrf_headers,
        json={"message": ""},
    )
    assert invalid.status_code == 400

    invalid_period = client.post(
        f"/api/v1/businesses/{business_id}/assistant/chat",
        headers=csrf_headers,
        json={"message": "Analyze", "period": "last_decade"},
    )
    assert invalid_period.status_code == 400


def test_ai_provider_timeout_and_http_error(app):
    app.config.update(
        AI_API_KEY="test-key",
        AI_BASE_URL="https://provider.example.test",
        AI_MODEL="test-model",
        AI_API_FORMAT="openai_chat",
        AI_CHAT_PATH="/chat/completions",
        AI_TIMEOUT_SECONDS=1,
    )
    with app.app_context():
        with patch(
            "app.services.ai_service.urllib.request.urlopen",
            side_effect=urllib.error.URLError("timed out"),
        ):
            try:
                call_ai_provider([{"role": "user", "content": "Hello"}])
                assert False, "Provider timeout should raise AiProviderError"
            except AiProviderError as error:
                assert error.code == "ai_provider_unavailable"

        with patch(
            "app.services.ai_service.urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                "https://provider.example.test/chat/completions",
                401,
                "Unauthorized",
                {},
                None,
            ),
        ):
            try:
                call_ai_provider([{"role": "user", "content": "Hello"}])
                assert False, "Provider HTTP error should raise AiProviderError"
            except AiProviderError as error:
                assert error.code == "ai_provider_error"
