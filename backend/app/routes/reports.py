"""Business reports and analytics endpoints."""

from datetime import datetime
from io import StringIO

from flask import Blueprint, Response, jsonify, request
from sqlalchemy import case, func, select

from app import db
from app.models import Customer, Expense, Payment, Product, Sale, SaleItem
from app.security import require_business_role
from app.services.financial_service import summarize_business_finances

reports = Blueprint("reports", __name__)


def error_response(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status


def _parse_range(args):
    range_name = (args.get("range") or "this_month").strip().lower()
    if range_name == "today":
        return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0), datetime.utcnow()
    if range_name == "this_week":
        start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        start = start.replace(day=start.day - start.weekday())
        return start, datetime.utcnow()
    if range_name == "this_month":
        start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start, datetime.utcnow()
    start_value = args.get("start_date")
    end_value = args.get("end_date")
    if start_value:
        start = datetime.fromisoformat(start_value)
    else:
        start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if end_value:
        end = datetime.fromisoformat(end_value)
    else:
        end = datetime.utcnow()
    return start, end


@reports.get("/<business_id>/dashboard")
@require_business_role()
def dashboard_summary(business_id):
    start_date, end_date = _parse_range(request.args)
    summary = summarize_business_finances(business_id, start_date, end_date)
    recent = db.session.execute(
        select(Sale)
        .where(Sale.business_id == business_id, Sale.sale_date >= start_date, Sale.sale_date <= end_date)
        .order_by(Sale.sale_date.desc())
        .limit(5)
    ).scalars().all()
    top_products = db.session.execute(
        select(Product.name, func.sum(SaleItem.quantity).label("units_sold"))
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(Product.business_id == business_id, Sale.business_id == business_id, Sale.sale_date >= start_date, Sale.sale_date <= end_date)
        .group_by(Product.name)
        .order_by(func.sum(SaleItem.quantity).desc())
        .limit(5)
    ).all()
    low_stock = db.session.execute(
        select(Product)
        .where(Product.business_id == business_id, Product.type == "product", Product.quantity_on_hand <= Product.reorder_level, Product.reorder_level > 0)
        .order_by(Product.quantity_on_hand.asc())
        .limit(10)
    ).scalars().all()
    summary["recent_transactions"] = [
        {
            "id": sale.reference_number,
            "name": sale.customer.full_name if sale.customer else "Walk-in customer",
            "amount": str(sale.total_amount),
            "status": sale.status,
            "date": sale.sale_date.isoformat(),
        }
        for sale in recent
    ]
    summary["best_selling_products"] = [
        {"name": name, "units_sold": str(units_sold)} for name, units_sold in top_products
    ]
    summary["low_stock_products"] = [
        {"name": product.name, "quantity_on_hand": str(product.quantity_on_hand), "reorder_level": str(product.reorder_level)}
        for product in low_stock
    ]
    summary["range"] = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
    return jsonify(summary)


@reports.get("/<business_id>/reports")
@require_business_role()
def sales_reports(business_id):
    start_date, end_date = _parse_range(request.args)
    report_type = (request.args.get("type") or "sales").lower()
    if report_type == "expenses":
        rows = db.session.execute(
            select(Expense)
            .where(Expense.business_id == business_id, Expense.expense_date >= start_date, Expense.expense_date <= end_date)
            .order_by(Expense.expense_date.desc())
        ).scalars().all()
        payload = {"type": "expenses", "items": [{"id": row.id, "category": row.category, "description": row.description, "amount": str(row.amount), "date": row.expense_date.isoformat()} for row in rows]}
        return jsonify(payload)
    if report_type == "inventory":
        rows = db.session.execute(
            select(Product)
            .where(Product.business_id == business_id, Product.type == "product")
            .order_by(Product.quantity_on_hand.asc())
        ).scalars().all()
        payload = {"type": "inventory", "items": [{"id": row.id, "name": row.name, "quantity_on_hand": str(row.quantity_on_hand), "reorder_level": str(row.reorder_level), "category": row.category} for row in rows]}
        return jsonify(payload)
    if report_type in {"customers", "customer"}:
        rows = db.session.execute(
            select(Customer)
            .where(Customer.business_id == business_id)
            .order_by(Customer.created_at.desc())
        ).scalars().all()
        items = []
        for customer in rows:
            expenses = [sale.total_amount for sale in customer.sales if sale.status != "cancelled"]
            total = sum(expenses, 0)
            paid = sum(
                payment.amount for sale in customer.sales for payment in sale.payments
                if payment.direction == "incoming" and payment.status == "received"
            )
            outstanding = max(0, total - paid)
            items.append({
                "id": customer.id,
                "name": customer.full_name,
                "phone": customer.phone,
                "total_purchases": str(total),
                "outstanding_balance": str(outstanding),
            })
        return jsonify({"type": "customers", "items": items})
    if report_type in {"payments", "payment"}:
        rows = db.session.execute(
            select(Payment)
            .where(Payment.business_id == business_id, Payment.payment_date >= start_date, Payment.payment_date <= end_date)
            .order_by(Payment.payment_date.desc())
        ).scalars().all()
        payload = {"type": "payments", "items": [{"id": row.reference, "customer": row.customer.full_name if row.customer else "Walk-in customer", "amount": str(row.amount), "method": row.method, "direction": row.direction, "status": row.status, "date": row.payment_date.isoformat()} for row in rows]}
        return jsonify(payload)
    if report_type in {"receivables", "receivable"}:
        rows = db.session.execute(
            select(Sale)
            .where(Sale.business_id == business_id, Sale.status != "cancelled", Sale.sale_date >= start_date, Sale.sale_date <= end_date)
            .order_by(Sale.sale_date.desc())
        ).scalars().all()
        items = []
        for row in rows:
            paid = sum((payment.amount for payment in row.payments if payment.direction == "incoming" and payment.status == "received"), 0)
            refunded = sum((payment.amount for payment in row.payments if payment.direction == "refund" and payment.status == "received"), 0)
            outstanding = max(0, row.total_amount - paid + refunded)
            if outstanding > 0:
                items.append({"id": row.reference_number, "customer": row.customer.full_name if row.customer else "Walk-in customer", "amount": str(outstanding), "status": row.status, "date": row.sale_date.isoformat()})
        return jsonify({"type": "receivables", "items": items})
    if report_type in {"products", "product_performance", "product-performance"}:
        rows = db.session.execute(
            select(Product.name, func.sum(SaleItem.quantity).label("units_sold"), func.sum(SaleItem.line_total).label("revenue"))
            .join(SaleItem, SaleItem.product_id == Product.id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Product.business_id == business_id, Sale.business_id == business_id, Sale.status != "cancelled", Sale.sale_date >= start_date, Sale.sale_date <= end_date)
            .group_by(Product.name)
            .order_by(func.sum(SaleItem.quantity).desc())
        ).all()
        payload = {"type": "product_performance", "items": [{"name": row.name, "units_sold": str(row.units_sold), "revenue": str(row.revenue)} for row in rows]}
        return jsonify(payload)
    sales_rows = db.session.execute(
        select(Sale)
        .where(Sale.business_id == business_id, Sale.sale_date >= start_date, Sale.sale_date <= end_date)
        .order_by(Sale.sale_date.desc())
    ).scalars().all()
    payload = {"type": report_type, "items": [{"id": row.reference_number, "customer": row.customer.full_name if row.customer else "Walk-in customer", "amount": str(row.total_amount), "status": row.status, "date": row.sale_date.isoformat()} for row in sales_rows]}
    return jsonify(payload)


