"""
Journey 7 & 8: PDF/Excel file download verification.

Uses page.request (Playwright API context) to make authenticated requests
and verify Content-Type + body length without needing a download dialog.
"""
import pytest

pytestmark = pytest.mark.django_db(transaction=True)


def _get_session_cookie(page, live_server):
    """Return the Django session cookie value from the active page."""
    cookies = page.context.cookies()
    for c in cookies:
        if c["name"] == "sessionid":
            return c["value"]
    return None


class TestInvoicePDFDownload:
    def test_invoice_pdf_returns_pdf_content_type(self, live_server, logged_in_page, e2e_user, e2e_company):
        from api.tests.factories import InvoiceFactory
        invoice = InvoiceFactory(created_by=e2e_user, company=e2e_company)

        url = f"{live_server.url}/invoice/{invoice.pk}/pdf/"
        response = logged_in_page.request.get(url)

        assert response.status == 200
        assert "application/pdf" in response.headers.get("content-type", "")
        assert len(response.body()) > 100

    def test_invoice_pdf_filename_contains_invoice_number(self, live_server, logged_in_page, e2e_user, e2e_company):
        from api.tests.factories import InvoiceFactory
        invoice = InvoiceFactory(created_by=e2e_user, company=e2e_company)

        url = f"{live_server.url}/invoice/{invoice.pk}/pdf/"
        response = logged_in_page.request.get(url)

        disposition = response.headers.get("content-disposition", "")
        assert invoice.invoice_number in disposition


class TestInvoiceExcelDownload:
    def test_invoice_excel_returns_xlsx(self, live_server, logged_in_page, e2e_user, e2e_company):
        from api.tests.factories import InvoiceFactory
        invoice = InvoiceFactory(created_by=e2e_user, company=e2e_company)

        url = f"{live_server.url}/invoice/{invoice.pk}/excel/"
        response = logged_in_page.request.get(url)

        assert response.status == 200
        content_type = response.headers.get("content-type", "")
        assert "spreadsheet" in content_type or "xlsx" in content_type or "openxml" in content_type
        assert len(response.body()) > 100

    def test_invoice_excel_filename_contains_invoice_number(self, live_server, logged_in_page, e2e_user, e2e_company):
        from api.tests.factories import InvoiceFactory
        invoice = InvoiceFactory(created_by=e2e_user, company=e2e_company)

        url = f"{live_server.url}/invoice/{invoice.pk}/excel/"
        response = logged_in_page.request.get(url)

        disposition = response.headers.get("content-disposition", "")
        assert invoice.invoice_number in disposition


class TestWHTCertPage:
    def test_wht_list_page_renders(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/tax/50tawi/")
        assert logged_in_page.locator("body").is_visible()

    # BUG: /tax/50tawi/ is missing @login_required (same pattern as BUG-004).
    # This test documents the broken state — unauthenticated access returns 200.
    # Fix: add @login_required above wht_cert_list_view in api/views.py line 949.
    def test_unauthenticated_wht_accessible_bug(self, live_server, page):
        page.goto(f"{live_server.url}/tax/50tawi/")
        page.wait_for_load_state("networkidle")
        # BUG: should redirect to login, but currently accessible (stays on /tax/50tawi/)
        assert "/tax/50tawi/" in page.url
