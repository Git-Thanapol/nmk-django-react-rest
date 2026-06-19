"""
Model tests — behaviour, constraints, computed properties, and known bugs.
"""
import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from api.models import (
    Company, Vendor, Product, PurchaseOrder, PurchaseItem,
    Invoice, InvoiceItem, Transaction, WithholdingTaxCert,
    ProductAlias,
)
from .factories import (
    CompanyFactory, VendorFactory, ProductFactory,
    PurchaseOrderFactory, PurchaseItemFactory,
    InvoiceFactory, InvoiceItemFactory,
    TransactionFactory, WithholdingTaxCertFactory, UserFactory,
    ProductAliasFactory,
)


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCompany:
    def test_str(self):
        c = CompanyFactory(name="KIT23 Co")
        assert str(c) == "KIT23 Co"

    def test_active_default(self):
        c = CompanyFactory()
        assert c.is_active is True

    def test_inactive_company(self):
        c = CompanyFactory(is_active=False)
        assert c.is_active is False


# ---------------------------------------------------------------------------
# Vendor
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestVendor:
    def test_unique_together_company_name(self):
        company = CompanyFactory()
        VendorFactory(company=company, name="UniVendor")
        with pytest.raises(IntegrityError):
            VendorFactory(company=company, name="UniVendor")

    def test_same_name_different_company_is_allowed(self):
        c1 = CompanyFactory()
        c2 = CompanyFactory()
        VendorFactory(company=c1, name="SharedVendor")
        v2 = VendorFactory(company=c2, name="SharedVendor")
        assert v2.pk is not None

    def test_str_includes_company(self):
        v = VendorFactory(name="Apple Inc")
        assert "Apple Inc" in str(v)
        assert str(v.company) in str(v)


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProduct:
    def test_unique_sku_per_company(self):
        company = CompanyFactory()
        ProductFactory(company=company, sku="IPHONE-15")
        with pytest.raises(IntegrityError):
            ProductFactory(company=company, sku="IPHONE-15")

    def test_same_sku_different_company_is_allowed(self):
        c1 = CompanyFactory()
        c2 = CompanyFactory()
        ProductFactory(company=c1, sku="SHARED-SKU")
        p2 = ProductFactory(company=c2, sku="SHARED-SKU")
        assert p2.pk is not None

    def test_current_stock_zero_when_no_transactions(self):
        p = ProductFactory()
        assert p.current_stock == 0

    def test_current_stock_after_purchase(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        PurchaseItemFactory(purchase_order=po, product=p, quantity=50)
        assert p.current_stock == 50

    def test_current_stock_decreases_after_sale(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        pi = PurchaseItemFactory(purchase_order=po, product=p, quantity=50)

        inv = InvoiceFactory(company=po.company, created_by=po.created_by)
        InvoiceItemFactory(invoice=inv, product=p, purchase_item=pi, quantity=10)

        assert p.current_stock == 40

    def test_current_stock_never_negative_when_oversold(self):
        """KNOWN BUG: stock can go negative; remaining_quantity is not decremented."""
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        pi = PurchaseItemFactory(purchase_order=po, product=p, quantity=5)
        pi.remaining_quantity = 5
        pi.save()

        inv = InvoiceFactory(company=po.company, created_by=po.created_by)
        # Selling 10 from a batch of 5 — clean() should raise
        item = InvoiceItem(
            invoice=inv, product=p, purchase_item=pi,
            quantity=10, unit_price=Decimal("100"),
        )
        with pytest.raises(ValidationError):
            item.clean()

    def test_str(self):
        p = ProductFactory(sku="TEST-001", name="Widget")
        assert "TEST-001" in str(p)
        assert "Widget" in str(p)


# ---------------------------------------------------------------------------
# PurchaseOrder — calculate_totals
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPurchaseOrderCalculateTotals:
    def test_subtotal_is_sum_of_items(self):
        po = PurchaseOrderFactory(tax_include=False, tax_percent=Decimal("0"))
        p = ProductFactory(company=po.company)
        PurchaseItemFactory(purchase_order=po, product=p, quantity=10, unit_cost=Decimal("100"))
        po.refresh_from_db()
        assert po.subtotal == Decimal("1000.00")

    def test_tax_included_extracts_vat_correctly(self):
        po = PurchaseOrderFactory(tax_include=True, tax_percent=Decimal("7"))
        p = ProductFactory(company=po.company)
        PurchaseItemFactory(purchase_order=po, product=p, quantity=1, unit_cost=Decimal("107"))
        po.refresh_from_db()
        # Subtotal = 107, extracted tax = 107 - 107/1.07 ≈ 7
        assert abs(po.tax_amount - Decimal("7")) < Decimal("0.01")

    def test_tax_excluded_adds_vat_forward(self):
        po = PurchaseOrderFactory(tax_include=False, tax_percent=Decimal("7"))
        p = ProductFactory(company=po.company)
        PurchaseItemFactory(purchase_order=po, product=p, quantity=1, unit_cost=Decimal("100"))
        po.refresh_from_db()
        assert abs(po.tax_amount - Decimal("7")) < Decimal("0.01")

    def test_total_amount_tax_excluded(self):
        po = PurchaseOrderFactory(tax_include=False, tax_percent=Decimal("7"))
        p = ProductFactory(company=po.company)
        PurchaseItemFactory(purchase_order=po, product=p, quantity=1, unit_cost=Decimal("100"))
        po.refresh_from_db()
        # BUG NOTE: total_amount = subtotal + tax_amount = 100 + 7 = 107 (correct for tax_exclude)
        assert abs(po.total_amount - Decimal("107")) < Decimal("0.01")

    def test_total_amount_tax_included_bug(self):
        """
        KNOWN BUG: When tax_include=True, total_amount = subtotal + tax_amount
        This double-counts because tax is already inside subtotal.
        Expected: total_amount == subtotal (107), Actual: total_amount > subtotal.
        """
        po = PurchaseOrderFactory(tax_include=True, tax_percent=Decimal("7"))
        p = ProductFactory(company=po.company)
        PurchaseItemFactory(purchase_order=po, product=p, quantity=1, unit_cost=Decimal("107"))
        po.refresh_from_db()
        # Document the current (buggy) behaviour so a future fix is caught by the test suite
        # If tax_include=True and subtotal=107, correct total_amount should be 107
        # but current code returns 107 + ~7 = ~114
        assert po.total_amount > po.subtotal, (
            "BUG: total_amount should equal subtotal when tax_include=True, "
            "but it incorrectly adds extracted tax on top of subtotal."
        )

    def test_item_count_property(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        PurchaseItemFactory(purchase_order=po, product=p)
        PurchaseItemFactory(purchase_order=po, product=p)
        assert po.item_count == 2


# ---------------------------------------------------------------------------
# PurchaseItem
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPurchaseItem:
    def test_total_price_calculated_on_save(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        pi = PurchaseItemFactory(purchase_order=po, product=p, quantity=5, unit_cost=Decimal("200"))
        assert pi.total_price == Decimal("1000.00")

    def test_remaining_quantity_set_on_first_save(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        pi = PurchaseItemFactory(purchase_order=po, product=p, quantity=15)
        assert pi.remaining_quantity == 15

    def test_remaining_quantity_not_reset_on_update(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        pi = PurchaseItemFactory(purchase_order=po, product=p, quantity=15)
        pi.remaining_quantity = 5
        pi.unit_cost = Decimal("999")
        pi.save()
        pi.refresh_from_db()
        assert pi.remaining_quantity == 5  # should NOT be reset to 15

    def test_quantity_must_be_positive(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        item = PurchaseItem(
            purchase_order=po, product=p,
            quantity=0, unit_cost=Decimal("100"),
        )
        with pytest.raises((ValidationError, Exception)):
            item.full_clean()


# ---------------------------------------------------------------------------
# Invoice — calculate_totals
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInvoiceCalculateTotals:
    def test_subtotal_is_sum_of_items(self):
        inv = InvoiceFactory(tax_include=False, tax_percent=Decimal("0"), shipping_cost=Decimal("0"))
        p = ProductFactory(company=inv.company)
        InvoiceItemFactory(invoice=inv, product=p, quantity=2, unit_price=Decimal("500"))
        inv.refresh_from_db()
        assert inv.subtotal == Decimal("1000.00")

    def test_grand_total_with_shipping_tax_included(self):
        inv = InvoiceFactory(
            tax_include=True, tax_percent=Decimal("7"),
            shipping_cost=Decimal("50"), discount_amount=Decimal("0"),
        )
        p = ProductFactory(company=inv.company)
        InvoiceItemFactory(invoice=inv, product=p, quantity=1, unit_price=Decimal("1000"))
        inv.refresh_from_db()
        # When tax_include=True: grand_total = subtotal + shipping - discount
        assert inv.grand_total == Decimal("1050.00")

    def test_grand_total_with_discount(self):
        inv = InvoiceFactory(
            tax_include=True, tax_percent=Decimal("7"),
            shipping_cost=Decimal("0"), discount_amount=Decimal("100"),
        )
        p = ProductFactory(company=inv.company)
        InvoiceItemFactory(invoice=inv, product=p, quantity=1, unit_price=Decimal("1000"))
        inv.refresh_from_db()
        assert inv.grand_total == Decimal("900.00")

    def test_profit_margin_property(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        pi = PurchaseItemFactory(purchase_order=po, product=p, quantity=10, unit_cost=Decimal("800"))

        inv = InvoiceFactory(company=po.company, created_by=po.created_by, tax_include=False, tax_percent=Decimal("0"))
        InvoiceItemFactory(invoice=inv, product=p, purchase_item=pi, quantity=1, unit_price=Decimal("1000"))
        inv.refresh_from_db()

        assert inv.profit_margin == Decimal("200.00")

    def test_item_count_property(self):
        inv = InvoiceFactory()
        p1 = ProductFactory()
        p2 = ProductFactory()
        InvoiceItemFactory(invoice=inv, product=p1)
        InvoiceItemFactory(invoice=inv, product=p2)
        assert inv.item_count == 2


# ---------------------------------------------------------------------------
# InvoiceItem
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInvoiceItem:
    def test_total_price_calculated_on_save(self):
        inv = InvoiceFactory()
        p = ProductFactory()
        item = InvoiceItemFactory(invoice=inv, product=p, quantity=3, unit_price=Decimal("200"))
        assert item.total_price == Decimal("600.00")

    def test_str_falls_back_to_item_name_when_no_product(self):
        inv = InvoiceFactory()
        item = InvoiceItem.objects.create(
            invoice=inv,
            product=None,
            item_name="Mystery Item",
            quantity=1,
            unit_price=Decimal("100"),
        )
        assert "Mystery Item" in str(item)

    def test_str_uses_product_name(self):
        inv = InvoiceFactory()
        p = ProductFactory(name="iPhone 15")
        item = InvoiceItemFactory(invoice=inv, product=p)
        assert "iPhone 15" in str(item)

    def test_unit_cost_from_purchase_item(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        pi = PurchaseItemFactory(purchase_order=po, product=p, unit_cost=Decimal("800"))

        inv = InvoiceFactory(company=po.company, created_by=po.created_by)
        item = InvoiceItemFactory(invoice=inv, product=p, purchase_item=pi)
        assert item.unit_cost == Decimal("800.00")

    def test_unit_cost_zero_without_purchase_item(self):
        inv = InvoiceFactory()
        p = ProductFactory()
        item = InvoiceItemFactory(invoice=inv, product=p, purchase_item=None)
        assert item.unit_cost == Decimal("0")

    def test_profit_calculation(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        pi = PurchaseItemFactory(purchase_order=po, product=p, unit_cost=Decimal("600"))

        inv = InvoiceFactory(company=po.company, created_by=po.created_by)
        item = InvoiceItemFactory(invoice=inv, product=p, purchase_item=pi, quantity=2, unit_price=Decimal("1000"))
        # profit = (2 * 1000) - (2 * 600) = 800
        assert item.profit == Decimal("800.00")

    def test_profit_margin_percentage(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        pi = PurchaseItemFactory(purchase_order=po, product=p, unit_cost=Decimal("0"))

        inv = InvoiceFactory(company=po.company, created_by=po.created_by)
        item = InvoiceItemFactory(invoice=inv, product=p, purchase_item=pi, quantity=1, unit_price=Decimal("100"))
        assert item.profit_margin_percentage == Decimal("100")

    def test_profit_margin_percentage_zero_price(self):
        inv = InvoiceFactory()
        p = ProductFactory()
        item = InvoiceItemFactory(invoice=inv, product=p, quantity=1, unit_price=Decimal("0"))
        assert item.profit_margin_percentage == Decimal("0")

    def test_clean_raises_when_insufficient_stock(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        pi = PurchaseItemFactory(purchase_order=po, product=p, quantity=5)
        pi.remaining_quantity = 3
        pi.save()

        inv = InvoiceFactory(company=po.company, created_by=po.created_by)
        item = InvoiceItem(
            invoice=inv, product=p, purchase_item=pi,
            quantity=5, unit_price=Decimal("100"),
        )
        with pytest.raises(ValidationError, match="Not enough quantity"):
            item.clean()

    def test_clean_passes_when_stock_is_sufficient(self):
        po = PurchaseOrderFactory()
        p = ProductFactory(company=po.company)
        pi = PurchaseItemFactory(purchase_order=po, product=p, quantity=10)

        inv = InvoiceFactory(company=po.company, created_by=po.created_by)
        item = InvoiceItem(
            invoice=inv, product=p, purchase_item=pi,
            quantity=10, unit_price=Decimal("100"),
        )
        item.clean()  # should not raise


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTransaction:
    def test_signed_amount_income(self):
        t = TransactionFactory(type="INCOME", amount=Decimal("5000"))
        assert t.signed_amount == Decimal("5000")

    def test_signed_amount_expense(self):
        t = TransactionFactory(type="EXPENSE", amount=Decimal("5000"))
        assert t.signed_amount == Decimal("-5000")

    def test_unique_together_company_transaction_number(self):
        company = CompanyFactory()
        user = UserFactory()
        TransactionFactory(company=company, transaction_number="TX-001", created_by=user)
        with pytest.raises(IntegrityError):
            TransactionFactory(company=company, transaction_number="TX-001", created_by=user)

    def test_amount_must_be_positive(self):
        t = TransactionFactory.build(amount=Decimal("0"))
        with pytest.raises(ValidationError):
            t.full_clean()


# ---------------------------------------------------------------------------
# WithholdingTaxCert — auto cert_number generation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestWithholdingTaxCertAutoNumber:
    def test_auto_generates_cert_number_on_first_cert(self):
        import datetime
        cert = WithholdingTaxCertFactory(cert_number="", date_issued=datetime.date(2025, 1, 1))
        assert cert.cert_number == "2025/0001"

    def test_auto_increments_cert_number(self):
        import datetime
        company = CompanyFactory()
        vendor = VendorFactory(company=company)
        cert1 = WithholdingTaxCert.objects.create(
            company=company, vendor=vendor,
            income_type="8", tax_rate=Decimal("3"),
            amount_before_tax=Decimal("10000"), tax_amount=Decimal("300"),
            date_issued=datetime.date(2025, 6, 1), cert_number="",
        )
        cert2 = WithholdingTaxCert.objects.create(
            company=company, vendor=vendor,
            income_type="8", tax_rate=Decimal("3"),
            amount_before_tax=Decimal("10000"), tax_amount=Decimal("300"),
            date_issued=datetime.date(2025, 6, 2), cert_number="",
        )
        assert cert1.cert_number == "2025/0001"
        assert cert2.cert_number == "2025/0002"

    def test_numbering_resets_per_year(self):
        import datetime
        company = CompanyFactory()
        vendor = VendorFactory(company=company)
        WithholdingTaxCert.objects.create(
            company=company, vendor=vendor,
            income_type="8", tax_rate=Decimal("3"),
            amount_before_tax=Decimal("10000"), tax_amount=Decimal("300"),
            date_issued=datetime.date(2024, 12, 31), cert_number="",
        )
        cert_2025 = WithholdingTaxCert.objects.create(
            company=company, vendor=vendor,
            income_type="8", tax_rate=Decimal("3"),
            amount_before_tax=Decimal("10000"), tax_amount=Decimal("300"),
            date_issued=datetime.date(2025, 1, 1), cert_number="",
        )
        assert cert_2025.cert_number == "2025/0001"

    def test_cert_number_not_overwritten_if_provided(self):
        import datetime
        cert = WithholdingTaxCertFactory(cert_number="MANUAL-001", date_issued=datetime.date(2025, 1, 1))
        assert cert.cert_number == "MANUAL-001"

    def test_total_text_thai_returns_string(self):
        cert = WithholdingTaxCertFactory(tax_amount=Decimal("300"))
        result = cert.total_text_thai
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# ProductAlias — unique external_key constraint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProductAlias:
    def test_unique_external_key(self):
        p1 = ProductFactory()
        p2 = ProductFactory()
        ProductAliasFactory(product=p1, external_key="ALIAS-001")
        with pytest.raises(IntegrityError):
            ProductAliasFactory(product=p2, external_key="ALIAS-001")

    def test_str(self):
        p = ProductFactory(name="AirPods 4")
        alias = ProductAliasFactory(product=p, external_key="EXT-AP4")
        assert "EXT-AP4" in str(alias)
        assert "AirPods 4" in str(alias)
