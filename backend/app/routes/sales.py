"""Business sales, payment, refund, and receipt endpoints."""

from datetime import datetime

from flask import Blueprint, g, jsonify, request
from sqlalchemy import or_, select

from app import db
from app.models import Sale, SaleItem
from app.security import require_business_role
from app.services.sale_service import (
    SaleInputError,
    cancel_sale,
    create_payment,
    create_sale,
    record_refund,
    serialize_sale,
)

sales = Blueprint("sales", __name__)


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
    search = request.args.get("q", "").strip()
    page = max(1, int(request.args.get("page", "1")))
    per_page = min(100, max(1, int(request.args.get("per_page", "25"))))
    filters = [Sale.business_id == business_id]
    if search:
        pattern = f"%{search}%"
        filters.append(
            or_(
                Sale.reference_number.ilike(pattern),
                Sale.notes.ilike(pattern),
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
        "sales": [serialize_sale(sale) for sale in rows],
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
        refund = record_refund(sale, _request_payload())
        db.session.commit()
    except SaleInputError as exc:
        db.session.rollback()
        return error_response("validation_error", str(exc), 400)
    except Exception:
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
        cancel_sale(sale, payload.get("reason"))
        db.session.commit()
    except SaleInputError as exc:
        db.session.rollback()
        return error_response("validation_error", str(exc), 400)
    except Exception:
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
