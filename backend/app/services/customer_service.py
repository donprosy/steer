"""Validation and business-scoped customer operations."""

import re
from decimal import Decimal

from sqlalchemy import func, or_, select

from app import db
from app.models import Customer
from app.services.auth_service import (
    AccountInputError,
    normalize_email,
    normalized_datetime,
)

CUSTOMER_FIELDS = {"full_name", "phone", "email", "address", "notes"}
PHONE_PATTERN = re.compile(r"\+?[\d\s().-]+")


class CustomerInputError(ValueError):
    """Raised when customer fields are invalid."""


def validate_customer_input(payload, partial=False):
    if not isinstance(payload, dict):
        raise CustomerInputError("A JSON request body is required.")

    unknown_fields = set(payload) - CUSTOMER_FIELDS
    if unknown_fields:
        raise CustomerInputError(
            f"Unsupported customer field: {sorted(unknown_fields)[0]}."
        )
    if partial and not payload:
        raise CustomerInputError("Provide at least one customer field to update.")
    if not partial:
        missing_fields = {"full_name", "phone"} - set(payload)
        if missing_fields:
            raise CustomerInputError(
                f"{sorted(missing_fields)[0].replace('_', ' ').capitalize()} is required."
            )

    data = {}
    for field, maximum in (
        ("full_name", 160),
        ("phone", 32),
        ("email", 254),
        ("address", 500),
        ("notes", 2000),
    ):
        if field not in payload:
            continue
        value = payload[field]
        if value is None and field in {"email", "address", "notes"}:
            data[field] = None
            continue
        if not isinstance(value, str):
            raise CustomerInputError(f"{field.replace('_', ' ').capitalize()} must be text.")
        value = value.strip()
        if field in {"email", "address", "notes"} and not value:
            data[field] = None
            continue
        if not value:
            raise CustomerInputError(f"{field.replace('_', ' ').capitalize()} is required.")
        if len(value) > maximum:
            raise CustomerInputError(
                f"{field.replace('_', ' ').capitalize()} must be {maximum} characters or fewer."
            )
        if field == "phone":
            digits = sum(character.isdigit() for character in value)
            if not PHONE_PATTERN.fullmatch(value) or not 7 <= digits <= 18:
                raise CustomerInputError("Enter a valid phone number.")
        elif field == "email":
            try:
                value = normalize_email(value)
            except AccountInputError as error:
                raise CustomerInputError("Enter a valid email address.") from error
        data[field] = value
    return data


def search_customers(business_id, search, page, per_page):
    filters = [Customer.business_id == business_id]
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        filters.append(
            or_(
                Customer.full_name.ilike(pattern, escape="\\"),
                Customer.phone.ilike(pattern, escape="\\"),
                Customer.email.ilike(pattern, escape="\\"),
            )
        )

    total = db.session.scalar(
        select(func.count()).select_from(Customer).where(*filters)
    ) or 0
    customers = db.session.scalars(
        select(Customer)
        .where(*filters)
        .order_by(Customer.created_at.desc(), Customer.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return customers, total


def find_customer(business_id, customer_id):
    return db.session.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.business_id == business_id,
        )
    )


def summarize_customer_finances(customer):
    sales = [sale for sale in customer.sales if sale.status != "cancelled"]
    total_purchases = sum((sale.total_amount for sale in sales), Decimal("0.00"))
    collected = sum(
        (
            payment.amount
            for sale in sales
            for payment in sale.payments
            if payment.direction == "incoming" and payment.status == "received"
        ),
        Decimal("0.00"),
    )
    refunds = sum(
        (
            payment.amount
            for sale in sales
            for payment in sale.payments
            if payment.direction == "refund" and payment.status == "received"
        ),
        Decimal("0.00"),
    )
    outstanding_balance = max(Decimal("0.00"), total_purchases - collected + refunds)
    purchase_history = [
        {
            "id": sale.reference_number,
            "date": normalized_datetime(sale.sale_date).isoformat(),
            "amount": format_decimal(sale.total_amount),
            "status": sale.status,
            "outstanding_balance": format_decimal(
                max(Decimal("0.00"), sale.total_amount - sum((payment.amount for payment in sale.payments if payment.direction == "incoming" and payment.status == "received"), Decimal("0.00")) + sum((payment.amount for payment in sale.payments if payment.direction == "refund" and payment.status == "received"), Decimal("0.00")))
            ),
        }
        for sale in sorted(sales, key=lambda item: item.sale_date, reverse=True)
    ]
    return {
        "total_purchases": format_decimal(total_purchases),
        "amount_paid": format_decimal(collected),
        "refund_total": format_decimal(refunds),
        "outstanding_balance": format_decimal(outstanding_balance),
        "purchase_history": purchase_history,
    }


def format_decimal(value):
    if value is None:
        return None
    return format(value.quantize(Decimal("0.01")), "f")


def serialize_customer(customer):
    summary = summarize_customer_finances(customer)
    return {
        "id": customer.id,
        "business_id": customer.business_id,
        "full_name": customer.full_name,
        "phone": customer.phone,
        "email": customer.email,
        "address": customer.address,
        "notes": customer.notes,
        "total_purchases": summary["total_purchases"],
        "amount_paid": summary["amount_paid"],
        "refund_total": summary["refund_total"],
        "outstanding_balance": summary["outstanding_balance"],
        "purchase_history": summary["purchase_history"],
        "created_at": normalized_datetime(customer.created_at).isoformat(),
        "updated_at": normalized_datetime(customer.updated_at).isoformat(),
    }
