# pytest-playwright runs inside an asyncio event loop. Django raises
# SynchronousOnlyOperation when it detects a running loop unless this is set.
import os
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

"""
E2E test fixtures — pytest-playwright + pytest-django.

All tests in this package use `transaction=True` so data committed in the
test thread is visible to the live-server thread (same in-process connection
shared via Django's connections_override mechanism).

Run:
    pytest api/tests/e2e/ -v --headed           # visible browser
    pytest api/tests/e2e/ --video=retain-on-failure --screenshot=only-on-failure
"""
import pytest

from api.tests.factories import (
    CompanyFactory,
    UserFactory,
    VendorFactory,
    ProductFactory,
)


@pytest.fixture
def e2e_user(db):
    """A regular user with a known password (testpass123)."""
    return UserFactory()


@pytest.fixture
def e2e_company(db):
    return CompanyFactory()


@pytest.fixture
def e2e_vendor(db, e2e_company):
    return VendorFactory(company=e2e_company)


@pytest.fixture
def e2e_product(db, e2e_company):
    return ProductFactory(company=e2e_company)


@pytest.fixture
def logged_in_page(live_server, page, e2e_user):
    """Playwright page already authenticated as e2e_user."""
    page.goto(f"{live_server.url}/login/")
    page.fill("#id_username", e2e_user.username)
    page.fill("#id_password", "testpass123")
    page.click('button[type="submit"]')
    page.wait_for_url("**/dashboard/")
    return page


@pytest.fixture
def sample_shopee_csv(tmp_path):
    """Minimal Shopee-format CSV fixture file."""
    content = (
        "Order ID,Order Status,Tracking Number,SKU Reference No.,Product Name,"
        "Variation Name,Quantity,Original Price,Deal Price,Seller Discount,"
        "Shopee Discount,Voucher Code,Coins,Payment Method,Estimated Ship Out Date,"
        "Ship Time,Order Complete Time,Is Boosted,Net Sales,Estimated Shipping Fee,"
        "Actual Shipping Cost,Seller Shipping Discount,Shopee Shipping Rebate,"
        "Shipping Fee Seller,Return / Refund Status,Username (Buyer),Receiver Name,"
        "Province,City,District,Remarks\n"
        "241100000001,Completed,TH1234567890,SKU-0001,Test Product,,1,1500.00,"
        "1500.00,0.00,0.00,,0,COD,01/05/2026,01/05/2026,03/05/2026,No,1500.00,"
        "50.00,50.00,0.00,0.00,50.00,,buyer1,Buyer One,Bangkok,Bangkok,Phra Nakhon,\n"
    )
    csv_file = tmp_path / "shopee_orders.csv"
    csv_file.write_text(content, encoding="utf-8-sig")
    return str(csv_file)
