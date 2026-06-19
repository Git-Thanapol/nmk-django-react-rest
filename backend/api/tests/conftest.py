import pytest
from rest_framework.test import APIClient
from .factories import UserFactory, CompanyFactory, VendorFactory, ProductFactory


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def admin_user(db):
    return UserFactory(is_staff=True, is_superuser=True)


@pytest.fixture
def company(db):
    return CompanyFactory()


@pytest.fixture
def vendor(db, company):
    return VendorFactory(company=company)


@pytest.fixture
def product(db, company):
    return ProductFactory(company=company)


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_api_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client
