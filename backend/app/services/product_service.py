"""Validation and search helpers for business products and inventory."""

from decimal import Decimal, InvalidOperation

from sqlalchemy import func, or_, select

from app import db
from app.models import InventoryMovement, Product
from app.services.auth_service import normalized_datetime

PRODUCT_FIELDS = {
    "name",
    "category",
    "type",
    "sku",
    "description",
    "selling_price",
    "purchase_cost",
    "quantity_on_hand",
    "reorder_level",
    "stock_unit",
    "is_active",
    "is_archived",
}


class ProductInputError(ValueError):
    """Raised when product data is invalid."""


def _decimal_from_value(value, field_name, *, minimum=Decimal("0"), allow_zero=True):
    if value is None:
        if allow_zero:
            return Decimal("0")
        raise ProductInputError(f"{field_name} is required.")
    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, int):
        number = Decimal(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ProductInputError(f"{field_name} must not be empty.")
        try:
            number = Decimal(stripped)
        except InvalidOperation as error:
            raise ProductInputError(f"Enter a valid {field_name}.") from error
    else:
        raise ProductInputError(f"{field_name} must be a number.")
    if not number.is_finite():
        raise ProductInputError(f"Enter a valid {field_name}.")
    if number < minimum:
        raise ProductInputError(f"{field_name} must be at least {minimum}.")
    return number


def _string_field(value, field_name, maximum, *, required=False):
    if value is None:
        if required:
            raise ProductInputError(f"{field_name} is required.")
        return None
    if not isinstance(value, str):
        raise ProductInputError(f"{field_name} must be text.")
    cleaned = value.strip()
    if required and not cleaned:
        raise ProductInputError(f"{field_name} is required.")
    if cleaned and len(cleaned) > maximum:
        raise ProductInputError(f"{field_name} must be {maximum} characters or fewer.")
    return cleaned or None


def validate_product_input(payload, partial=False):
    if not isinstance(payload, dict):
        raise ProductInputError("A JSON request body is required.")

    unknown_fields = set(payload) - PRODUCT_FIELDS
    if unknown_fields:
        raise ProductInputError(f"Unsupported product field: {sorted(unknown_fields)[0]}.")
    if partial and not payload:
        raise ProductInputError("Provide at least one product field to update.")

    if not partial:
        required_fields = {"name", "category", "selling_price"}
        missing = sorted(required_fields - set(payload))
        if missing:
            raise ProductInputError(f"{missing[0].replace('_', ' ').capitalize()} is required.")

    data = {}
    if "name" in payload:
        data["name"] = _string_field(payload["name"], "Name", 160, required=True)
    if "category" in payload:
        data["category"] = _string_field(payload["category"], "Category", 80, required=True)
    if "type" in payload:
        product_type = payload["type"]
        if product_type not in {"product", "service"}:
            raise ProductInputError("Type must be either 'product' or 'service'.")
        data["type"] = product_type
    if "sku" in payload:
        value = _string_field(payload["sku"], "SKU", 64)
        data["sku"] = value.upper() if value else None
    if "description" in payload:
        data["description"] = _string_field(payload["description"], "Description", 2000)
    if "selling_price" in payload:
        price = _decimal_from_value(payload["selling_price"], "Selling price")
        data["selling_price"] = price.quantize(Decimal("0.01"))
    if "purchase_cost" in payload:
        cost = _decimal_from_value(payload["purchase_cost"], "Purchase cost")
        data["purchase_cost"] = cost.quantize(Decimal("0.01"))
    if "quantity_on_hand" in payload:
        quantity = _decimal_from_value(payload["quantity_on_hand"], "Quantity on hand")
        data["quantity_on_hand"] = quantity.quantize(Decimal("0.001"))
    if "reorder_level" in payload:
        reorder_level = _decimal_from_value(payload["reorder_level"], "Reorder level")
        data["reorder_level"] = reorder_level.quantize(Decimal("0.001"))
    if "stock_unit" in payload:
        value = _string_field(payload["stock_unit"], "Stock unit", 32)
        data["stock_unit"] = value or "unit"
    if "is_active" in payload:
        if not isinstance(payload["is_active"], bool):
            raise ProductInputError("Active status must be true or false.")
        data["is_active"] = payload["is_active"]
    if "is_archived" in payload:
        if not isinstance(payload["is_archived"], bool):
            raise ProductInputError("Archived status must be true or false.")
        data["is_archived"] = payload["is_archived"]
    if "type" in data and data["type"] == "service":
        data["quantity_on_hand"] = Decimal("0")
        data["reorder_level"] = Decimal("0")
        data["stock_unit"] = "service"
    if not data:
        raise ProductInputError("Provide at least one product field to update.")
    return data


def search_products(business_id, search, product_type, low_stock_only, page, per_page):
    filters = [Product.business_id == business_id, Product.is_archived.is_(False)]
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        filters.append(
            or_(
                Product.name.ilike(pattern, escape="\\"),
                Product.category.ilike(pattern, escape="\\"),
                Product.sku.ilike(pattern, escape="\\"),
            )
        )
    if product_type in {"product", "service"}:
        filters.append(Product.type == product_type)
    if low_stock_only:
        filters.extend(
            [
                Product.type == "product",
                Product.quantity_on_hand <= Product.reorder_level,
                Product.reorder_level > 0,
            ]
        )

    total = db.session.scalar(select(func.count()).select_from(Product).where(*filters)) or 0
    rows = db.session.scalars(
        select(Product)
        .where(*filters)
        .order_by(Product.created_at.desc(), Product.id)
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    return rows, total


def find_product(business_id, product_id):
    return db.session.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.business_id == business_id,
            Product.is_archived.is_(False),
        )
    )


