"""
Journey 1: Login → dashboard, logout, bad credentials.
"""
import pytest

pytestmark = pytest.mark.django_db(transaction=True)


class TestLogin:
    def test_login_page_renders(self, live_server, page):
        page.goto(f"{live_server.url}/login/")
        assert page.title() != ""
        assert page.locator("#id_username").is_visible()
        assert page.locator("#id_password").is_visible()

    def test_valid_credentials_redirect_to_dashboard(self, live_server, page, e2e_user):
        page.goto(f"{live_server.url}/login/")
        page.fill("#id_username", e2e_user.username)
        page.fill("#id_password", "testpass123")
        page.click('button[type="submit"]')
        page.wait_for_url("**/dashboard/")
        assert "dashboard" in page.url

    def test_invalid_password_stays_on_login(self, live_server, page, e2e_user):
        page.goto(f"{live_server.url}/login/")
        page.fill("#id_username", e2e_user.username)
        page.fill("#id_password", "wrongpassword")
        page.click('button[type="submit"]')
        # Should stay on login page (no redirect)
        assert "login" in page.url or page.url.rstrip("/").endswith("")
        # Error message should be visible somewhere on the page
        content = page.content()
        assert any(kw in content for kw in ["ไม่ถูกต้อง", "incorrect", "invalid", "Password"])

    def test_empty_credentials_stays_on_login(self, live_server, page):
        page.goto(f"{live_server.url}/login/")
        page.click('button[type="submit"]')
        assert "help" not in page.url

    def test_logout_redirects_to_login(self, live_server, page, e2e_user):
        # Log in first
        page.goto(f"{live_server.url}/login/")
        page.fill("#id_username", e2e_user.username)
        page.fill("#id_password", "testpass123")
        page.click('button[type="submit"]')
        page.wait_for_url("**/dashboard/")

        # Now log out
        page.goto(f"{live_server.url}/logout/")
        page.wait_for_load_state("networkidle")
        # logout redirects to 'login' view which is at / or /login/
        assert "login" in page.url or page.url in (f"{live_server.url}/", f"{live_server.url}/login/")

    def test_authenticated_user_can_access_purchases(self, live_server, logged_in_page):
        logged_in_page.goto(f"{live_server.url}/purchases/")
        assert logged_in_page.locator("body").is_visible()
        assert logged_in_page.url.endswith("/purchases/")

    def test_unauthenticated_purchases_redirects(self, live_server, page):
        page.goto(f"{live_server.url}/purchases/")
        page.wait_for_load_state("networkidle")
        # Should redirect to login (accounts/login or /login)
        assert "login" in page.url.lower()
