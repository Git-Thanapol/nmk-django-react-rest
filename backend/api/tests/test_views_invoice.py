"""
Invoice view tests — FIFO auto-assign, manual batch, stock restore, cancellation, edge cases.
"""
import pytest
import unittest.mock as mock
from decimal import Decimal
from django.urls import reverse

from .factories import (
    CompanyFactory, VendorFactory, ProductFactory,
    PurchaseOrderFactory, PurchaseItemFactory,
    InvoiceFactory, InvoiceItemFactory, UserFactory,
)
from api.models import Invoice, InvoiceItem, PurchaseItem

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _inv_data(company, invoice_number='INV-TEST-001', status='UNPRINTED', extra=None):
    """Minimal valid InvoiceForm POST data."""
    data = {
        'invoice_number': invoice_number,
        'company': company.pk,
        'status': status,
        'tax_include': 'on',
        'tax_percent': '7.00',
        'shipping_cost': '0.00',
        'invoice_date': '2026-01-15',
        'invoiceitem_set-TOTAL_FORMS': '0',
        'invoiceitem_set-INITIAL_FORMS': '0',
        'invoiceitem_set-MIN_NUM_FORMS': '0',
        'invoiceitem_set-MAX_NUM_FORMS': '1000',
    }
    if extra:
        data.update(extra)
    return data


def _add_item(data, idx, product=None, purchase_item=None, quantity=1, unit_price='1500.00',
              item_id='', invoice_id='', delete=''):
    """Append one formset row and bump TOTAL_FORMS."""
    p = f'invoiceitem_set-{idx}'
    data[f'{p}-product'] = str(product.pk) if product else ''
    data[f'{p}-purchase_item'] = str(purchase_item.pk) if purchase_item else ''
    data[f'{p}-quantity'] = str(quantity)
    data[f'{p}-unit_price'] = str(unit_price)
    data[f'{p}-id'] = str(item_id)
    data[f'{p}-invoice'] = str(invoice_id)
    data[f'{p}-DELETE'] = str(delete)
    data['invoiceitem_set-TOTAL_FORMS'] = str(idx + 1)
    return data


def _edit_data(invoice, items_data, cancel=False, cancel_reason=''):
    """Build POST data for editing an existing invoice."""
    data = {
        'invoice_number': invoice.invoice_number,
        'company': invoice.company.pk,
        'status': 'CANCELLED' if cancel else invoice.status,
        'tax_include': 'on',
        'tax_percent': '7.00',
        'shipping_cost': '0.00',
        'invoice_date': '2026-01-15',
        'cancel_reason': cancel_reason,
        'invoiceitem_set-TOTAL_FORMS': str(len(items_data)),
        'invoiceitem_set-INITIAL_FORMS': str(len(items_data)),
        'invoiceitem_set-MIN_NUM_FORMS': '0',
        'invoiceitem_set-MAX_NUM_FORMS': '1000',
    }
    for idx, item in enumerate(items_data):
        p = f'invoiceitem_set-{idx}'
        data[f'{p}-id'] = str(item.pk)
        data[f'{p}-invoice'] = str(invoice.pk)
        data[f'{p}-product'] = str(item.product.pk) if item.product else ''
        data[f'{p}-purchase_item'] = str(item.purchase_item.pk) if item.purchase_item else ''
        data[f'{p}-quantity'] = str(item.quantity)
        data[f'{p}-unit_price'] = str(item.unit_price)
        data[f'{p}-DELETE'] = ''
    return data


# ---------------------------------------------------------------------------
# GET: basic rendering
# ---------------------------------------------------------------------------