def serialize_decimal(value, *, currency=False):
    if value is None:
        return None
    if currency:
        return format(value.quantize(Decimal("0.01")), "f")
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized.quantize(Decimal("1")), "f")
    return format(normalized, "f")


def serialize_product(product):
    return {
        "id": product.id,
        "business_id": product.business_id,
        "name": product.name,
        "category": product.category,
        "type": product.type,
        "sku": product.sku,
        "description": product.description,
        "selling_price": serialize_decimal(product.selling_price, currency=True),
        "purchase_cost": serialize_decimal(product.purchase_cost, currency=True),
        "quantity_on_hand": serialize_decimal(product.quantity_on_hand),
        "reorder_level": serialize_decimal(product.reorder_level),
        "stock_unit": product.stock_unit,
        "is_active": product.is_active,
        "is_archived": product.is_archived,
        "created_at": normalized_datetime(product.created_at).isoformat(),
        "updated_at": normalized_datetime(product.updated_at).isoformat(),
    }


def serialize_movement(movement):
    return {
        "id": movement.id,
        "product_id": movement.product_id,
        "business_id": movement.business_id,
        "delta_quantity": serialize_decimal(movement.delta_quantity),
        "quantity_after": serialize_decimal(movement.quantity_after),
        "unit_cost": serialize_decimal(movement.unit_cost, currency=True),
        "reason": movement.reason,
        "note": movement.note,
        "created_at": normalized_datetime(movement.created_at).isoformat(),
    }


def apply_stock_adjustment(product, *, delta_quantity, reason, note=None, user=None):
    if product.type != "product":
        raise ProductInputError("Inventory adjustments apply only to physical products.")
    delta = _decimal_from_value(delta_quantity, "Quantity change", minimum=Decimal("-9999999999"), allow_zero=False)
    if delta == 0:
        raise ProductInputError("Quantity change must be non-zero.")
    updated_quantity = product.quantity_on_hand + delta
    if updated_quantity < 0:
        raise ProductInputError("Stock cannot go below zero.")

    product.quantity_on_hand = updated_quantity
    movement = InventoryMovement(
        business_id=product.business_id,
        product_id=product.id,
        user_id=getattr(user, "id", None),
        delta_quantity=delta,
        quantity_after=updated_quantity,
        unit_cost=product.purchase_cost,
        reason=reason,
        note=note,
    )
    db.session.add(movement)
    return movement
