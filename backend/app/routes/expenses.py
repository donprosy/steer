"""Expense management endpoints."""

from datetime import datetime

from flask import Blueprint, g, jsonify, request

from app import db
from app.models import Expense
from app.security import require_business_role
from app.services.expense_service import (
    ExpenseInputError,
    search_expenses,
    serialize_expense,
    validate_expense_input,
)

expenses = Blueprint("expenses", __name__)


def error_response(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status


def _request_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ExpenseInputError("A JSON request body is required.")
    return payload


@expenses.get("/<business_id>/expenses")
@require_business_role()
def list_expenses(business_id):
    try:
        search = request.args.get("q", "").strip()
        page = max(1, int(request.args.get("page", "1")))
        per_page = min(100, max(1, int(request.args.get("per_page", "25"))))
        start_date_raw = request.args.get("start_date")
        end_date_raw = request.args.get("end_date")
    except ValueError:
        return error_response("validation_error", "Pagination values must be valid integers.", 400)

    start_date = datetime.fromisoformat(start_date_raw) if start_date_raw else None
    end_date = datetime.fromisoformat(end_date_raw) if end_date_raw else None

    rows, total = search_expenses(
        business_id,
        search,
        page,
        per_page,
        start_date=start_date,
        end_date=end_date,
    )
    return jsonify({
        "expenses": [serialize_expense(expense) for expense in rows],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": max(1, (total + per_page - 1) // per_page) if total else 0,
        },
    })


@expenses.post("/<business_id>/expenses")
@require_business_role("owner", "manager", "staff")
def create_expense(business_id):
    try:
        data = validate_expense_input(_request_payload())
        expense = Expense(business_id=business_id, **data)
        db.session.add(expense)
        db.session.commit()
    except ExpenseInputError as exc:
        db.session.rollback()
        return error_response("validation_error", str(exc), 400)
    except Exception:
        db.session.rollback()
        return error_response("expense_failed", "The expense could not be recorded.", 500)
    return jsonify({"expense": serialize_expense(expense)}), 201


@expenses.patch("/<business_id>/expenses/<expense_id>")
@require_business_role("owner", "manager")
def update_expense(business_id, expense_id):
    expense = db.session.get(Expense, expense_id)
    if expense is None or expense.business_id != business_id:
        return error_response("expense_not_found", "Expense not found.", 404)
    try:
        data = validate_expense_input(_request_payload(), partial=True)
        for field, value in data.items():
            setattr(expense, field, value)
        db.session.commit()
    except ExpenseInputError as exc:
        db.session.rollback()
        return error_response("validation_error", str(exc), 400)
    return jsonify({"expense": serialize_expense(expense)})


@expenses.delete("/<business_id>/expenses/<expense_id>")
@require_business_role("owner", "manager")
def delete_expense(business_id, expense_id):
    expense = db.session.get(Expense, expense_id)
    if expense is None or expense.business_id != business_id:
        return error_response("expense_not_found", "Expense not found.", 404)
    db.session.delete(expense)
    db.session.commit()
    return jsonify({"message": "Expense deleted."})
