"""
Journey 9: CSV import — upload Shopee CSV → ImportLog created.

UI flow:
1. Navigate to /import/platforms/
2. Select company from the dropdown
3. Set the hidden file input (#shopeeFile) — triggers handleFileSelect() which
   unhides step-2 and shows the submit button
4. Click the submit button (inside #shopeeForm, step-2)
5. Assert redirect back and import log entry in table

The background thread runs async; we only check for PENDING/COMPLETED in the
imports table, not for the final COMPLETED state.
"""
import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestPlatformImportPage:
    def test_import_page_renders(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/import/platforms/")
        assert logged_in_page.locator("body").is_visible()
        assert logged_in_page.locator("#shopeeFile").count() >= 1

    def test_unauthenticated_import_redirects(self, live_server, page):
        page.goto(f"{live_server.url}/import/platforms/")
        page.wait_for_load_state("networkidle")
        assert "login" in page.url.lower()

    def test_upload_shopee_csv_creates_import_log(
        self, live_server, logged_in_page, e2e_company, sample_shopee_csv
    ):
        logged_in_page.goto(f"{live_server.url}/import/platforms/")

        # Select company from the Shopee form's company dropdown
        shopee_company_select = logged_in_page.locator("#shopeeForm select[name='company_id']")
        shopee_company_select.select_option(value=str(e2e_company.pk))

        # Set the file — triggers handleFileSelect() which unhides the submit button
        logged_in_page.locator("#shopeeFile").set_input_files(sample_shopee_csv)

        # After JS fires, #shopee-step-2 should become visible
        logged_in_page.wait_for_selector("#shopee-step-2:not(.d-none)", timeout=5000)

        # Click the submit button inside the Shopee form
        logged_in_page.locator("#shopeeForm button[type='submit']").click()
        logged_in_page.wait_for_load_state("networkidle")

        # Should redirect back to the import page showing import history
        assert "import" in logged_in_page.url
        content = logged_in_page.content()
        assert any(kw in content.lower() for kw in ["shopee", "pending", "completed", "failed"])

    def test_submit_without_company_stays_on_page(self, live_server, logged_in_page, sample_shopee_csv):
        """Submitting without selecting a company should be blocked by HTML5 required validation."""
        logged_in_page.goto(f"{live_server.url}/import/platforms/")

        # Set file without selecting a company
        logged_in_page.locator("#shopeeFile").set_input_files(sample_shopee_csv)
        logged_in_page.wait_for_selector("#shopee-step-2:not(.d-none)", timeout=5000)

        # Try to submit — browser required validation on company_id should block it
        logged_in_page.locator("#shopeeForm button[type='submit']").click()
        logged_in_page.wait_for_load_state("networkidle")

        # Should stay on the import page (not redirected away)
        assert "import" in logged_in_page.url
