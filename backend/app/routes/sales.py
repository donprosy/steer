"""Business sales, payment, refund, and receipt endpoints."""

import logging
from datetime import datetime

from flask import Blueprint, g, jsonify, request
from sqlalchemy import or_, select

from app import db
from app.models import Customer, Sale
from app.security import require_business_role
from app.services.date_range import parse_date_range
from app.services.sale_service import (
    SaleInputError,
    cancel_sale,
    create_payment,
    create_sale,
    record_refund,
    serialize_sale,
)

sales = Blueprint("sales", __name__)
logger = logging.getLogger(__name__)


def error_response(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status


def _request_payload():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise SaleInputError("A JSON request body is required.")
    return payload


def _find_sale(business_id, sale_id):
    return db.session.execute(
        select(Sale).where(Sale.business_id == business_id, Sale.id == sale_id)
    ).scalar_one_or_none()


@sales.get("/<business_id>/sales")
@require_business_role()
def list_sales(business_id):
    try:
        search = request.args.get("q", "").strip()
        if len(search) > 100:
            raise ValueError
        page = int(request.args.get("page", "1"))
        per_page = int(request.args.get("per_page", "25"))
        if page < 1 or page > 1000000 or per_page < 1 or per_page > 100:
            raise ValueError
        status = request.args.get("status", "all").strip().lower()
        if status not in {"all", "pending", "partially_paid", "paid", "cancelled", "refunded"}:
            raise ValueError
        start_date, end_date = (
            parse_date_range(request.args)
            if request.args.get("range")
            else (None, None)
        )
    except ValueError:
        return error_response("validation_error", "Provide valid search and pagination values.", 400)
    filters = [Sale.business_id == business_id]
    if status != "all":
        filters.append(Sale.status == status)
    if start_date is not None:
        filters.append(Sale.sale_date >= start_date)
    if end_date is not None:
        filters.append(Sale.sale_date <= end_date)
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        filters.append(
            or_(
                Sale.reference_number.ilike(pattern, escape="\\"),
                Sale.notes.ilike(pattern, escape="\\"),
            )
        )
    total = db.session.execute(db.select(db.func.count()).select_from(Sale).where(*filters)).scalar() or 0
    rows = db.session.execute(
        db.select(Sale)
        .where(*filters)
        .order_by(Sale.sale_date.desc(), Sale.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).scalars().all()
    return jsonify({
        "business_id": business_id,
        "sales": [
            {
                "id": sale.id,
                "reference_number": sale.reference_number,
                "customer": sale.customer.full_name if sale.customer else "Walk-in customer",
                "amount": str(sale.total_amount),
                "status": sale.status,
                "date": sale.sale_date.isoformat(),
            }
            for sale in rows
        ],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": max(1, (total + per_page - 1) // per_page) if total else 0,
        },
    })


@sales.post("/<business_id>/sales")
@require_business_role("owner", "manager", "staff")
def create_sale_route(business_id):
    try:
        sale = create_sale(business_id, _request_payload(), g.current_user)
        db.session.commit()
    except SaleInputError as exc:
        db.session.rollback()
        return error_response("validation_error", str(exc), 400)
    except Exception:
        logger.exception("Unexpected error creating sale for business %s", business_id)
        db.session.rollback()
        return error_response("sale_failed", "The sale could not be created.", 500)
    return jsonify({"sale": serialize_sale(sale)}), 201


@sales.get("/<business_id>/sales/<sale_id>")
@require_business_role()
def get_sale(business_id, sale_id):
    sale = _find_sale(business_id, sale_id)
    if sale is None:
        return error_response("sale_not_found", "Sale not found.", 404)
    return jsonify({"sale": serialize_sale(sale)})


@sales.patch("/<business_id>/sales/<sale_id>")
@require_business_role("owner", "manager")
def update_sale(business_id, sale_id):
    sale = _find_sale(business_id, sale_id)
    if sale is None:
        return error_response("sale_not_found", "Sale not found.", 404)
    if sale.status in {"cancelled", "refunded"}:
        return error_response("sale_locked", "Cancelled or refunded sales cannot be edited.", 400)
    payload = _request_payload()
    unknown = set(payload) - {"customer_id", "notes", "sale_date"}
    if unknown:
        return error_response("validation_error", f"Unsupported sale field: {sorted(unknown)[0]}.", 400)
    if not payload:
        return error_response("validation_error", "Provide at least one sale field to update.", 400)
    if "customer_id" in payload:
        customer_id = payload["customer_id"]
        if customer_id in (None, ""):
            sale.customer_id = None
        else:
            customer = db.session.scalar(
                select(Customer).where(
                    Customer.id == customer_id,
                    Customer.business_id == business_id,
                )
            )
            if customer is None:
                return error_response("validation_error", "Customer not found in this business.", 400)
            sale.customer_id = customer.id
    if "notes" in payload:
        notes = payload["notes"]
        if notes is not None and (not isinstance(notes, str) or len(notes) > 4000):
            return error_response("validation_error", "Notes must be text under 4000 characters.", 400)
        sale.notes = notes.strip() if isinstance(notes, str) and notes.strip() else None
    if "sale_date" in payload:
        value = payload["sale_date"]
        if not isinstance(value, str):
            return error_response("validation_error", "Sale date must be an ISO 8601 date string.", 400)
        try:
            sale.sale_date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return error_response("validation_error", "Sale date must be an ISO 8601 date string.", 400)
    db.session.commit()
    return jsonify({"sale": serialize_sale(sale)})


@sales.post("/<business_id>/sales/<sale_id>/payments")
@require_business_role("owner", "manager", "staff")
def add_payment(business_id, sale_id):
    sale = _find_sale(business_id, sale_id)
    if sale is None:
        return error_response("sale_not_found", "Sale not found.", 404)
    try:
        payment = create_payment(sale, _request_payload())
        db.session.commit()
    except SaleInputError as exc:
        db.session.rollback()
        return error_response("validation_error", str(exc), 400)
    except Exception:
        logger.exception("Unexpected error recording payment for sale %s", sale_id)
        db.session.rollback()
        return error_response("payment_failed", "The payment could not be recorded.", 500)
    return jsonify({"payment": {"id": payment.id, "amount": str(payment.amount), "reference": payment.reference, "status": payment.status}})


@sales.post("/<business_id>/sales/<sale_id>/refunds")
@require_business_role("owner", "manager")
def record_refund_route(business_id, sale_id):
    sale = _find_sale(business_id, sale_id)
    if sale is None:
        return error_response("sale_not_found", "Sale not found.", 404)
    try:
        refund = record_refund(sale, _request_payload(), g.current_user)
        db.session.commit()
    except SaleInputError as exc:
        db.session.rollback()
        return error_response("validation_error", str(exc), 400)
    except Exception:
        logger.exception("Unexpected error recording refund for sale %s", sale_id)
        db.session.rollback()
        return error_response("refund_failed", "The refund could not be processed.", 500)
    return jsonify({"refund": {"id": refund.id, "reference": refund.reference, "amount": str(refund.amount), "status": refund.status}})


@sales.post("/<business_id>/sales/<sale_id>/cancel")
@require_business_role("owner", "manager")
def cancel_sale_route(business_id, sale_id):
    sale = _find_sale(business_id, sale_id)
    if sale is None:
        return error_response("sale_not_found", "Sale not found.", 404)
    try:
        payload = _request_payload()
        cancel_sale(sale, payload.get("reason"), g.current_user)
        db.session.commit()
    except SaleInputError as exc:
        db.session.rollback()
        return error_response("validation_error", str(exc), 400)
    except Exception:
        logger.exception("Unexpected error cancelling sale %s", sale_id)
        db.session.rollback()
        return error_response("sale_cancel_failed", "The sale could not be cancelled.", 500)
    return jsonify({"sale": serialize_sale(sale)})


@sales.get("/<business_id>/payments")
@require_business_role()
def list_payments(business_id):
    rows = db.session.execute(
        db.select(Sale)
        .where(Sale.business_id == business_id)
        .order_by(Sale.sale_date.desc())
    ).scalars().all()
    payments = []
    for sale in rows:
        for payment in sale.payments:
            payments.append({
                "id": payment.id,
                "sale_id": payment.sale_id,
                "reference": payment.reference,
                "method": payment.method,
                "direction": payment.direction,
                "amount": str(payment.amount),
                "status": payment.status,
                "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
            })
    return jsonify({"payments": payments})