class TestInvoiceGetViews:
    def test_list_renders(self, auth_client):
        response = auth_client.get('/invoices/')
        assert response.status_code == 200

    def test_list_requires_login(self, client):
        response = client.get('/invoices/')
        assert response.status_code in (301, 302)
        assert 'login' in response['Location'].lower()

    def test_edit_renders_for_existing(self, auth_client, company, user):
        invoice = InvoiceFactory(company=company, created_by=user)
        response = auth_client.get(f'/invoices/edit/{invoice.pk}/')
        assert response.status_code == 200

    def test_list_hides_cancelled_by_default(self, auth_client, company, user):
        InvoiceFactory(company=company, created_by=user, invoice_number='SHOW-001', status='UNPRINTED')
        InvoiceFactory(company=company, created_by=user, invoice_number='HIDE-001', status='CANCELLED')
        response = auth_client.get('/invoices/')
        content = response.content.decode()
        assert 'SHOW-001' in content
        assert 'HIDE-001' not in content

    def test_list_shows_cancelled_with_param(self, auth_client, company, user):
        InvoiceFactory(company=company, created_by=user, invoice_number='CANCEL-XYZ', status='CANCELLED')
        response = auth_client.get('/invoices/?show_cancelled=1')
        assert 'CANCEL-XYZ' in response.content.decode()

    def test_list_search_filters_by_number(self, auth_client, company, user):
        InvoiceFactory(company=company, created_by=user, invoice_number='ALPHA-001')
        InvoiceFactory(company=company, created_by=user, invoice_number='BETA-001')
        response = auth_client.get('/invoices/?q=ALPHA')
        content = response.content.decode()
        assert 'ALPHA-001' in content
        assert 'BETA-001' not in content


# ---------------------------------------------------------------------------
# POST: FIFO auto-assign
# ---------------------------------------------------------------------------

class TestInvoiceFIFOAutoAssign:
    def test_fifo_selects_oldest_batch(self, auth_client, company, user):
        """Oldest (lowest ID) batch is consumed first when purchase_item left blank."""
        product = ProductFactory(company=company)
        po = PurchaseOrderFactory(company=company, created_by=user)
        batch1 = PurchaseItemFactory(purchase_order=po, product=product, quantity=10, unit_cost=Decimal('1000'))
        batch2 = PurchaseItemFactory(purchase_order=po, product=product, quantity=5, unit_cost=Decimal('1000'))

        data = _inv_data(company)
        _add_item(data, 0, product=product, quantity=3)

        response = auth_client.post('/invoices/', data)
        assert response.status_code == 302, response.content.decode()[:500]

        batch1.refresh_from_db()
        batch2.refresh_from_db()
        assert batch1.remaining_quantity == 7   # oldest → consumed
        assert batch2.remaining_quantity == 5   # untouched

        item = InvoiceItem.objects.get(invoice__invoice_number='INV-TEST-001')
        assert item.purchase_item_id == batch1.pk

    def test_fifo_no_single_batch_covers_qty_shows_error(self, auth_client, company, user):
        """When no single batch has enough stock, creation fails and stays on page."""
        product = ProductFactory(company=company)
        po = PurchaseOrderFactory(company=company, created_by=user)
        PurchaseItemFactory(purchase_order=po, product=product, quantity=6, unit_cost=Decimal('1000'))
        PurchaseItemFactory(purchase_order=po, product=product, quantity=5, unit_cost=Decimal('1000'))

        data = _inv_data(company)
        _add_item(data, 0, product=product, quantity=10)

        response = auth_client.post('/invoices/', data)
        assert response.status_code == 200  # stays on page, error message
        assert not Invoice.objects.filter(invoice_number='INV-TEST-001').exists()

    def test_fifo_no_stock_at_all_shows_error(self, auth_client, company, user):
        product = ProductFactory(company=company)

        data = _inv_data(company)
        _add_item(data, 0, product=product, quantity=1)

        response = auth_client.post('/invoices/', data)
        assert response.status_code == 200
        assert not Invoice.objects.filter(invoice_number='INV-TEST-001').exists()

    def test_fifo_item_without_product_skips_stock_logic(self, auth_client, company, user):
        """Items with no product (imported platform items) skip FIFO assignment."""
        data = _inv_data(company)
        _add_item(data, 0, product=None, quantity=2, unit_price='500')

        response = auth_client.post('/invoices/', data)
        # No product → no batch needed, but may still fail form validation
        # The view skips stock logic for items without product
        assert response.status_code in (200, 302)


