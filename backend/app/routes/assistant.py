"""Authenticated, tenant-scoped Stage 5 AI assistant endpoints."""

import json
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import select

from app import db
from app.models import AiConversation, AiMessage, AiUsageRecord
from app.security import require_business_role
from app.services.ai_service import (
    AiProviderError,
    build_business_context,
    call_ai_provider,
)


assistant = Blueprint("assistant", __name__)


def error_response(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status


def _payload():
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else {}


def _find_conversation(business_id, conversation_id):
    return db.session.scalar(
        select(AiConversation).where(
            AiConversation.id == conversation_id,
            AiConversation.business_id == business_id,
            AiConversation.user_id == g.current_user.id,
        )
    )


def _serialize_conversation(conversation, include_messages=False):
    payload = {
        "id": conversation.id,
        "business_id": conversation.business_id,
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
    }
    if include_messages:
        payload["messages"] = [
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat(),
                "metadata": json.loads(message.metadata_json)
                if message.metadata_json else None,
            }
            for message in conversation.messages
        ]
    return payload


def _month_period():
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def _usage(business_id):
    start, end = _month_period()
    records = db.session.scalars(
        select(AiUsageRecord).where(
            AiUsageRecord.business_id == business_id,
            AiUsageRecord.created_at >= start,
            AiUsageRecord.created_at < end,
        )
    ).all()
    plan_key = current_app.config.get("AI_DEFAULT_PLAN_KEY", "starter")
    plan_limits = current_app.config.get("AI_PLAN_LIMITS", {})
    limit = plan_limits.get(plan_key, current_app.config.get("AI_DEFAULT_PLAN_LIMIT", 100))
    return {
        "plan_key": plan_key,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "reply_count": len(records),
        "limit": limit,
        "remaining": max(0, limit - len(records)),
        "exhausted": len(records) >= limit,
    }


@assistant.get("/<business_id>/assistant/conversations")
@require_business_role()
def list_conversations(business_id):
    conversations = db.session.scalars(
        select(AiConversation)
        .where(
            AiConversation.business_id == business_id,
            AiConversation.user_id == g.current_user.id,
        )
        .order_by(AiConversation.updated_at.desc())
        .limit(100)
    ).all()
    return jsonify({
        "conversations": [_serialize_conversation(item) for item in conversations]
    })


@assistant.post("/<business_id>/assistant/conversations")
@require_business_role()
def create_conversation(business_id):
    payload = _payload()
    title = payload.get("title", "New business conversation")
    if not isinstance(title, str) or not title.strip():
        return error_response("validation_error", "Conversation title must be text.", 400)
    title = title.strip()[:160]
    conversation = AiConversation(
        business_id=business_id,
        user_id=g.current_user.id,
        title=title,
    )
    db.session.add(conversation)
    db.session.commit()
    return jsonify({"conversation": _serialize_conversation(conversation, True)}), 201


@assistant.get("/<business_id>/assistant/conversations/<conversation_id>")
@require_business_role()
def get_conversation(business_id, conversation_id):
    conversation = _find_conversation(business_id, conversation_id)
    if conversation is None:
        return error_response("conversation_not_found", "Conversation not found.", 404)
    return jsonify({"conversation": _serialize_conversation(conversation, True)})


@assistant.patch("/<business_id>/assistant/conversations/<conversation_id>")
@require_business_role()
def rename_conversation(business_id, conversation_id):
    conversation = _find_conversation(business_id, conversation_id)
    if conversation is None:
        return error_response("conversation_not_found", "Conversation not found.", 404)
    payload = _payload()
    title = payload.get("title")
    if not isinstance(title, str) or not title.strip() or len(title.strip()) > 160:
        return error_response("validation_error", "Title must be between 1 and 160 characters.", 400)
    conversation.title = title.strip()
    db.session.commit()
    return jsonify({"conversation": _serialize_conversation(conversation, True)})


@assistant.delete("/<business_id>/assistant/conversations/<conversation_id>")
@require_business_role()
def delete_conversation(business_id, conversation_id):
    conversation = _find_conversation(business_id, conversation_id)
    if conversation is None:
        return error_response("conversation_not_found", "Conversation not found.", 404)
    db.session.delete(conversation)
    db.session.commit()
    return jsonify({"message": "Conversation deleted."})


