"""Decimal-safe financial aggregation helpers for business reporting."""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select

from app import db
from app.models import Expense, Payment, Sale, SaleItem


def _money(value):
    return Decimal(str(value or "0")).quantize(Decimal("0.01"))


def summarize_business_finances(business_id, start_date=None, end_date=None):
    filters = [Sale.business_id == business_id, Sale.status != "cancelled"]
    if start_date is not None:
        filters.append(Sale.sale_date >= start_date)
    if end_date is not None:
        filters.append(Sale.sale_date <= end_date)

    sales = db.session.scalars(select(Sale).where(*filters).order_by(Sale.sale_date.desc())).all()
    sale_ids = [sale.id for sale in sales]
    total_sales = sum((sale.total_amount for sale in sales), Decimal("0.00"))

    refund_total = _money(
        db.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.business_id == business_id,
                Payment.direction == "refund",
                Payment.status == "received",
                Payment.sale_id.in_(sale_ids if sale_ids else ["__none__"]),
            )
        )
    )
    incoming_total = _money(
        db.session.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.business_id == business_id,
                Payment.direction == "incoming",
                Payment.status == "received",
                Payment.sale_id.in_(sale_ids if sale_ids else ["__none__"]),
            )
        )
    )

    cogs = Decimal("0.00")
    if sale_ids:
        rows = db.session.execute(
            select(SaleItem.product_id, SaleItem.quantity, SaleItem.unit_cost)
            .join(Sale, Sale.id == SaleItem.sale_id)
            .where(Sale.business_id == business_id, Sale.id.in_(sale_ids), Sale.status != "cancelled")
        ).all()
        for product_id, quantity, unit_cost in rows:
            cogs += (Decimal(str(quantity)) * Decimal(str(unit_cost))).quantize(Decimal("0.01"))

    expense_filters = [Expense.business_id == business_id]
    if start_date is not None:
        expense_filters.append(Expense.expense_date >= start_date)
    if end_date is not None:
        expense_filters.append(Expense.expense_date <= end_date)

    expense_total = _money(
        db.session.scalar(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(*expense_filters)
        )
    )

    net_sales = total_sales - refund_total
    gross_profit = net_sales - cogs
    net_profit = gross_profit - expense_total
    outstanding_receivables = sum(
        (max(Decimal("0.00"), sale.total_amount - sum((p.amount for p in sale.payments if p.direction == "incoming" and p.status == "received"), Decimal("0.00"))) for sale in sales),
        Decimal("0.00"),
    )

    return {
        "total_sales": format_money(total_sales),
        "net_sales": format_money(net_sales),
        "cash_collected": format_money(incoming_total),
        "outstanding_receivables": format_money(outstanding_receivables),
        "cogs": format_money(cogs),
        "gross_profit": format_money(gross_profit),
        "operating_expenses": format_money(expense_total),
        "net_profit": format_money(net_profit),
        "sales_count": len(sales),
        "refund_total": format_money(refund_total),
    }


def format_money(value):
    return format(Decimal(str(value or "0")).quantize(Decimal("0.01")), "f")


def period_start(label):
    today = datetime.utcnow().date()
    if label == "today":
        return datetime.combine(today, datetime.min.time())
    if label == "this_week":
        return datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
    if label == "this_month":
        return datetime.combine(today.replace(day=1), datetime.min.time())
    if label == "this_year":
        return datetime.combine(today.replace(month=1, day=1), datetime.min.time())
    return datetime.combine(today - timedelta(days=30), datetime.min.time())
