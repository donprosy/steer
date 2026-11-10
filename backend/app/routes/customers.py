"""Business-scoped customer management endpoints."""

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Customer
from app.security import require_business_role
from app.services.customer_service import (
    CustomerInputError,
    find_customer,
    search_customers,
    serialize_customer,
    validate_customer_input,
)

customers = Blueprint("customers", __name__)


def error_response(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status


def _request_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise CustomerInputError("A JSON request body is required.")
    return payload


def _positive_integer(value, field, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise CustomerInputError(f"{field} must be a positive whole number.") from None
    if parsed < 1 or parsed > maximum:
        raise CustomerInputError(f"{field} must be between 1 and {maximum}.")
    return parsed


@customers.get("/<business_id>/customers")
@require_business_role()
def list_customers(business_id):
    try:
        search = request.args.get("q", "").strip()
        if len(search) > 100:
            raise CustomerInputError("Search text must be 100 characters or fewer.")
        page = _positive_integer(request.args.get("page", "1"), "Page", 1000000)
        per_page = _positive_integer(request.args.get("per_page", "25"), "Page size", 100)
    except CustomerInputError as error:
        return error_response("validation_error", str(error), 400)

    records, total = search_customers(business_id, search, page, per_page)
    return jsonify(
        {
            "customers": [serialize_customer(customer) for customer in records],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
            },
        }
    )


@customers.post("/<business_id>/customers")
@require_business_role()
def create_customer(business_id):
    try:
        data = validate_customer_input(_request_payload())
    except CustomerInputError as error:
        return error_response("validation_error", str(error), 400)

    customer = Customer(business_id=business_id, **data)
    db.session.add(customer)
    db.session.commit()
    return jsonify({"customer": serialize_customer(customer)}), 201


@customers.get("/<business_id>/customers/<customer_id>")
@require_business_role()
def get_customer(business_id, customer_id):
    customer = find_customer(business_id, customer_id)
    if customer is None:
        return error_response("customer_not_found", "Customer not found.", 404)
    return jsonify({"customer": serialize_customer(customer)})


@customers.patch("/<business_id>/customers/<customer_id>")
@require_business_role()
def update_customer(business_id, customer_id):
    customer = find_customer(business_id, customer_id)
    if customer is None:
        return error_response("customer_not_found", "Customer not found.", 404)
    try:
        data = validate_customer_input(_request_payload(), partial=True)
    except CustomerInputError as error:
        return error_response("validation_error", str(error), 400)

    for field, value in data.items():
        setattr(customer, field, value)
    db.session.commit()
    return jsonify({"customer": serialize_customer(customer)})


@customers.delete("/<business_id>/customers/<customer_id>")
@require_business_role("owner", "manager")
def delete_customer(business_id, customer_id):
    customer = find_customer(business_id, customer_id)
    if customer is None:
        return error_response("customer_not_found", "Customer not found.", 404)
    db.session.delete(customer)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return error_response(
            "customer_in_use",
            "This customer has linked business records and cannot be deleted.",
            409,
        )
    return jsonify({"message": "Customer deleted."})
