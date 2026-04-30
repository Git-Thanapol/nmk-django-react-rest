"""
Template-view tests — authentication gate, CRUD smoke tests, redirect behaviour.
"""
import pytest
from django.urls import reverse

from .factories import (
    CompanyFactory, VendorFactory, ProductFactory,
    PurchaseOrderFactory, PurchaseItemFactory,
    InvoiceFactory, InvoiceItemFactory,
    TransactionFactory, UserFactory,
)


# ---------------------------------------------------------------------------
# Authentication gate
# ---------------------------------------------------------------------------

PROTECTED_GET_URLS = [
    '/purchases/',
    '/invoices/',
    '/products/',
    '/vendors/',
    '/transactions/',
    '/companies/',
]

# BUG: /reports/ is NOT protected with @login_required — unauthenticated users can access it.
# Tracked in TEST_PLAN.md as BUG-004.
UNPROTECTED_SHOULD_BE_PROTECTED = ['/reports/']


@pytest.mark.django_db
@pytest.mark.parametrize("url", PROTECTED_GET_URLS)
def test_unauthenticated_redirects_to_login(client, url):
    response = client.get(url)
    assert response.status_code in (302, 301)
    assert '/login' in response['Location'] or 'login' in response['Location'].lower()


@pytest.mark.django_db
@pytest.mark.parametrize("url", PROTECTED_GET_URLS)
def test_authenticated_can_access(auth_client, url):
    response = auth_client.get(url)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Login view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLoginView:
    def test_login_page_renders(self, client):
        response = client.get('/login/')
        assert response.status_code == 200

    def test_valid_credentials_redirect(self, client, user):
        response = client.post('/login/', {
            'username': user.username,
            'password': 'testpass123',
        })
        assert response.status_code == 302

    def test_invalid_credentials_stays_on_login(self, client, user):
        response = client.post('/login/', {
            'username': user.username,
            'password': 'wrongpassword',
        })
        assert response.status_code == 200

    def test_empty_credentials_stays_on_login(self, client):
        response = client.post('/login/', {'username': '', 'password': ''})
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Product CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestProductViews:
    def test_list_shows_products(self, auth_client, product):
        response = auth_client.get('/products/')
        assert response.status_code == 200

    def test_create_product_get(self, auth_client):
        response = auth_client.get('/products/')
        assert response.status_code == 200

    def test_create_product_post(self, auth_client, company):
        data = {
            'sku': 'NEW-001', 'name': 'New Product', 'category': 'OTHER',
            'cost_price': '100', 'selling_price': '200',
            'is_active': 'on', 'company': company.pk,
        }
        response = auth_client.post('/products/', data)
        assert response.status_code in (200, 302)

    def test_edit_product_get(self, auth_client, product):
        response = auth_client.get(f'/products/edit/{product.pk}/')
        assert response.status_code == 200

    def test_delete_product(self, auth_client, product):
        response = auth_client.post(f'/products/delete/{product.pk}/')
        assert response.status_code in (200, 302, 404)


# ---------------------------------------------------------------------------
# Vendor CRUD
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestVendorViews:
    def test_list_shows_vendors(self, auth_client, vendor):
        response = auth_client.get('/vendors/')
        assert response.status_code == 200

    def test_edit_vendor_get(self, auth_client, vendor):
        response = auth_client.get(f'/vendors/edit/{vendor.pk}/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Purchase order views
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPurchaseViews:
    def test_list_purchases(self, auth_client):
        response = auth_client.get('/purchases/')
        assert response.status_code == 200

    def test_edit_purchase_get(self, auth_client, user):
        po = PurchaseOrderFactory(created_by=user)
        response = auth_client.get(f'/purchases/edit/{po.pk}/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Invoice views
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInvoiceViews:
    def test_list_invoices(self, auth_client):
        response = auth_client.get('/invoices/')
        assert response.status_code == 200

    def test_edit_invoice_get(self, auth_client, user):
        inv = InvoiceFactory(created_by=user)
        response = auth_client.get(f'/invoices/edit/{inv.pk}/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Company views
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCompanyViews:
    def test_company_list(self, auth_client, company):
        response = auth_client.get('/companies/')
        assert response.status_code == 200

    def test_add_company_get(self, auth_client):
        response = auth_client.get('/companies/add/')
        assert response.status_code == 200

    def test_add_company_post(self, auth_client):
        data = {
            'name': 'Brand New Co', 'nick_name': 'BNC',
            'tax_id': '', 'address': '', 'phone': '',
            'email': '', 'is_active': 'on',
        }
        response = auth_client.post('/companies/add/', data)
        assert response.status_code in (200, 302)

    def test_edit_company_get(self, auth_client, company):
        response = auth_client.get(f'/companies/{company.pk}/edit/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Duplicate PO check (AJAX)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDuplicatePOCheck:
    def test_returns_json(self, auth_client, user):
        po = PurchaseOrderFactory(created_by=user)
        response = auth_client.get(
            '/api/purchases/check-duplicate/',
            {'po_number': po.po_number, 'company_id': po.company_id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert response.status_code == 200
        data = response.json()
        # Response uses 'duplicate_po_number', not 'is_duplicate'
        assert 'duplicate_po_number' in data

    def test_existing_po_flagged_as_duplicate(self, auth_client, user):
        po = PurchaseOrderFactory(created_by=user)
        response = auth_client.get(
            '/api/purchases/check-duplicate/',
            {'po_number': po.po_number, 'company_id': po.company_id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert response.status_code == 200
        assert response.json()['duplicate_po_number'] is True

    def test_no_duplicate_when_po_not_exists(self, auth_client):
        response = auth_client.get(
            '/api/purchases/check-duplicate/',
            {'po_number': 'DOESNOTEXIST', 'company_id': 999},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        assert response.status_code == 200
        assert response.json()['duplicate_po_number'] is False
