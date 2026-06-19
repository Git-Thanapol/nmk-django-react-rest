"""
Dashboard KPI aggregation helpers.
All functions return plain Python dicts / lists (no HttpResponse) for easy unit testing.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    Sum,
)
from django.db.models.functions import TruncDate, TruncMonth

from .models import Invoice, InvoiceItem, PurchaseItem, PurchaseOrder


# ---------------------------------------------------------------------------
# Date range helper
# ---------------------------------------------------------------------------

def resolve_date_range(
    period: str = "this_month",
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[date, date]:
    today = date.today()
    if period == "this_month":
        return today.replace(day=1), today
    if period == "last_month":
        first = today.replace(day=1)
        last_day_prev = first - timedelta(days=1)
        return last_day_prev.replace(day=1), last_day_prev
    if period == "last_30_days":
        return today - timedelta(days=30), today
    if period == "custom" and from_date and to_date:
        return from_date, to_date
    return today.replace(day=1), today


# ---------------------------------------------------------------------------
# Base querysets
# ---------------------------------------------------------------------------

def _invoice_qs(company_id, from_date, to_date):
    qs = Invoice.objects.filter(invoice_date__gte=from_date, invoice_date__lte=to_date)
    if company_id:
        qs = qs.filter(company_id=company_id)
    return qs


def _purchase_qs(company_id, from_date, to_date):
    qs = PurchaseOrder.objects.filter(order_date__gte=from_date, order_date__lte=to_date)
    if company_id:
        qs = qs.filter(company_id=company_id)
    return qs


# ---------------------------------------------------------------------------
# KPI Summary
# ---------------------------------------------------------------------------

def get_kpi_summary(company_id=None, from_date=None, to_date=None) -> dict:
    inv_qs = _invoice_qs(company_id, from_date, to_date)
    po_qs = _purchase_qs(company_id, from_date, to_date)

    total_sales = inv_qs.aggregate(t=Sum("grand_total"))["t"] or Decimal(0)
    total_purchases = po_qs.aggregate(t=Sum("total_amount"))["t"] or Decimal(0)

    # Gross profit: revenue from line items - COGS where purchase_item linked
    item_qs = InvoiceItem.objects.filter(invoice__in=inv_qs, purchase_item__isnull=False)
    item_revenue = item_qs.aggregate(t=Sum("total_price"))["t"] or Decimal(0)
    item_cost = item_qs.aggregate(
        t=Sum(
            ExpressionWrapper(
                F("quantity") * F("purchase_item__unit_cost"),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
    )["t"] or Decimal(0)
    gross_profit = item_revenue - item_cost
    profit_pct = (
        round(float(gross_profit) / float(item_revenue) * 100, 1)
        if item_revenue
        else 0.0
    )

    # Low-stock count: PurchaseItem with 0 < remaining < threshold
    low_stock_qs = PurchaseItem.objects.filter(
        remaining_quantity__gt=0, remaining_quantity__lt=5
    )
    if company_id:
        low_stock_qs = low_stock_qs.filter(purchase_order__company_id=company_id)
    low_stock_count = low_stock_qs.count()

    return {
        "total_sales": float(total_sales),
        "total_purchases": float(total_purchases),
        "gross_profit": float(gross_profit),
        "profit_pct": profit_pct,
        "low_stock_count": low_stock_count,
    }


# ---------------------------------------------------------------------------
# Sales trend (last N days, one point per day)
# ---------------------------------------------------------------------------

def get_sales_trend(company_id=None, days: int = 30) -> list[dict]:
    today = date.today()
    from_date = today - timedelta(days=days - 1)

    qs = (
        Invoice.objects.filter(invoice_date__gte=from_date, invoice_date__lte=today)
        .annotate(day=TruncDate("invoice_date"))
    )
    if company_id:
        qs = qs.filter(company_id=company_id)

    daily = {
        row["day"]: float(row["total"])
        for row in qs.values("day").annotate(total=Sum("grand_total")).order_by("day")
    }

    # Fill gaps with 0
    result = []
    for i in range(days):
        d = from_date + timedelta(days=i)
        result.append({"date": d.isoformat(), "total": daily.get(d, 0.0)})
    return result


# ---------------------------------------------------------------------------
# Top N SKUs by quantity sold
# ---------------------------------------------------------------------------

def get_top_skus(company_id=None, from_date=None, to_date=None, limit: int = 10) -> list[dict]:
    inv_qs = _invoice_qs(company_id, from_date, to_date)
    rows = (
        InvoiceItem.objects.filter(invoice__in=inv_qs)
        .values("product__sku", "product__name")
        .annotate(total_qty=Sum("quantity"))
        .order_by("-total_qty")[:limit]
    )
    return [
        {
            "sku": r["product__sku"] or "N/A",
            "name": r["product__name"] or "Unknown",
            "qty": r["total_qty"],
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Purchase vs Sales (monthly, last N months)
# ---------------------------------------------------------------------------

def get_purchase_vs_sales(company_id=None, months: int = 6) -> list[dict]:
    today = date.today()
    from_date = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    # Go back (months-1) more months
    for _ in range(months - 1):
        from_date = (from_date - timedelta(days=1)).replace(day=1)

    inv_qs = Invoice.objects.filter(invoice_date__gte=from_date)
    po_qs = PurchaseOrder.objects.filter(order_date__gte=from_date)
    if company_id:
        inv_qs = inv_qs.filter(company_id=company_id)
        po_qs = po_qs.filter(company_id=company_id)

    sales_by_month = {
        row["month"]: float(row["total"])
        for row in inv_qs.annotate(month=TruncMonth("invoice_date"))
        .values("month")
        .annotate(total=Sum("grand_total"))
        .order_by("month")
    }
    purchases_by_month = {
        row["month"]: float(row["total"])
        for row in po_qs.annotate(month=TruncMonth("order_date"))
        .values("month")
        .annotate(total=Sum("total_amount"))
        .order_by("month")
    }

    result = []
    cur = from_date
    for _ in range(months):
        label = cur.strftime("%b %Y")
        result.append({
            "month": label,
            "sales": sales_by_month.get(cur, 0.0),
            "purchases": purchases_by_month.get(cur, 0.0),
        })
        # advance to next month
        nxt = (cur.replace(day=28) + timedelta(days=4))
        cur = nxt.replace(day=1)

    return result


# ---------------------------------------------------------------------------
# Stock alerts (low remaining quantity)
# ---------------------------------------------------------------------------

def get_stock_alerts(company_id=None, threshold: int = 5) -> list[dict]:
    qs = PurchaseItem.objects.filter(
        remaining_quantity__gt=0, remaining_quantity__lt=threshold
    ).select_related("product", "purchase_order__company")
    if company_id:
        qs = qs.filter(purchase_order__company_id=company_id)

    return [
        {
            "sku": item.product.sku if item.product else "N/A",
            "name": item.product.name if item.product else "Unknown",
            "remaining": item.remaining_quantity,
            "po_number": item.purchase_order.po_number,
            "company": str(item.purchase_order.company),
        }
        for item in qs.order_by("remaining_quantity")[:50]
    ]
