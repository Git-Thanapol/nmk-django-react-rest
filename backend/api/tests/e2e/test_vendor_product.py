"""
Journey 4: Vendor list + create, Product list + create.
"""
import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestVendorUI:
    def test_vendor_list_renders(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/vendors/")
        assert logged_in_page.locator("body").is_visible()
        assert logged_in_page.locator("#id_name").is_visible()

    def test_existing_vendor_appears_in_list(self, live_server, logged_in_page, e2e_vendor):
        logged_in_page.goto(f"{live_server.url}/vendors/")
        assert e2e_vendor.name in logged_in_page.content()

    def test_create_vendor_via_ui(self, live_server, logged_in_page, e2e_company):
        logged_in_page.goto(f"{live_server.url}/vendors/")
        logged_in_page.fill("#id_name", "E2E Vendor Co.")
        logged_in_page.fill("#id_company_selection", e2e_company.name)
        logged_in_page.fill("#id_phone", "081-000-9999")
        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_load_state("networkidle")

        # After successful save, redirects back to vendor list
        assert "vendors" in logged_in_page.url
        assert "E2E Vendor Co." in logged_in_page.content()

    def test_edit_vendor_form_renders(self, live_server, logged_in_page, e2e_vendor):
        logged_in_page.goto(f"{live_server.url}/vendors/edit/{e2e_vendor.pk}/")
        assert logged_in_page.locator("#id_name").is_visible()


class TestProductUI:
    def test_product_list_renders(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/products/")
        assert logged_in_page.locator("body").is_visible()
        assert logged_in_page.locator("#id_sku").is_visible()

    def test_existing_product_appears_in_list(self, live_server, logged_in_page, e2e_product):
        logged_in_page.goto(f"{live_server.url}/products/")
        assert e2e_product.sku in logged_in_page.content()

    def test_create_product_via_ui(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/products/")
        logged_in_page.fill("#id_sku", "E2E-SKU-001")
        logged_in_page.fill("#id_name", "E2E Test Product")
        logged_in_page.fill("#id_category", "Electronics")  # required field
        logged_in_page.fill("#id_cost_price", "500")
        logged_in_page.fill("#id_selling_price", "750")
        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_load_state("networkidle")

        # After redirect, product appears in list
        assert "E2E-SKU-001" in logged_in_page.content()

    def test_edit_product_form_renders(self, live_server, logged_in_page, e2e_product):
        logged_in_page.goto(f"{live_server.url}/products/edit/{e2e_product.pk}/")
        sku_input = logged_in_page.locator("#id_sku")
        assert sku_input.is_visible()
        assert sku_input.input_value() == e2e_product.sku

    def test_product_search_filters_results(self, live_server, logged_in_page, e2e_product):
        logged_in_page.goto(f"{live_server.url}/products/?q={e2e_product.sku}")
        assert e2e_product.sku in logged_in_page.content()
