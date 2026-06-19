"""
Journey 8: Reports dashboard — access control + page renders + export.

Note: BUG-004 — /reports/ is missing @login_required. The test
`test_reports_accessible_without_login` documents this bug:
it PASSES (200) even without authentication, which is incorrect behaviour.
Once BUG-004 is fixed, this test should be updated to expect a 302 redirect.
"""
import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestReportsDashboard:
    def test_reports_page_renders_when_authenticated(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/reports/")
        assert logged_in_page.locator("body").is_visible()
        assert logged_in_page.url.endswith("/reports/")

    def test_reports_page_has_filter_form(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/reports/")
        # The reports page should have a form for date filtering
        form = logged_in_page.locator("form")
        assert form.count() >= 1

    # BUG-004: /reports/ should redirect unauthenticated users but currently doesn't.
    # This test DOCUMENTS the bug — it passes because the bug exists.
    # When BUG-004 is fixed, change assert to: assert "login" in page.url.lower()
    def test_reports_accessible_without_login_bug004(self, live_server, page):
        page.goto(f"{live_server.url}/reports/")
        page.wait_for_load_state("networkidle")
        # BUG: unauthenticated access returns 200 (should be 302 → login)
        assert "/reports/" in page.url  # documents the current broken state


class TestVatTrackingPage:
    def test_vat_tracking_page_renders(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/vat-tracking/")
        assert logged_in_page.locator("body").is_visible()

    def test_unauthenticated_vat_tracking_redirects(self, live_server, page):
        page.goto(f"{live_server.url}/vat-tracking/")
        page.wait_for_load_state("networkidle")
        assert "login" in page.url.lower()