@reports.get("/<business_id>/reports/export")
@require_business_role()
def export_report_csv(business_id):
    report_type = (request.args.get("type") or "sales").lower()
    start_date, end_date = _parse_range(request.args)
    output = StringIO()
    if report_type == "expenses":
        rows = db.session.execute(
            select(Expense)
            .where(Expense.business_id == business_id, Expense.expense_date >= start_date, Expense.expense_date <= end_date)
            .order_by(Expense.expense_date.desc())
        ).scalars().all()
        output.write("id,category,description,amount,date\n")
        for row in rows:
            output.write(f"{row.id},{row.category},{row.description},{row.amount},{row.expense_date.isoformat()}\n")
    elif report_type in {"customers", "customer"}:
        rows = db.session.execute(select(Customer).where(Customer.business_id == business_id).order_by(Customer.created_at.desc())).scalars().all()
        output.write("id,name,phone,total_purchases,outstanding_balance\n")
        for row in rows:
            total = sum((sale.total_amount for sale in row.sales if sale.status != "cancelled"), 0)
            paid = sum((payment.amount for sale in row.sales for payment in sale.payments if payment.direction == "incoming" and payment.status == "received"), 0)
            output.write(f"{row.id},{row.full_name},{row.phone},{total},{max(0, total - paid)}\n")
    elif report_type in {"payments", "payment"}:
        rows = db.session.execute(select(Payment).where(Payment.business_id == business_id, Payment.payment_date >= start_date, Payment.payment_date <= end_date).order_by(Payment.payment_date.desc())).scalars().all()
        output.write("reference,customer,amount,method,direction,status,date\n")
        for row in rows:
            customer = row.customer.full_name if row.customer else "Walk-in customer"
            output.write(f"{row.reference},{customer},{row.amount},{row.method},{row.direction},{row.status},{row.payment_date.isoformat()}\n")
    elif report_type in {"receivables", "receivable"}:
        rows = db.session.execute(select(Sale).where(Sale.business_id == business_id, Sale.status != "cancelled", Sale.sale_date >= start_date, Sale.sale_date <= end_date).order_by(Sale.sale_date.desc())).scalars().all()
        output.write("reference,customer,outstanding_balance,date\n")
        for row in rows:
            paid = sum((payment.amount for payment in row.payments if payment.direction == "incoming" and payment.status == "received"), 0)
            refunded = sum((payment.amount for payment in row.payments if payment.direction == "refund" and payment.status == "received"), 0)
            outstanding = max(0, row.total_amount - paid + refunded)
            if outstanding > 0:
                customer = row.customer.full_name if row.customer else "Walk-in customer"
                output.write(f"{row.reference_number},{customer},{outstanding},{row.sale_date.isoformat()}\n")
    else:
        rows = db.session.execute(
            select(Sale)
            .where(Sale.business_id == business_id, Sale.sale_date >= start_date, Sale.sale_date <= end_date)
            .order_by(Sale.sale_date.desc())
        ).scalars().all()
        output.write("reference,customer,amount,status,date\n")
        for row in rows:
            customer = row.customer.full_name if row.customer else "Walk-in customer"
            output.write(f"{row.reference_number},{customer},{row.total_amount},{row.status},{row.sale_date.isoformat()}\n")
    content = output.getvalue()
    return Response(content, mimetype="text/csv", headers={"Content-Disposition": f'attachment; filename="{report_type}_report.csv"'})