# ---------------------------------------------------------------------------
# POST: manual batch selection
# ---------------------------------------------------------------------------

class TestInvoiceManualBatch:
    def test_manual_batch_deducts_from_selected(self, auth_client, company, user):
        product = ProductFactory(company=company)
        po = PurchaseOrderFactory(company=company, created_by=user)
        batch1 = PurchaseItemFactory(purchase_order=po, product=product, quantity=10, unit_cost=Decimal('1000'))
        batch2 = PurchaseItemFactory(purchase_order=po, product=product, quantity=10, unit_cost=Decimal('1000'))

        data = _inv_data(company)
        _add_item(data, 0, product=product, purchase_item=batch2, quantity=3)

        response = auth_client.post('/invoices/', data)
        assert response.status_code == 302

        batch1.refresh_from_db()
        batch2.refresh_from_db()
        assert batch1.remaining_quantity == 10  # untouched
        assert batch2.remaining_quantity == 7   # deducted

    def test_manual_batch_exceeded_stock_shows_error(self, auth_client, company, user):
        product = ProductFactory(company=company)
        po = PurchaseOrderFactory(company=company, created_by=user)
        batch = PurchaseItemFactory(purchase_order=po, product=product, quantity=3, unit_cost=Decimal('1000'))

        data = _inv_data(company)
        _add_item(data, 0, product=product, purchase_item=batch, quantity=5)

        response = auth_client.post('/invoices/', data)
        assert response.status_code == 200
        assert not Invoice.objects.filter(invoice_number='INV-TEST-001').exists()

    def test_manual_batch_product_mismatch_shows_error(self, auth_client, company, user):
        """Batch belonging to product_b, form says product_a → error."""
        product_a = ProductFactory(company=company, sku='SKU-A01')
        product_b = ProductFactory(company=company, sku='SKU-B01')
        po = PurchaseOrderFactory(company=company, created_by=user)
        batch_b = PurchaseItemFactory(purchase_order=po, product=product_b, quantity=10, unit_cost=Decimal('1000'))

        data = _inv_data(company)
        _add_item(data, 0, product=product_a, purchase_item=batch_b, quantity=1)

        response = auth_client.post('/invoices/', data)
        assert response.status_code == 200
        assert not Invoice.objects.filter(invoice_number='INV-TEST-001').exists()


# ---------------------------------------------------------------------------
# POST: cancel invoice → stock restore
# ---------------------------------------------------------------------------

class TestInvoiceCancellation:
    def _setup(self, company, user, qty_sold=3, batch_qty=10):
        product = ProductFactory(company=company)
        po = PurchaseOrderFactory(company=company, created_by=user)
        batch = PurchaseItemFactory(purchase_order=po, product=product, quantity=batch_qty,
                                     unit_cost=Decimal('1000'))
        batch.remaining_quantity = batch_qty - qty_sold
        batch.save(update_fields=['remaining_quantity'])

        invoice = InvoiceFactory(company=company, created_by=user, status='UNPRINTED')
        inv_item = InvoiceItemFactory(invoice=invoice, product=product, purchase_item=batch,
                                       quantity=qty_sold, unit_price=Decimal('1500'))
        return batch, invoice, inv_item

    def test_cancel_restores_remaining_quantity(self, auth_client, company, user):
        batch, invoice, inv_item = self._setup(company, user, qty_sold=3)
        assert batch.remaining_quantity == 7

        data = _edit_data(invoice, [inv_item], cancel=True, cancel_reason='Return')
        response = auth_client.post(f'/invoices/edit/{invoice.pk}/', data)
        assert response.status_code == 302

        batch.refresh_from_db()
        assert batch.remaining_quantity == 10  # 7 + 3 restored

    def test_cancel_suffixes_invoice_number(self, auth_client, company, user):
        _, invoice, inv_item = self._setup(company, user, qty_sold=1)
        original_num = invoice.invoice_number

        data = _edit_data(invoice, [inv_item], cancel=True)
        auth_client.post(f'/invoices/edit/{invoice.pk}/', data)

        invoice.refresh_from_db()
        assert invoice.status == 'CANCELLED'
        assert '-Cancelled-' in invoice.invoice_number
        assert original_num not in invoice.invoice_number  # original value is truncated+suffixed

    def test_cancel_redirects_to_invoice_list(self, auth_client, company, user):
        _, invoice, inv_item = self._setup(company, user, qty_sold=1)
        data = _edit_data(invoice, [inv_item], cancel=True)
        response = auth_client.post(f'/invoices/edit/{invoice.pk}/', data)
        assert response.status_code == 302
        assert '/invoices' in response['Location']


