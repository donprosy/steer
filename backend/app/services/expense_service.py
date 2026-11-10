"""Business expense validation and persistence."""

from decimal import Decimal, InvalidOperation

from sqlalchemy import func, or_, select

from app import db
from app.models import Expense
from app.services.auth_service import normalized_datetime

EXPENSE_FIELDS = {"category", "description", "amount", "payment_method", "expense_date", "notes"}


class ExpenseInputError(ValueError):
    """Raised for invalid expense payloads."""


def _decimal(value, field_name):
    if value is None:
        raise ExpenseInputError(f"{field_name} is required.")
    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, int):
        number = Decimal(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ExpenseInputError(f"{field_name} is required.")
        try:
            number = Decimal(stripped)
        except InvalidOperation as error:
            raise ExpenseInputError(f"Enter a valid {field_name}.") from error
    else:
        raise ExpenseInputError(f"{field_name} must be a number.")
    if not number.is_finite() or number <= 0:
        raise ExpenseInputError(f"{field_name} must be greater than zero.")
    return number.quantize(Decimal("0.01"))


def validate_expense_input(payload, partial=False):
    if not isinstance(payload, dict):
        raise ExpenseInputError("A JSON request body is required.")
    unknown_fields = set(payload) - EXPENSE_FIELDS
    if unknown_fields:
        raise ExpenseInputError(f"Unsupported expense field: {sorted(unknown_fields)[0]}.")
    if not partial and not set({"category", "description", "amount", "payment_method"}) <= set(payload):
        raise ExpenseInputError("Category, description, amount, and payment method are required.")
    if partial and not payload:
        raise ExpenseInputError("Provide at least one expense field to update.")

    data = {}
    if "category" in payload:
        category = payload["category"]
        if not isinstance(category, str) or not category.strip():
            raise ExpenseInputError("Category is required.")
        data["category"] = category.strip()[:80]
    if "description" in payload:
        description = payload["description"]
        if not isinstance(description, str) or not description.strip():
            raise ExpenseInputError("Description is required.")
        data["description"] = description.strip()[:255]
    if "amount" in payload:
        data["amount"] = _decimal(payload["amount"], "Amount")
    if "payment_method" in payload:
        method = payload["payment_method"]
        if method not in {"cash", "bank_transfer", "pos", "other"}:
            raise ExpenseInputError("Unsupported payment method.")
        data["payment_method"] = method
    if "expense_date" in payload:
        value = payload["expense_date"]
        if not isinstance(value, str):
            raise ExpenseInputError("Expense date must be a date string.")
        try:
            from datetime import datetime
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as error:
            raise ExpenseInputError("Expense date is invalid.") from error
        data["expense_date"] = parsed
    if "notes" in payload:
        notes = payload["notes"]
        if notes is not None and (not isinstance(notes, str) or len(notes.strip()) > 2000):
            raise ExpenseInputError("Notes must be text under 2000 characters.")
        data["notes"] = notes.strip() if isinstance(notes, str) and notes.strip() else None
    if not data:
        raise ExpenseInputError("Provide at least one expense field to update.")
    return data


def search_expenses(business_id, search, page, per_page, start_date=None, end_date=None):
    filters = [Expense.business_id == business_id]
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        filters.append(or_(Expense.description.ilike(pattern, escape="\\"), Expense.category.ilike(pattern, escape="\\")))
    if start_date is not None:
        filters.append(Expense.expense_date >= start_date)
    if end_date is not None:
        filters.append(Expense.expense_date <= end_date)
    total = db.session.scalar(select(func.count()).select_from(Expense).where(*filters)) or 0
    rows = db.session.scalars(
        select(Expense)
        .where(*filters)
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return rows, total


def serialize_expense(expense):
    return {
        "id": expense.id,
        "business_id": expense.business_id,
        "category": expense.category,
        "description": expense.description,
        "amount": format_decimal(expense.amount),
        "payment_method": expense.payment_method,
        "expense_date": normalized_datetime(expense.expense_date).isoformat(),
        "notes": expense.notes,
        "created_at": normalized_datetime(expense.created_at).isoformat(),
        "updated_at": normalized_datetime(expense.updated_at).isoformat(),
    }


def format_decimal(value):
    if value is None:
        return None
    return format(value.quantize(Decimal("0.01")), "f")