@assistant.post("/<business_id>/assistant/chat")
@require_business_role()
def chat(business_id):
    payload = _payload()
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        return error_response("validation_error", "Message must be text.", 400)
    message = message.strip()[:4000]
    request_id = payload.get("request_id")
    if request_id is not None and (
        not isinstance(request_id, str)
        or not request_id.strip()
        or len(request_id.strip()) > 64
    ):
        return error_response("validation_error", "Request ID must be text under 64 characters.", 400)
    request_id = request_id.strip() if isinstance(request_id, str) else secrets.token_hex(16)

    conversation_id = payload.get("conversation_id")
    conversation = None
    if conversation_id:
        conversation = _find_conversation(business_id, conversation_id)
        if conversation is None:
            return error_response("conversation_not_found", "Conversation not found.", 404)
    if conversation is None:
        conversation = AiConversation(
            business_id=business_id,
            user_id=g.current_user.id,
            title=message[:160],
        )
        db.session.add(conversation)
        db.session.flush()

    existing = db.session.scalar(
        select(AiMessage).where(
            AiMessage.conversation_id == conversation.id,
            AiMessage.request_id == request_id,
            AiMessage.role == "assistant",
        )
    )
    if existing:
        return jsonify({
            "conversation": _serialize_conversation(conversation, True),
            "message": {
                "id": existing.id,
                "role": "assistant",
                "content": existing.content,
                "created_at": existing.created_at.isoformat(),
            },
            "usage": _usage(business_id),
            "idempotent": True,
        })

    usage = _usage(business_id)
    if usage["exhausted"]:
        return error_response(
            "ai_usage_limit",
            "Your AI reply limit for this billing period has been reached.",
            429,
        )

    period = payload.get("period", "this_month")
    try:
        context = build_business_context(business_id, period)
    except ValueError as error:
        return error_response("validation_error", str(error), 400)

    user_message = AiMessage(
        conversation_id=conversation.id,
        role="user",
        content=message,
    )
    db.session.add(user_message)

    recent = list(conversation.messages)[-current_app.config["AI_MAX_CONTEXT_MESSAGES"]:]
    history = [
        {"role": item.role, "content": item.content}
        for item in recent
        if item.role in {"user", "assistant"}
    ]
    history.append({"role": "user", "content": message})
    system_prompt = (
        "You are Steer's read-only Nigerian business analyst. "
        "Use only the supplied verified business data. Never invent figures or records. "
        "Do not perform transactions or claim that you changed data. "
        "Separate verified facts from recommendations. "
        "Use NGN and the ₦ symbol. "
        "If a requested fact is absent, state that it is unavailable."
    )
    provider_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": "Verified backend data:\n" + json.dumps(context, ensure_ascii=False)},
        *history,
    ]

    try:
        response = call_ai_provider(provider_messages)
    except AiProviderError as error:
        db.session.rollback()
        return error_response(error.code, str(error), error.status)

    assistant_message = AiMessage(
        conversation_id=conversation.id,
        role="assistant",
        content=response["content"],
        request_id=request_id,
        metadata_json=json.dumps({
            "period": period,
            "provider_model": current_app.config.get("AI_MODEL"),
        }),
    )
    db.session.add(assistant_message)
    start, end = _month_period()
    db.session.add(AiUsageRecord(
        business_id=business_id,
        user_id=g.current_user.id,
        conversation_id=conversation.id,
        request_id=request_id,
        plan_key=usage["plan_key"],
        period_start=start,
        period_end=end,
        provider="configured-ai-provider",
        model=response_metadata_model(),
        input_tokens=response["input_tokens"],
        output_tokens=response["output_tokens"],
    ))
    conversation.updated_at = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify({
        "conversation": _serialize_conversation(conversation, True),
        "message": {
            "id": assistant_message.id,
            "role": "assistant",
            "content": assistant_message.content,
            "created_at": assistant_message.created_at.isoformat(),
        },
        "usage": _usage(business_id),
        "verified_context_period": context["period"],
    }), 201


def response_metadata_model():
    return current_app.config.get("AI_MODEL")


@assistant.get("/<business_id>/assistant/usage")
@require_business_role()
def usage(business_id):
    return jsonify({"usage": _usage(business_id)})


@assistant.get("/<business_id>/assistant/insights")
@require_business_role()
def insights(business_id):
    period = request.args.get("period", "this_month")
    try:
        context = build_business_context(business_id, period)
    except ValueError as error:
        return error_response("validation_error", str(error), 400)
    return jsonify({
        "period": context["period"],
        "insights": {
            "financial_summary": context["financial_summary"],
            "best_selling_products": context["best_selling_products"],
            "profit_by_product": context["profit_by_product"],
            "low_stock_products": context["low_stock_products"],
            "outstanding_customer_balances": context["outstanding_customer_balances"],
            "expenses_by_category": context["expenses_by_category"],
        },
    })


@assistant.get("/<business_id>/assistant/reports")
@require_business_role()
def reports(business_id):
    period = request.args.get("period", "this_month")
    try:
        context = build_business_context(business_id, period)
    except ValueError as error:
        return error_response("validation_error", str(error), 400)
    return jsonify({
        "period": context["period"],
        "report": {
            "financial_summary": context["financial_summary"],
            "sales": {
                "best_selling_products": context["best_selling_products"],
                "profit_by_product": context["profit_by_product"],
            },
            "expenses": {
                "by_category": context["expenses_by_category"],
            },
            "inventory": {
                "inventory_units": context["inventory_units"],
                "low_stock_products": context["low_stock_products"],
            },
            "customers": {
                "outstanding_balances": context["outstanding_customer_balances"],
            },
        },
    })
