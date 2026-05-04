import factory
from factory.django import DjangoModelFactory
from django.contrib.auth.models import User
from decimal import Decimal

from api.models import (
    Company, Vendor, Product, PurchaseOrder, PurchaseItem,
    Invoice, InvoiceItem, Transaction, Note,
    ProductMapping, ProductAlias, ImportLog, WithholdingTaxCert,
)


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@test.com")
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')
    is_active = True


class CompanyFactory(DjangoModelFactory):
    class Meta:
        model = Company

    name = factory.Sequence(lambda n: f"Test Company {n}")
    nick_name = factory.Sequence(lambda n: f"TC{n}")
    tax_id = factory.Sequence(lambda n: f"1234567890{n:03d}")
    is_active = True


class VendorFactory(DjangoModelFactory):
    class Meta:
        model = Vendor

    company = factory.SubFactory(CompanyFactory)
    name = factory.Sequence(lambda n: f"Vendor {n}")
    phone = "081-000-0000"
    is_active = True


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    company = factory.SubFactory(CompanyFactory)
    sku = factory.Sequence(lambda n: f"SKU-{n:04d}")
    name = factory.Sequence(lambda n: f"Product {n}")
    category = "SMARTPHONE"
    cost_price = Decimal("1000.00")
    selling_price = Decimal("1500.00")
    is_active = True


class PurchaseOrderFactory(DjangoModelFactory):
    class Meta:
        model = PurchaseOrder

    company = factory.SubFactory(CompanyFactory)
    po_number = factory.Sequence(lambda n: f"PO-{n:04d}")
    vendor = factory.SubFactory(VendorFactory, company=factory.SelfAttribute('..company'))
    purchase_type = "Cash"
    status = "PAID"
    tax_include = True
    tax_percent = Decimal("7.00")
    created_by = factory.SubFactory(UserFactory)


class PurchaseItemFactory(DjangoModelFactory):
    class Meta:
        model = PurchaseItem

    purchase_order = factory.SubFactory(PurchaseOrderFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 10
    unit_cost = Decimal("1000.00")


class InvoiceFactory(DjangoModelFactory):
    class Meta:
        model = Invoice

    company = factory.SubFactory(CompanyFactory)
    invoice_number = factory.Sequence(lambda n: f"INV-{n:04d}")
    status = "UNPRINTED"
    tax_include = True
    tax_percent = Decimal("7.00")
    shipping_cost = Decimal("0.00")
    discount_amount = Decimal("0.00")
    created_by = factory.SubFactory(UserFactory)


class InvoiceItemFactory(DjangoModelFactory):
    class Meta:
        model = InvoiceItem

    invoice = factory.SubFactory(InvoiceFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 1
    unit_price = Decimal("1500.00")


class TransactionFactory(DjangoModelFactory):
    class Meta:
        model = Transaction

    company = factory.SubFactory(CompanyFactory)
    transaction_number = factory.Sequence(lambda n: f"TX-{n:04d}")
    type = "INCOME"
    category = "OTHER"
    amount = Decimal("1000.00")
    description = "Test transaction"
    created_by = factory.SubFactory(UserFactory)


class NoteFactory(DjangoModelFactory):
    class Meta:
        model = Note

    user = factory.SubFactory(UserFactory)
    title = factory.Sequence(lambda n: f"Note {n}")
    content = "Test content"


class ProductMappingFactory(DjangoModelFactory):
    class Meta:
        model = ProductMapping

    product = factory.SubFactory(ProductFactory)
    platform_name = factory.Sequence(lambda n: f"Platform Product Name {n}")
    platform = "SHOPEE"


class ProductAliasFactory(DjangoModelFactory):
    class Meta:
        model = ProductAlias

    product = factory.SubFactory(ProductFactory)
    external_key = factory.Sequence(lambda n: f"EXT-KEY-{n}")
    platform = "SHOPEE"


class WithholdingTaxCertFactory(DjangoModelFactory):
    class Meta:
        model = WithholdingTaxCert

    company = factory.SubFactory(CompanyFactory)
    vendor = factory.SubFactory(VendorFactory)
    income_type = "8"
    tax_rate = Decimal("3.00")
    amount_before_tax = Decimal("10000.00")
    tax_amount = Decimal("300.00")
