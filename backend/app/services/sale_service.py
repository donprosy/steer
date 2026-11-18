"""Sales, payments, receipts, and refund logic."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import func, select

from app import db
from app.models import Customer, InventoryMovement, Payment, Product, Sale, SaleItem
from app.services.auth_service import normalized_datetime


class SaleInputError(ValueError):
    """Raised when sale payloads are invalid."""


def _decimal(value, field_name, decimal_places=2):
    if value is None:
        raise SaleInputError(f"{field_name} is required.")
    if isinstance(value, Decimal):
        number = value
    elif isinstance(value, int):
        number = Decimal(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise SaleInputError(f"{field_name} is required.")
        try:
            number = Decimal(stripped)
        except InvalidOperation as error:
            raise SaleInputError(f"Enter a valid {field_name}.") from error
    else:
        raise SaleInputError(f"{field_name} must be a number.")
    if not number.is_finite() or number < 0:
        raise SaleInputError(f"Enter a valid {field_name}.")
    quantum = Decimal("1").scaleb(-decimal_places)
    return number.quantize(quantum)


def _quantity(value, field_name):
    quantity = _decimal(value, field_name, decimal_places=3)
    if quantity <= 0:
        raise SaleInputError(f"{field_name} must be greater than zero.")
    return quantity


def generate_reference_number(prefix="STEER-SALE"):
    return f"{prefix}-{uuid4().hex[:8].upper()}"


def parse_items(raw_items, business_id):
    if not isinstance(raw_items, list) or not raw_items:
        raise SaleInputError("At least one sale item is required.")

    items = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise SaleInputError(f"Sale item {index + 1} is invalid.")
        product_id = raw.get("product_id")
        if not product_id:
            raise SaleInputError(f"Product is required for item {index + 1}.")
        product = db.session.execute(
            select(Product).where(Product.id == product_id, Product.business_id == business_id, Product.is_archived.is_(False))
        ).scalar_one_or_none()
        if product is None or not product.is_active:
            raise SaleInputError("One or more products were not found in this business.")
        quantity = _quantity(raw.get("quantity"), "Quantity")
        if product.type == "product" and product.quantity_on_hand < quantity:
            raise SaleInputError(f"Not enough stock for {product.name}.")
        unit_price = _decimal(raw.get("unit_price", product.selling_price), "Unit price")
        unit_cost = _decimal(raw.get("unit_cost", product.purchase_cost), "Unit cost")
        description = raw.get("description") or product.name
        if not isinstance(description, str) or len(description.strip()) == 0:
            raise SaleInputError(f"Description is required for item {index + 1}.")
        line_total = (unit_price * quantity).quantize(Decimal("0.01"))
        items.append(
            {
                "product": product,
                "quantity": quantity,
                "unit_price": unit_price,
                "unit_cost": unit_cost,
                "description": description.strip()[:200],
                "line_total": line_total,
            }
        )
    return items


def _paid_total(sale):
    return sum(
        (payment.amount for payment in sale.payments if payment.direction == "incoming" and payment.status == "received"),
        Decimal("0.00"),
    )


def _refund_total(sale):
    return sum(
        (payment.amount for payment in sale.payments if payment.direction == "refund" and payment.status == "received"),
        Decimal("0.00"),
    )


def _sync_sale_status(sale):
    total_paid = _paid_total(sale)
    total_refunded = _refund_total(sale)
    if sale.status == "cancelled":
        return
    net_paid = total_paid - total_refunded
    if total_refunded >= sale.total_amount and sale.total_amount > 0:
        sale.status = "refunded"
    elif total_paid >= sale.total_amount:
        sale.status = "paid"
    elif net_paid <= 0:
        sale.status = "pending"
    else:
        sale.status = "partially_paid"


def apply_sale_inventory(sale, reverse=False):
    for item in sale.items:
        if item.product is None or item.product.type != "product":
            continue
        delta = Decimal("0") if reverse else -item.quantity
        if reverse:
            delta = item.quantity
        item.product.quantity_on_hand = item.product.quantity_on_hand + delta
        if item.product.quantity_on_hand < 0:
            raise SaleInputError(f"Inventory for {item.product.name} cannot go below zero.")
        db.session.add(
            InventoryMovement(
                business_id=sale.business_id,
                product_id=item.product_id,
                user_id=getattr(sale, "created_by_id", None),
                delta_quantity=delta,
                quantity_after=item.product.quantity_on_hand,
                unit_cost=item.unit_cost,
                reason="sale_refund" if reverse else "sale",
                note=sale.reference_number,
            )
        )


def serialize_sale(sale):
    paid = _paid_total(sale)
    refunded = _refund_total(sale)
    outstanding = max(Decimal("0.00"), sale.total_amount - paid)
    return {
        "id": sale.id,
        "business_id": sale.business_id,
        "customer_id": sale.customer_id,
        "customer_name": sale.customer.full_name if sale.customer else None,
        "customer_phone": sale.customer.phone if sale.customer else None,
        "reference_number": sale.reference_number,
        "status": sale.status,
        "notes": sale.notes,
        "total_amount": format_decimal(sale.total_amount),
        "amount_paid": format_decimal(paid),
        "amount_refunded": format_decimal(refunded),
        "outstanding_balance": format_decimal(outstanding),
        "sale_date": normalized_datetime(sale.sale_date).isoformat(),
        "created_at": normalized_datetime(sale.created_at).isoformat(),
        "updated_at": normalized_datetime(sale.updated_at).isoformat(),
        "items": [serialize_sale_item(item) for item in sale.items],
        "payments": [serialize_payment(payment) for payment in sale.payments],
    }


def serialize_sale_item(item):
    return {
        "id": item.id,
        "sale_id": item.sale_id,
        "product_id": item.product_id,
        "description": item.description,
        "quantity": format_decimal(item.quantity),
        "unit_price": format_decimal(item.unit_price),
        "unit_cost": format_decimal(item.unit_cost),
        "line_total": format_decimal(item.line_total),
    }


def serialize_payment(payment):
    return {
        "id": payment.id,
        "sale_id": payment.sale_id,
        "business_id": payment.business_id,
        "customer_id": payment.customer_id,
        "method": payment.method,
        "direction": payment.direction,
        "amount": format_decimal(payment.amount),
        "payment_date": normalized_datetime(payment.payment_date).isoformat(),
        "reference": payment.reference,
        "status": payment.status,
        "notes": payment.notes,
    }


def format_decimal(value):
    if value is None:
        return None
    return format(value.quantize(Decimal("0.01")), "f")


def create_sale(business_id, payload, current_user=None):
    if not isinstance(payload, dict):
        raise SaleInputError("A JSON request body is required.")
    customer_id = payload.get("customer_id")
    if customer_id is not None:
        customer = db.session.execute(
            select(Customer).where(Customer.id == customer_id, Customer.business_id == business_id)
        ).scalar_one_or_none()
        if customer is None:
            raise SaleInputError("Customer not found in this business.")
    else:
        customer = None

    items = parse_items(payload.get("items"), business_id)
    total_amount = sum((item["line_total"] for item in items), Decimal("0.00")).quantize(Decimal("0.01"))
    reference_number = payload.get("reference_number")
    if reference_number is None:
        reference_number = generate_reference_number()
    if not isinstance(reference_number, str) or not reference_number.strip() or len(reference_number) > 64:
        raise SaleInputError("Reference number must be text under 64 characters.")
    reference_number = reference_number.strip()
    notes = payload.get("notes")
    if notes is not None and (not isinstance(notes, str) or len(notes) > 4000):
        raise SaleInputError("Sale notes must be text under 4000 characters.")
    if db.session.execute(select(Sale.id).where(Sale.business_id == business_id, Sale.reference_number == reference_number)).scalar_one_or_none():
        raise SaleInputError("A sale with that reference already exists.")

    sale = Sale(
        business_id=business_id,
        customer_id=getattr(customer, "id", None),
        reference_number=reference_number,
        status="pending",
        total_amount=total_amount,
        notes=notes.strip() if isinstance(notes, str) and notes.strip() else None,
    )
    db.session.add(sale)
    db.session.flush()

    for item in items:
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=item["product"].id,
            description=item["description"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            unit_cost=item["unit_cost"],
            line_total=item["line_total"],
        )
        db.session.add(sale_item)
        if item["product"].type == "product":
            item["product"].quantity_on_hand = item["product"].quantity_on_hand - item["quantity"]
            if item["product"].quantity_on_hand < 0:
                raise SaleInputError(f"Not enough stock for {item['product'].name}.")
            db.session.add(
                InventoryMovement(
                    business_id=business_id,
                    product_id=item["product"].id,
                    user_id=getattr(current_user, "id", None),
                    delta_quantity=-item["quantity"],
                    quantity_after=item["product"].quantity_on_hand,
                    unit_cost=item["unit_cost"],
                    reason="sale",
                    note=sale.reference_number,
                )
            )
    db.session.flush()

    sale.total_amount = total_amount
    initial_payment = payload.get("initial_payment_amount")
    if initial_payment not in (None, "", 0, "0", "0.00"):
        amount = _decimal(initial_payment, "Payment amount")
        create_payment(
            sale,
            {
                "amount": str(amount),
                "method": payload.get("payment_method", "cash"),
                "reference": payload.get("payment_reference"),
                "notes": payload.get("payment_notes"),
            },
        )
    _sync_sale_status(sale)
    return sale


def create_payment(sale, payload):
    if sale.status in {"cancelled", "refunded"}:
        raise SaleInputError("This sale cannot accept new payments.")
    if not isinstance(payload, dict):
        raise SaleInputError("A JSON request body is required.")
    amount = _decimal(payload.get("amount"), "Payment amount")
    if amount <= 0:
        raise SaleInputError("Payment amount must be greater than zero.")
    payment_method = payload.get("method", "cash")
    if payment_method not in {"cash", "bank_transfer", "pos", "other"}:
        raise SaleInputError("Unsupported payment method.")
    reference = payload.get("reference")
    if reference is None:
        reference = generate_reference_number("STEER-PAYMENT")
    if not isinstance(reference, str) or not reference.strip() or len(reference) > 64:
        raise SaleInputError("Payment reference must be text under 64 characters.")
    reference = reference.strip()
    notes = payload.get("notes")
    if notes is not None and (not isinstance(notes, str) or len(notes) > 2000):
        raise SaleInputError("Payment notes must be text under 2000 characters.")
    if db.session.execute(select(Payment.id).where(Payment.reference == reference)).scalar_one_or_none():
        raise SaleInputError("A payment with that reference already exists.")

    existing_paid = _paid_total(sale)
    remaining = sale.total_amount - existing_paid
    if amount > remaining:
        raise SaleInputError("Payment cannot exceed the remaining sale balance.")

    payment = Payment(
        business_id=sale.business_id,
        sale=sale,
        sale_id=sale.id,
        customer_id=sale.customer_id,
        method=payment_method,
        direction="incoming",
        amount=amount,
        payment_date=parse_payment_date(payload.get("payment_date")),
        reference=reference,
        notes=notes.strip() if isinstance(notes, str) and notes.strip() else None,
    )
    db.session.add(payment)
    _sync_sale_status(sale)
    return payment


def record_refund(sale, payload, current_user=None):
    if sale.status in {"cancelled"}:
        raise SaleInputError("Cancelled sales cannot be refunded.")
    if not isinstance(payload, dict):
        raise SaleInputError("A JSON request body is required.")
    amount = _decimal(payload.get("amount"), "Refund amount")
    if amount <= 0:
        raise SaleInputError("Refund amount must be greater than zero.")
    collected = _paid_total(sale)
    already_refunded = _refund_total(sale)
    if amount > collected - already_refunded:
        raise SaleInputError("Refund cannot exceed the amount collected for this sale.")

    payment_method = payload.get("method", "cash")
    if payment_method not in {"cash", "bank_transfer", "pos", "other"}:
        raise SaleInputError("Unsupported payment method.")
    reference = payload.get("reference")
    if reference is None:
        reference = generate_reference_number("STEER-REFUND")
    if not isinstance(reference, str) or not reference.strip() or len(reference) > 64:
        raise SaleInputError("Refund reference must be text under 64 characters.")
    reference = reference.strip()
    if db.session.execute(select(Payment.id).where(Payment.reference == reference)).scalar_one_or_none():
        raise SaleInputError("A refund with that reference already exists.")
    notes = payload.get("notes")
    if notes is not None and (not isinstance(notes, str) or len(notes) > 2000):
        raise SaleInputError("Refund notes must be text under 2000 characters.")

    refund = Payment(
        business_id=sale.business_id,
        sale=sale,
        sale_id=sale.id,
        customer_id=sale.customer_id,
        method=payment_method,
        direction="refund",
        amount=amount,
        payment_date=parse_payment_date(payload.get("payment_date")),
        reference=reference,
        status="received",
        notes=notes.strip() if isinstance(notes, str) and notes.strip() else None,
    )
    db.session.add(refund)

    total_refunded = already_refunded + amount
    if total_refunded >= sale.total_amount:
        for item in sale.items:
            if item.product is not None and item.product.type == "product":
                item.product.quantity_on_hand = item.product.quantity_on_hand + item.quantity
                db.session.add(
                    InventoryMovement(
                        business_id=sale.business_id,
                        product_id=item.product_id,
                        user_id=getattr(current_user, "id", None),
                        delta_quantity=item.quantity,
                        quantity_after=item.product.quantity_on_hand,
                        unit_cost=item.unit_cost,
                        reason="refund",
                        note=sale.reference_number,
                    )
                )
    _sync_sale_status(sale)
    return refund


def cancel_sale(sale, reason=None, current_user=None):
    if sale.status == "cancelled":
        return sale
    if sale.status == "refunded":
        raise SaleInputError("A fully refunded sale cannot also be cancelled.")
    if _paid_total(sale) - _refund_total(sale) > 0:
        raise SaleInputError("Refund received payments before cancelling this sale.")
    if reason is not None and (not isinstance(reason, str) or len(reason) > 500):
        raise SaleInputError("Cancellation reason must be text under 500 characters.")
    for item in sale.items:
        if item.product is not None and item.product.type == "product":
            item.product.quantity_on_hand = item.product.quantity_on_hand + item.quantity
            db.session.add(
                InventoryMovement(
                    business_id=sale.business_id,
                    product_id=item.product_id,
                    user_id=getattr(current_user, "id", None),
                    delta_quantity=item.quantity,
                    quantity_after=item.product.quantity_on_hand,
                    unit_cost=item.unit_cost,
                    reason="cancelled_sale",
                    note=reason or sale.reference_number,
                )
            )
    sale.status = "cancelled"
    sale.notes = (sale.notes or "") + (f" | {reason.strip()}" if isinstance(reason, str) and reason.strip() else "")
    return sale


def parse_payment_date(value):
    if value is None:
        return datetime.now(timezone.utc)
    if not isinstance(value, str):
        raise SaleInputError("Payment date must be an ISO 8601 date string.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise SaleInputError("Payment date is invalid.") from error
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
