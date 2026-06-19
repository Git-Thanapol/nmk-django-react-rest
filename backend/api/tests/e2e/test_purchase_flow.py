"""
Journey 5: Purchase order create with formset + AJAX duplicate-PO check.

The duplicate-check fires on blur of #id_po_number and calls
GET /api/purchases/check-duplicate/?po_number=...&company_id=...
If duplicate, shows #po_number_error (hidden by default with class d-none).
"""
import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestPurchaseListPage:
    def test_purchase_list_renders(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/purchases/")
        assert logged_in_page.locator("#id_po_number").is_visible()

    def test_existing_po_appears_in_list(self, live_server, logged_in_page, e2e_user, e2e_company):
        from api.tests.factories import PurchaseOrderFactory, VendorFactory
        vendor = VendorFactory(company=e2e_company)
        po = PurchaseOrderFactory(created_by=e2e_user, company=e2e_company, vendor=vendor)

        logged_in_page.goto(f"{live_server.url}/purchases/")
        assert po.po_number in logged_in_page.content()


class TestDuplicatePOAjax:
    def test_no_error_shown_for_new_po_number(self, live_server, logged_in_page, e2e_company):
        from api.tests.factories import VendorFactory
        VendorFactory(company=e2e_company)

        logged_in_page.goto(f"{live_server.url}/purchases/")
        po_input = logged_in_page.locator("#id_po_number")
        po_input.fill("BRAND-NEW-PO-9999")
        po_input.blur()
        logged_in_page.wait_for_load_state("networkidle")

        error_el = logged_in_page.locator("#po_number_error")
        # Error element should exist but be hidden (d-none class)
        assert "d-none" in (error_el.get_attribute("class") or "")

    def test_duplicate_po_number_shows_error(self, live_server, logged_in_page, e2e_user, e2e_company):
        from api.tests.factories import PurchaseOrderFactory, VendorFactory
        vendor = VendorFactory(company=e2e_company)
        existing_po = PurchaseOrderFactory(
            created_by=e2e_user, company=e2e_company, vendor=vendor
        )

        logged_in_page.goto(f"{live_server.url}/purchases/")

        # Fill in the company select first (needed for the check)
        company_select = logged_in_page.locator("#id_company")
        company_select.select_option(value=str(e2e_company.pk))

        po_input = logged_in_page.locator("#id_po_number")
        po_input.fill(existing_po.po_number)
        po_input.blur()

        # Wait for AJAX to complete
        logged_in_page.wait_for_load_state("networkidle")

        error_el = logged_in_page.locator("#po_number_error")
        # Error element should no longer be hidden
        classes = error_el.get_attribute("class") or ""
        assert "d-none" not in classes


class TestPurchaseOrderCreate:
    def test_purchase_form_has_formset_table(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/purchases/")
        assert logged_in_page.locator("#itemsTable").is_visible()

    def test_formset_has_at_least_one_row(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/purchases/")
        rows = logged_in_page.locator("#itemsTable tbody tr.item-row")
        assert rows.count() >= 1

    def test_create_purchase_order(self, live_server, logged_in_page, e2e_user, e2e_company, e2e_product):
        from api.tests.factories import VendorFactory
        vendor = VendorFactory(company=e2e_company)

        logged_in_page.goto(f"{live_server.url}/purchases/")

        # Fill header fields
        logged_in_page.fill("#id_po_number", "E2E-PO-0001")
        logged_in_page.locator("#id_vendor").select_option(value=str(vendor.pk))
        logged_in_page.locator("#id_company").select_option(value=str(e2e_company.pk))

        # Fill the first formset row
        first_row = logged_in_page.locator("#itemsTable tbody tr.item-row").first
        first_row.locator("select").first.select_option(value=str(e2e_product.pk))
        first_row.locator('input[name*="quantity"]').fill("5")
        first_row.locator('input[name*="unit_cost"]').fill("1000")

        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_load_state("networkidle")

        # After successful save, redirects to purchase list
        assert "E2E-PO-0001" in logged_in_page.content()
