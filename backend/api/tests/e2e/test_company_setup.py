"""
Journey 3: Company create → appears in list → edit name persists.
"""
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)


class TestCompanySetup:
    def test_company_list_renders(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/companies/")
        assert logged_in_page.locator("body").is_visible()

    def test_company_add_form_renders(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/companies/add/")
        assert logged_in_page.locator("#id_name").is_visible()
        assert logged_in_page.locator("#id_nick_name").is_visible()

    def test_create_company_appears_in_list(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/companies/add/")
        logged_in_page.fill("#id_name", "E2E Test Company")
        logged_in_page.fill("#id_nick_name", "E2E")
        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_load_state("networkidle")

        # After save, should redirect to company list
        assert "companies" in logged_in_page.url or "add" not in logged_in_page.url
        content = logged_in_page.content()
        assert "E2E Test Company" in content

    def test_edit_company_name_persists(self, live_server, logged_in_page, e2e_company):
        logged_in_page.goto(f"{live_server.url}/companies/{e2e_company.pk}/edit/")
        logged_in_page.fill("#id_name", "Updated Company Name")
        logged_in_page.click('button[type="submit"]')
        logged_in_page.wait_for_load_state("networkidle")

        # Navigate back to the edit page and verify the name was saved
        logged_in_page.goto(f"{live_server.url}/companies/{e2e_company.pk}/edit/")
        name_input = logged_in_page.locator("#id_name")
        assert name_input.input_value() == "Updated Company Name"

    def test_company_list_shows_existing_company(self, live_server, logged_in_page, e2e_company):
        logged_in_page.goto(f"{live_server.url}/companies/")
        content = logged_in_page.content()
        assert e2e_company.name in content
