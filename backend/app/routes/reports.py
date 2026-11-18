"""Business reports and analytics endpoints."""

import csv
from datetime import datetime, timedelta
from decimal import Decimal
from io import StringIO

from flask import Blueprint, Response, jsonify, request
from sqlalchemy import func, select

from app import db
from app.models import Customer, Expense, Payment, Product, Sale, SaleItem
from app.security import require_business_role
from app.services.date_range import parse_date_range
from app.services.financial_service import format_money, summarize_business_finances

reports = Blueprint("reports", __name__)


def error_response(code, message, status):
    return jsonify({"error": {"code": code, "message": message}}), status


def _parse_range(args):
    return parse_date_range(args)


def _financial_trend(business_id, start_date, end_date):
    first_day = start_date.date()
    last_day = end_date.date()
    day_count = (last_day - first_day).days + 1
    bucket_days = max(1, (day_count + 59) // 60)
    bucket_count = (day_count + bucket_days - 1) // bucket_days
    buckets = [
        {"date": (first_day + timedelta(days=index * bucket_days)).isoformat(),
         "sales": Decimal("0.00"), "expenses": Decimal("0.00")}
        for index in range(bucket_count)
    ]

    sales_by_day = db.session.execute(
        select(func.date(Sale.sale_date), func.sum(Sale.total_amount))
        .where(
            Sale.business_id == business_id,
            Sale.status != "cancelled",
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date,
        )
        .group_by(func.date(Sale.sale_date))
    ).all()
    refunds_by_day = db.session.execute(
        select(func.date(Sale.sale_date), func.sum(Payment.amount))
        .join(Sale, Sale.id == Payment.sale_id)
        .where(
            Sale.business_id == business_id,
            Sale.status != "cancelled",
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date,
            Payment.business_id == business_id,
            Payment.direction == "refund",
            Payment.status == "received",
        )
        .group_by(func.date(Sale.sale_date))
    ).all()
    expenses_by_day = db.session.execute(
        select(func.date(Expense.expense_date), func.sum(Expense.amount))
        .where(
            Expense.business_id == business_id,
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
        )
        .group_by(func.date(Expense.expense_date))
    ).all()

    def add_values(rows, field, multiplier=1):
        for day_value, amount in rows:
            day = datetime.fromisoformat(str(day_value)).date()
            index = min((day - first_day).days // bucket_days, bucket_count - 1)
            buckets[index][field] += Decimal(str(amount or "0")) * multiplier

    add_values(sales_by_day, "sales")
    add_values(refunds_by_day, "sales", -1)
    add_values(expenses_by_day, "expenses")
    return [
        {
            "date": item["date"],
            "sales": format_money(item["sales"]),
            "expenses": format_money(item["expenses"]),
        }
        for item in buckets
    ]


@reports.get("/<business_id>/dashboard")
@require_business_role()
def dashboard_summary(business_id):
    try:
        start_date, end_date = _parse_range(request.args)
    except ValueError as error:
        return error_response("validation_error", str(error), 400)
    summary = summarize_business_finances(business_id, start_date, end_date)
    summary["business_id"] = business_id
    summary["customer_count"] = db.session.scalar(
        select(func.count()).select_from(Customer).where(Customer.business_id == business_id)
    ) or 0
    summary["products_in_stock"] = db.session.scalar(
        select(func.count()).select_from(Product).where(
            Product.business_id == business_id,
            Product.type == "product",
            Product.is_active.is_(True),
            Product.is_archived.is_(False),
            Product.quantity_on_hand > 0,
        )
    ) or 0
    inventory_units = db.session.scalar(
        select(func.coalesce(func.sum(Product.quantity_on_hand), 0)).where(
            Product.business_id == business_id,
            Product.type == "product",
            Product.is_active.is_(True),
            Product.is_archived.is_(False),
        )
    )
    summary["inventory_units"] = format(Decimal(str(inventory_units or "0")).normalize(), "f")
    summary["out_of_stock_count"] = db.session.scalar(
        select(func.count()).select_from(Product).where(
            Product.business_id == business_id,
            Product.type == "product",
            Product.is_active.is_(True),
            Product.is_archived.is_(False),
            Product.quantity_on_hand <= 0,
        )
    ) or 0
    summary["trend"] = _financial_trend(business_id, start_date, end_date)
    recent = db.session.execute(
        select(Sale)
        .where(Sale.business_id == business_id, Sale.sale_date >= start_date, Sale.sale_date <= end_date)
        .order_by(Sale.sale_date.desc())
        .limit(5)
    ).scalars().all()
    recent_expenses = db.session.execute(
        select(Expense)
        .where(
            Expense.business_id == business_id,
            Expense.expense_date >= start_date,
            Expense.expense_date <= end_date,
        )
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .limit(5)
    ).scalars().all()
    top_products = db.session.execute(
        select(Product.name, func.sum(SaleItem.quantity).label("units_sold"))
        .join(SaleItem, SaleItem.product_id == Product.id)
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(
            Product.business_id == business_id,
            Sale.business_id == business_id,
            Sale.status.notin_(("cancelled", "refunded")),
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date,
        )
        .group_by(Product.name)
        .order_by(func.sum(SaleItem.quantity).desc())
        .limit(5)
    ).all()
    low_stock = db.session.execute(
        select(Product)
        .where(
            Product.business_id == business_id,
            Product.type == "product",
            Product.is_active.is_(True),
            Product.is_archived.is_(False),
            Product.quantity_on_hand <= Product.reorder_level,
        )
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
    summary["recent_expenses"] = [
        {
            "id": expense.id,
            "description": expense.description,
            "category": expense.category,
            "amount": str(expense.amount),
            "date": expense.expense_date.isoformat(),
        }
        for expense in recent_expenses
    ]
    summary["recent_activity"] = sorted(
        [
            {
                "id": f"sale-{sale.reference_number}",
                "type": "sale",
                "title": f"Sale {sale.reference_number}",
                "detail": sale.customer.full_name if sale.customer else "Walk-in customer",
                "amount": str(sale.total_amount),
                "date": sale.sale_date.isoformat(),
            }
            for sale in recent
        ] + [
            {
                "id": f"expense-{expense.id}",
                "type": "expense",
                "title": expense.description,
                "detail": expense.category,
                "amount": str(expense.amount),
                "date": expense.expense_date.isoformat(),
            }
            for expense in recent_expenses
        ],
        key=lambda item: item["date"],
        reverse=True,
    )[:8]
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
    try:
        start_date, end_date = _parse_range(request.args)
    except ValueError as error:
        return error_response("validation_error", str(error), 400)
    report_type = (request.args.get("type") or "sales").lower()
    supported_types = {
        "sales", "expenses", "inventory", "customers", "customer", "payments",
        "payment", "receivables", "receivable", "products", "product_performance",
        "product-performance", "profit_loss",
    }
    if report_type not in supported_types:
        return error_response("validation_error", "Unsupported report type.", 400)
    if report_type == "expenses":
        rows = db.session.execute(
            select(Expense)
            .where(Expense.business_id == business_id, Expense.expense_date >= start_date, Expense.expense_date <= end_date)
            .order_by(Expense.expense_date.desc())
        ).scalars().all()
        payload = {
            "type": "expenses",
            "items": [
                {
                    "id": row.id,
                    "category": row.category,
                    "description": row.description,
                    "amount": str(row.amount),
                    "payment_method": row.payment_method,
                    "notes": row.notes,
                    "date": row.expense_date.isoformat(),
                }
                for row in rows
            ],
        }
        return jsonify(payload)
    if report_type == "profit_loss":
        summary = summarize_business_finances(business_id, start_date, end_date)
        labels = {
            "total_sales": "Gross sales",
            "refund_total": "Refunds",
            "net_sales": "Net sales",
            "cogs": "Cost of goods sold",
            "gross_profit": "Gross profit",
            "operating_expenses": "Operating expenses",
            "net_profit": "Net profit",
            "cash_collected": "Net cash collected",
            "outstanding_receivables": "Outstanding receivables",
        }
        return jsonify({
            "business_id": business_id,
            "type": "profit_loss",
            "items": [
                {"metric": label, "amount": summary[key]}
                for key, label in labels.items()
            ],
        })
    if report_type == "inventory":
        rows = db.session.execute(
            select(Product)
            .where(
                Product.business_id == business_id,
                Product.type == "product",
                Product.is_archived.is_(False),
            )
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
            .where(            Sale.business_id == business_id, Sale.status.notin_(("cancelled", "refunded")), Sale.sale_date >= start_date, Sale.sale_date <= end_date)
            .order_by(Sale.sale_date.desc())
        ).scalars().all()
        items = []
        for row in rows:
            paid = sum((payment.amount for payment in row.payments if payment.direction == "incoming" and payment.status == "received"), 0)
            outstanding = max(0, row.total_amount - paid)
            if outstanding > 0:
                items.append({"id": row.reference_number, "customer": row.customer.full_name if row.customer else "Walk-in customer", "amount": str(outstanding), "status": row.status, "date": row.sale_date.isoformat()})
        return jsonify({"type": "receivables", "items": items})
    if report_type in {"products", "product_performance", "product-performance"}:
        rows = db.session.execute(
            select(Product.name, func.sum(SaleItem.quantity).label("units_sold"), func.sum(SaleItem.line_total).label("revenue"))
            .join(SaleItem, SaleItem.product_id == Product.id)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Product.business_id == business_id, Sale.business_id == business_id, Sale.status.notin_(("cancelled", "refunded")), Sale.sale_date >= start_date, Sale.sale_date <= end_date)
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
    payload = {
        "type": report_type,
        "items": [
            {
                "id": row.reference_number,
                "sale_id": row.id,
                "customer": row.customer.full_name if row.customer else "Walk-in customer",
                "amount": str(row.total_amount),
                "status": row.status,
                "date": row.sale_date.isoformat(),
            }
            for row in sales_rows
        ],
    }
    return jsonify(payload)


@reports.get("/<business_id>/reports/export")
@require_business_role()
def export_report_csv(business_id):
    report_type = (request.args.get("type") or "sales").lower()
    report_response = sales_reports(business_id=business_id)
    if isinstance(report_response, tuple):
        return report_response
    data = report_response.get_json()
    fields = {
        "sales": ("id", "customer", "amount", "status", "date"),
        "expenses": ("id", "category", "description", "amount", "date"),
        "inventory": ("id", "name", "quantity_on_hand", "reorder_level", "category"),
        "customers": ("id", "name", "phone", "total_purchases", "outstanding_balance"),
        "customer": ("id", "name", "phone", "total_purchases", "outstanding_balance"),
        "payments": ("id", "customer", "amount", "method", "direction", "status", "date"),
        "payment": ("id", "customer", "amount", "method", "direction", "status", "date"),
        "receivables": ("id", "customer", "amount", "status", "date"),
        "receivable": ("id", "customer", "amount", "status", "date"),
        "products": ("name", "units_sold", "revenue"),
        "product_performance": ("name", "units_sold", "revenue"),
        "product-performance": ("name", "units_sold", "revenue"),
        "profit_loss": ("metric", "amount"),
    }[report_type]
    output = StringIO()
    writer = csv.writer(output, lineterminator="\r\n")
    writer.writerow(fields)
    for item in data["items"]:
        values = [item.get(field, "") for field in fields]
        writer.writerow([_safe_csv_value(value) for value in values])
    content = output.getvalue()
    return Response(content, mimetype="text/csv", headers={"Content-Disposition": f'attachment; filename="{report_type}_report.csv"'})


def _safe_csv_value(value):
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text