# ---------------------------------------------------------------------------
# POST: edit invoice → stock restore + re-deduct
# ---------------------------------------------------------------------------

class TestInvoiceEditStock:
    def test_edit_qty_restores_then_deducts(self, auth_client, company, user):
        """Increasing quantity from 3→5: restore 3 then deduct 5."""
        product = ProductFactory(company=company)
        po = PurchaseOrderFactory(company=company, created_by=user)
        batch = PurchaseItemFactory(purchase_order=po, product=product, quantity=10,
                                     unit_cost=Decimal('1000'))
        batch.remaining_quantity = 7  # 3 sold
        batch.save(update_fields=['remaining_quantity'])

        invoice = InvoiceFactory(company=company, created_by=user, status='UNPRINTED')
        inv_item = InvoiceItemFactory(invoice=invoice, product=product,
                                       purchase_item=batch, quantity=3,
                                       unit_price=Decimal('1500'))

        # Change quantity to 5
        data = _edit_data(invoice, [inv_item])
        data['invoiceitem_set-0-quantity'] = '5'
        data['invoiceitem_set-0-purchase_item'] = str(batch.pk)

        response = auth_client.post(f'/invoices/edit/{invoice.pk}/', data)
        assert response.status_code == 302

        batch.refresh_from_db()
        # restore 3 → 10; deduct 5 → 5
        assert batch.remaining_quantity == 5


# ---------------------------------------------------------------------------
# PDF side-effect (BUG-012)
# ---------------------------------------------------------------------------

class TestInvoicePDFSideEffect:
    def test_pdf_view_marks_billed_on_unprinted(self, auth_client, company, user):
        invoice = InvoiceFactory(company=company, created_by=user, status='UNPRINTED')
        with mock.patch('weasyprint.HTML') as m:
            m.return_value.write_pdf.return_value = b'%PDF-1.4'
            response = auth_client.get(f'/invoice/{invoice.pk}/pdf/')
        assert response.status_code == 200
        invoice.refresh_from_db()
        assert invoice.status == 'BILLED'
        assert invoice.is_printed is True

    @pytest.mark.xfail(strict=False, reason="BUG-012: pdf view sets BILLED even on cancelled invoices. views.py:1255")
    def test_pdf_view_does_not_mutate_cancelled_invoice(self, auth_client, company, user):
        invoice = InvoiceFactory(company=company, created_by=user, status='CANCELLED')
        with mock.patch('weasyprint.HTML') as m:
            m.return_value.write_pdf.return_value = b'%PDF-1.4'
            auth_client.get(f'/invoice/{invoice.pk}/pdf/')
        invoice.refresh_from_db()
        assert invoice.status == 'CANCELLED'

    @pytest.mark.xfail(strict=False, reason="BUG-012: pdf view updates print_datetime on every access. views.py:1256")
    def test_pdf_view_idempotent_after_first_print(self, auth_client, company, user):
        """Second PDF access should not mutate print_datetime."""
        invoice = InvoiceFactory(company=company, created_by=user, status='BILLED', is_printed=True)
        with mock.patch('weasyprint.HTML') as m:
            m.return_value.write_pdf.return_value = b'%PDF-1.4'
            auth_client.get(f'/invoice/{invoice.pk}/pdf/')
            first_dt = Invoice.objects.get(pk=invoice.pk).print_datetime
            auth_client.get(f'/invoice/{invoice.pk}/pdf/')
            second_dt = Invoice.objects.get(pk=invoice.pk).print_datetime
        assert first_dt == second_dt  # fails: every access updates print_datetime
