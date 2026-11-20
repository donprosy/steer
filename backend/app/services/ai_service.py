"""Read-only business context assembly and configurable AI provider adapter."""

import json
import urllib.error
import urllib.request
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from flask import current_app
from sqlalchemy import func, or_, select

from app import db
from app.models import Customer, Expense, Product, Sale, SaleItem
from app.services.financial_service import summarize_business_finances


class AiProviderError(RuntimeError):
    def __init__(self, code, message, status=503):
        super().__init__(message)
        self.code = code
        self.status = status


def parse_period(period):
    now = datetime.now(timezone.utc)
    today = now.date()
    period = (period or "this_month").strip().lower()
    if period == "today":
        return datetime.combine(today, time.min, timezone.utc), now
    if period == "this_week":
        start = today - timedelta(days=today.weekday())
        return datetime.combine(start, time.min, timezone.utc), now
    if period == "this_year":
        start = today.replace(month=1, day=1)
        return datetime.combine(start, time.min, timezone.utc), now
    if period == "this_month":
        start = today.replace(day=1)
        return datetime.combine(start, time.min, timezone.utc), now
    raise ValueError("Period must be today, this_week, this_month, or this_year.")


def build_business_context(business_id, period="this_month"):
    start, end = parse_period(period)
    summary = summarize_business_finances(business_id, start, end)

    best_products = db.session.execute(
        select(Product.name, func.sum(SaleItem.quantity).label("units"), func.sum(SaleItem.line_total).label("revenue"))
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(
            Product.business_id == business_id,
            Sale.business_id == business_id,
            Sale.status.notin_(("cancelled", "refunded")),
            Sale.sale_date >= start,
            Sale.sale_date <= end,
        )
        .group_by(Product.name)
        .order_by(func.sum(SaleItem.line_total).desc())
        .limit(10)
    ).all()
    profitable_products = db.session.execute(
        select(
            Product.name,
            func.sum(SaleItem.line_total).label("revenue"),
            func.sum(SaleItem.quantity * SaleItem.unit_cost).label("cost"),
        )
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(
            Product.business_id == business_id,
            Sale.business_id == business_id,
            Sale.status.notin_(("cancelled", "refunded")),
            Sale.sale_date >= start,
            Sale.sale_date <= end,
        )
        .group_by(Product.name)
        .order_by(func.sum(SaleItem.line_total - SaleItem.quantity * SaleItem.unit_cost).desc())
        .limit(10)
    ).all()

    low_stock = db.session.execute(
        select(Product.name, Product.quantity_on_hand, Product.reorder_level)
        .where(
            Product.business_id == business_id,
            Product.type == "product",
            Product.is_archived.is_(False),
            or_(
                Product.quantity_on_hand <= 0,
                Product.quantity_on_hand <= Product.reorder_level,
            ),
        )
        .order_by(Product.quantity_on_hand.asc())
        .limit(10)
    ).all()

    customers = db.session.execute(
        select(Customer)
        .where(Customer.business_id == business_id)
        .order_by(Customer.created_at.desc())
        .limit(20)
    ).scalars().all()
    customer_balances = []
    for customer in customers:
        sales = [sale for sale in customer.sales if sale.status not in {"cancelled", "refunded"}]
        total = sum((sale.total_amount for sale in sales), Decimal("0"))
        paid = sum(
            (
                payment.amount
                for sale in sales
                for payment in sale.payments
                if payment.direction == "incoming" and payment.status == "received"
            ),
            Decimal("0"),
        )
        balance = max(Decimal("0"), total - paid)
        if balance > 0:
            customer_balances.append({
                "customer": customer.full_name,
                "outstanding_balance": format(balance, ".2f"),
            })

    expense_rows = db.session.execute(
        select(Expense.category, func.sum(Expense.amount).label("amount"))
        .where(
            Expense.business_id == business_id,
            Expense.expense_date >= start,
            Expense.expense_date <= end,
        )
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .limit(10)
    ).all()

    inventory_units = db.session.scalar(
        select(func.coalesce(func.sum(Product.quantity_on_hand), 0)).where(
            Product.business_id == business_id,
            Product.type == "product",
            Product.is_archived.is_(False),
        )
    ) or 0

    return {
        "currency": "NGN",
        "period": {
            "label": period,
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "financial_summary": summary,
        "best_selling_products": [
            {"name": name, "units_sold": str(units), "revenue": format(revenue or 0, ".2f")}
            for name, units, revenue in best_products
        ],
        "profit_by_product": [
            {
                "name": name,
                "profit": format((revenue or 0) - (cost or 0), ".2f"),
                "revenue": format(revenue or 0, ".2f"),
                "cogs": format(cost or 0, ".2f"),
            }
            for name, revenue, cost in profitable_products
        ],
        "low_stock_products": [
            {"name": name, "quantity_on_hand": str(quantity), "reorder_level": str(reorder)}
            for name, quantity, reorder in low_stock
        ],
        "inventory_units": str(inventory_units),
        "expenses_by_category": [
            {"category": category, "amount": format(amount or 0, ".2f")}
            for category, amount in expense_rows
        ],
        "outstanding_customer_balances": sorted(
            customer_balances,
            key=lambda item: Decimal(item["outstanding_balance"]),
            reverse=True,
        )[:10],
    }


def provider_configured():
    return bool(
        current_app.config.get("AI_API_KEY")
        and current_app.config.get("AI_BASE_URL")
        and current_app.config.get("AI_MODEL")
    )


def call_ai_provider(messages):
    if not provider_configured():
        raise AiProviderError(
            "ai_not_configured",
            "The AI provider is not configured. Contact the administrator.",
        )

    base_url = current_app.config["AI_BASE_URL"].rstrip("/")
    chat_path = current_app.config.get("AI_CHAT_PATH", "/chat/completions").strip()
    if not chat_path.startswith("/"):
        chat_path = f"/{chat_path}"
    url = f"{base_url}{chat_path}"
    api_format = current_app.config.get("AI_API_FORMAT", "openai_chat")

    if api_format == "openai_chat":
        payload = {
            "model": current_app.config["AI_MODEL"],
            "messages": messages,
            "temperature": 0.2,
        }
    else:
        payload = {
            "model": current_app.config["AI_MODEL"],
            "messages": messages,
        }

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"{current_app.config.get('AI_AUTH_SCHEME', 'Bearer')} {current_app.config['AI_API_KEY']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            request,
            timeout=float(current_app.config.get("AI_TIMEOUT_SECONDS", 30)),
        ) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:500]
        raise AiProviderError(
            "ai_provider_error",
            "The AI provider rejected the request.",
            502,
        ) from error
    except (urllib.error.URLError, TimeoutError):
        raise AiProviderError(
            "ai_provider_unavailable",
            "The AI provider is unavailable or timed out. Please try again.",
        )
    except json.JSONDecodeError:
        raise AiProviderError(
            "ai_provider_error",
            "The AI provider returned an invalid response.",
            502,
        )

    content = extract_provider_content(body)
    usage = body.get("usage") if isinstance(body, dict) else None
    input_tokens = usage.get("prompt_tokens") if isinstance(usage, dict) else None
    output_tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
    if input_tokens is None and isinstance(usage, dict):
        input_tokens = usage.get("input_tokens")
    if output_tokens is None and isinstance(usage, dict):
        output_tokens = usage.get("output_tokens")
    return {
        "content": content,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    }


def extract_provider_content(body):
    if not isinstance(body, dict):
        raise AiProviderError("ai_provider_error", "The AI provider returned an invalid response.", 502)
    choices = body.get("choices")
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            return message["content"].strip()
        if isinstance(choices[0], dict) and isinstance(choices[0].get("text"), str):
            return choices[0]["text"].strip()
    for key in ("response", "answer", "content", "output_text"):
        value = body.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise AiProviderError("ai_provider_error", "The AI provider returned no usable response.", 502)
