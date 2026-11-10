"""Product and inventory management endpoints."""

from flask import Blueprint, g, jsonify, request

from app import db
from app.models import Product
from app.security import require_business_role
from app.services.product_service import (
    ProductInputError,
    apply_stock_adjustment,
    find_product,
    search_products,
    serialize_movement,
    serialize_product,
    validate_product_input,
)

products = Blueprint("products", __name__)


def error_response(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status


def _request_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ProductInputError("A JSON request body is required.")
    return payload


def _positive_integer(value, field, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ProductInputError(f"{field} must be a positive whole number.") from None
    if parsed < 1 or parsed > maximum:
        raise ProductInputError(f"{field} must be between 1 and {maximum}.")
    return parsed


@products.get("/<business_id>/products")
@require_business_role()
def list_products(business_id):
    try:
        search = request.args.get("q", "").strip()
        if len(search) > 100:
            raise ProductInputError("Search text must be 100 characters or fewer.")
        product_type = request.args.get("type", "all").strip().lower()
        if product_type not in {"all", "product", "service"}:
            raise ProductInputError("Type filter must be 'all', 'product', or 'service'.")
        low_stock_only = request.args.get("low_stock", "0").strip().lower() in {"1", "true", "yes"}
        page = _positive_integer(request.args.get("page", "1"), "Page", 1000000)
        per_page = _positive_integer(request.args.get("per_page", "25"), "Page size", 100)
    except ProductInputError as error:
        return error_response("validation_error", str(error), 400)

    records, total = search_products(
        business_id,
        search,
        product_type if product_type != "all" else "all",
        low_stock_only,
        page,
        per_page,
    )

    return jsonify(
        {
            "products": [serialize_product(product) for product in records],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": max(1, (total + per_page - 1) // per_page) if total else 0,
            },
        }
    )


@products.post("/<business_id>/products")
@require_business_role("owner", "manager")
def create_product(business_id):
    try:
        data = validate_product_input(_request_payload())
    except ProductInputError as error:
        return error_response("validation_error", str(error), 400)

    product = Product(business_id=business_id, **data)
    db.session.add(product)
    db.session.commit()
    return jsonify({"product": serialize_product(product)}), 201


@products.get("/<business_id>/products/<product_id>")
@require_business_role()
def get_product(business_id, product_id):
    product = find_product(business_id, product_id)
    if product is None:
        return error_response("product_not_found", "Product not found.", 404)
    history = [serialize_movement(item) for item in product.inventory_movements[:10]]
    return jsonify({"product": serialize_product(product), "movements": history})


@products.patch("/<business_id>/products/<product_id>")
@require_business_role("owner", "manager")
def update_product(business_id, product_id):
    product = find_product(business_id, product_id)
    if product is None:
        return error_response("product_not_found", "Product not found.", 404)
    try:
        data = validate_product_input(_request_payload(), partial=True)
    except ProductInputError as error:
        return error_response("validation_error", str(error), 400)

    for field, value in data.items():
        setattr(product, field, value)
    db.session.commit()
    return jsonify({"product": serialize_product(product)})


@products.post("/<business_id>/products/<product_id>/archive")
@require_business_role("owner", "manager")
def archive_product(business_id, product_id):
    product = find_product(business_id, product_id)
    if product is None:
        return error_response("product_not_found", "Product not found.", 404)
    product.is_archived = True
    product.is_active = False
    db.session.commit()
    return jsonify({"message": "Product archived."})


@products.post("/<business_id>/products/<product_id>/stock-adjustment")
@require_business_role("owner", "manager")
def adjust_stock(business_id, product_id):
    product = find_product(business_id, product_id)
    if product is None:
        return error_response("product_not_found", "Product not found.", 404)
    try:
        payload = _request_payload()
        delta_quantity = payload.get("delta_quantity")
        reason = payload.get("reason", "manual_adjustment")
        note = payload.get("note")
        if not isinstance(reason, str) or not reason.strip():
            raise ProductInputError("Reason is required.")
        if note is not None and not isinstance(note, str):
            raise ProductInputError("Note must be text.")
        movement = apply_stock_adjustment(
            product,
            delta_quantity=delta_quantity,
            reason=reason.strip()[:64],
            note=note.strip()[:500] if note else None,
            user=g.current_user,
        )
    except ProductInputError as error:
        db.session.rollback()
        return error_response("validation_error", str(error), 400)

    db.session.commit()
    return jsonify({"product": serialize_product(product), "movement": serialize_movement(movement)})
