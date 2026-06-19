"""
Form validation tests — clean methods, edge cases, and widget configuration.
"""
import pytest
from decimal import Decimal

from api.forms import (
    ProductForm, VendorForm, CompanyForm,
    PurchaseOrderForm, InvoiceForm, TransactionForm,
    ImportFileForm,
)
from .factories import CompanyFactory, VendorFactory, ProductFactory, UserFactory


@pytest.mark.django_db
class TestProductFormSkuValidation:
    def test_valid_new_product(self, company):
        data = {
            'sku': 'UNIQUE-SKU', 'name': 'Widget', 'category': 'OTHER',
            'cost_price': '100', 'selling_price': '150',
            'is_active': True, 'company': company.pk,
        }
        form = ProductForm(data=data)
        assert form.is_valid(), form.errors

    def test_duplicate_sku_globally_rejected(self, company):
        """
        BUG NOTE: ProductForm.clean_sku() checks global uniqueness, but the
        model only enforces unique_together ['company', 'sku']. The form is
        stricter than the DB constraint, preventing valid cross-company reuse.
        """
        ProductFactory(company=company, sku="DUP-SKU")
        data = {
            'sku': 'DUP-SKU', 'name': 'Another Widget', 'category': 'OTHER',
            'cost_price': '100', 'selling_price': '150',
            'is_active': True, 'company': company.pk,
        }
        form = ProductForm(data=data)
        assert not form.is_valid()
        assert 'sku' in form.errors

    def test_editing_same_instance_does_not_raise_duplicate_error(self, company):
        p = ProductFactory(company=company, sku="EDIT-ME")
        data = {
            'sku': 'EDIT-ME', 'name': 'Updated Name', 'category': 'OTHER',
            'cost_price': '200', 'selling_price': '300',
            'is_active': True, 'company': company.pk,
        }
        form = ProductForm(data=data, instance=p)
        assert form.is_valid(), form.errors

    def test_sku_required(self, company):
        data = {
            'sku': '', 'name': 'Widget', 'category': 'OTHER',
            'cost_price': '100', 'selling_price': '150',
            'is_active': True, 'company': company.pk,
        }
        form = ProductForm(data=data)
        assert not form.is_valid()
        assert 'sku' in form.errors


@pytest.mark.django_db
class TestVendorForm:
    def test_valid_vendor(self):
        data = {
            'name': 'New Vendor', 'contact_person': '', 'phone': '',
            'email': '', 'address': '', 'tax_id': '', 'is_active': True,
        }
        form = VendorForm(data=data)
        assert form.is_valid(), form.errors

    def test_email_field_validates_format(self):
        data = {
            'name': 'Vendor X', 'contact_person': '', 'phone': '',
            'email': 'not-an-email', 'address': '', 'tax_id': '', 'is_active': True,
        }
        form = VendorForm(data=data)
        assert not form.is_valid()
        assert 'email' in form.errors

    def test_company_selection_prefilled_on_edit(self, vendor):
        form = VendorForm(instance=vendor)
        assert form.fields['company_selection'].initial == vendor.company.name


@pytest.mark.django_db
class TestCompanyForm:
    def test_valid_company(self):
        data = {
            'name': 'New Co Ltd', 'nick_name': 'NC', 'tax_id': '1234567890123',
            'address': '123 Main St', 'phone': '021234567',
            'email': 'info@newco.com', 'is_active': True,
        }
        form = CompanyForm(data=data)
        assert form.is_valid(), form.errors

    def test_name_required(self):
        data = {
            'name': '', 'nick_name': 'NC', 'tax_id': '',
            'address': '', 'phone': '', 'email': '', 'is_active': True,
        }
        form = CompanyForm(data=data)
        assert not form.is_valid()
        assert 'name' in form.errors


@pytest.mark.django_db
class TestImportFileForm:
    def test_rejects_disallowed_extension(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("malware.exe", b"bad content", content_type="application/octet-stream")
        form = ImportFileForm(data={'platform': 'shopee'}, files={'import_file': f})
        assert not form.is_valid()
        assert 'import_file' in form.errors

    def test_accepts_xlsx(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("orders.xlsx", b"pk\x03\x04", content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        form = ImportFileForm(data={'platform': 'shopee'}, files={'import_file': f})
        assert form.is_valid(), form.errors

    def test_accepts_csv(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        f = SimpleUploadedFile("orders.csv", b"order_id,status\n1,paid", content_type="text/csv")
        form = ImportFileForm(data={'platform': 'lazada'}, files={'import_file': f})
        assert form.is_valid(), form.errors
