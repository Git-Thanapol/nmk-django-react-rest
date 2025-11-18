from django.db import models
from django.contrib.auth.models import User

from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from django.db import migrations, models


# Create your models here.
class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,related_name='notes')
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    

class Company(models.Model):
    """Multi-company support"""
    name = models.CharField(max_length=200)
    tax_id = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True,null=True)
    email = models.EmailField(blank=True,null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'companies'
        verbose_name_plural = 'Companies'
    
    def __str__(self):
        return self.name

class SellingChannel(models.Model):
    """Dynamic selling channels (can add more than 4)"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'selling_channels'
    
    def __str__(self):
        return self.name

class Vendor(models.Model):
    """Supplier/vendor for purchasing items"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='vendors', null=True, blank=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True,null=True)
    email = models.EmailField(blank=True,null=True)
    address = models.TextField(blank=True,null=True)
    tax_id = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vendors'
        unique_together = ['company', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.company})"

class Customer(models.Model):
    """Customer for invoices"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='customers', null=True, blank=True)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True,null=True)
    email = models.EmailField(blank=True,null=True)
    address = models.TextField(blank=True,null=True)
    tax_id = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'customers'
    
    def __str__(self):
        return f"{self.name} ({self.company})"

class Product(models.Model):
    """Product/Item that can be purchased and sold"""
    PRODUCT_CATEGORIES = [
        ('SMARTPHONE', 'Smartphone'),
        ('ACCESSORY', 'Accessory'),
        ('TABLET', 'Tablet'),
        ('OTHER', 'Other'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    sku = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=PRODUCT_CATEGORIES)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'products'
        unique_together = ['company', 'sku']
    
    def __str__(self):
        return f"{self.sku} - {self.name} ({self.company})"
    
    @property
    def current_stock(self):
        """Calculate current stock quantity"""
        total_purchased = self.purchase_items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        
        total_sold = self.invoice_items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        
        return total_purchased - total_sold

class PurchaseOrder(models.Model):
    """Purchase order from vendors"""
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ORDERED', 'Ordered'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]

    PURCHASE_TYPE_CHOICES = [
        ('Credit', 'Credit'),
        ('Cash', 'Cash'),
        ('Check', 'Check'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='purchase_orders', null=True, blank=True)
    po_number = models.CharField(max_length=50)
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='purchase_orders')
    purchase_type = models.CharField(max_length=20, choices=PURCHASE_TYPE_CHOICES, default='Cash')
    order_date = models.DateField(default=timezone.now)
    vendor_invoice_number = models.CharField(max_length=100, blank=True)
    expected_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_include = models.BooleanField(default=True)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=7)  # Default 7% VAT
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    tax_sequence_number = models.CharField(max_length=100, blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'purchase_orders'
        unique_together = ['company', 'po_number']
        ordering = ['-order_date']
    
    def __str__(self):
        return f"PO-{self.po_number} ({self.company})"
    
    def calculate_totals(self):
        """Calculate order totals from items"""
        from .models import PurchaseItem
        items = PurchaseItem.objects.filter(purchase_order=self)
        self.subtotal = sum(item.total_price for item in items)
        # Assuming 7% VAT for Thailand
        if self.tax_include:
            self.tax_amount = self.subtotal - (self.subtotal / (1 + self.tax_percent / 100))
        else:
            self.tax_amount = self.subtotal * (self.tax_percent / 100)
        
        self.total_amount = self.subtotal + self.tax_amount
        self.save()
    
    def get_item_count(self):
        """Get item count without using reverse relation in property"""
        from .models import PurchaseItem
        return PurchaseItem.objects.filter(purchase_order=self).count()
    
    item_count = property(get_item_count)

class PurchaseItem(models.Model):
    """Individual items in a purchase order"""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='purchase_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)],default=1 )
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    remaining_quantity = models.PositiveIntegerField(default=0)  # Track unsold quantity
    
    class Meta:
        db_table = 'purchase_items'
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.quantity * self.unit_cost
        
        # Set remaining quantity on first save
        if not self.pk:
            self.remaining_quantity = self.quantity
        
        super().save(*args, **kwargs)
        # Update purchase order totals
        self.purchase_order.calculate_totals()
    
    @property
    def available_quantity(self):
        """Get available quantity for selling"""
        return self.remaining_quantity

class Invoice(models.Model):
    """Sales invoice to customers"""
    SELLING_CHANNELS = [
        ('OFFLINE', 'Offline Store'),
        ('TIKTOK', 'TikTok Shop'),
        ('SHOPEE', 'Shopee'),
        ('LAZADA', 'Lazada'),
    ]
    
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PAID', 'Paid'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invoices', null=True, blank=True)
    invoice_number = models.CharField(max_length=50)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    invoice_date = models.DateField(default=timezone.now)
    selling_channel = models.ForeignKey(SellingChannel, on_delete=models.PROTECT, default=1) # Default to 'OFFLINE'
    platform_order_id = models.CharField(max_length=100, blank=True)  # For online platforms
    platform_tracking_number = models.CharField(max_length=100, blank=True)  # For online platforms
    tax_sequence_number = models.CharField(max_length=100, blank=True, null=True)
    saleperson = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=7)  # Default 7% VAT
    tax_include = models.BooleanField(default=True)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'invoices'
        unique_together = ['company', 'invoice_number']
        ordering = ['-invoice_date']
    
    def __str__(self):
        return f"INV-{self.invoice_number} ({self.company})"
    
    def calculate_totals(self):
        """Calculate invoice totals from items"""
        from .models import InvoiceItem
        items = InvoiceItem.objects.filter(invoice=self)
        self.subtotal = sum(item.total_price for item in items)
        # 7% VAT for Thailand
        if self.tax_include:
            self.tax_amount = self.subtotal - (self.subtotal / (1 + self.tax_percent / 100))
        else:
            self.tax_amount = self.subtotal * (self.tax_percent / 100)

        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost
        self.save()
    
    def get_item_count(self):
        """Get item count without using reverse relation in property"""
        from .models import InvoiceItem
        return InvoiceItem.objects.filter(invoice=self).count()
    
    item_count = property(get_item_count)
    
    def get_profit_margin(self):
        """Calculate profit margin for this invoice"""
        from .models import InvoiceItem
        items = InvoiceItem.objects.filter(invoice=self)
        total_cost = sum(item.total_cost for item in items)
        return self.subtotal - total_cost
    
    profit_margin = property(get_profit_margin)

class InvoiceItem(models.Model):
    """Individual items in an invoice with purchase item tracking"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='invoice_items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    purchase_item = models.ForeignKey(PurchaseItem, on_delete=models.PROTECT, related_name='invoice_items')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    class Meta:
        db_table = 'invoice_items'
    
    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    
    def clean(self):
        """Validate that purchase item has enough quantity"""
        from django.core.exceptions import ValidationError
        
        if self.purchase_item and self.quantity > self.purchase_item.available_quantity:
            raise ValidationError(
                f"Not enough quantity available. Available: {self.purchase_item.available_quantity}, Requested: {self.quantity}"
            )
    
    def save(self, *args, **kwargs):
        # Calculate total price
        self.total_price = self.quantity * self.unit_price
        
        # Validate before saving
        self.clean()
        
        super().save(*args, **kwargs)
        
        # Update purchase item remaining quantity
        if self.purchase_item:
            self.purchase_item.remaining_quantity -= self.quantity
            self.purchase_item.save()
        
        # Update invoice totals
        self.invoice.calculate_totals()
    
    @property
    def unit_cost(self):
        """Get cost from the linked purchase item"""
        return self.purchase_item.unit_cost
    
    @property
    def total_cost(self):
        return self.quantity * self.unit_cost
    
    @property
    def profit(self):
        return self.total_price - self.total_cost
    
    @property
    def profit_margin_percentage(self):
        """Calculate profit margin percentage"""
        if self.total_price > 0:
            return (self.profit / self.total_price) * 100
        return 0

class Transaction(models.Model):
    """Other income/expense transactions"""
    TRANSACTION_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    ]
    
    CATEGORY_CHOICES = [
        ('REPAIR_SERVICE', 'Phone Repair Service'),
        ('DELIVERY', 'Delivery Service'),
        ('SALARY', 'Salary'),
        ('RENT', 'Rent'),
        ('UTILITY', 'Utility'),
        ('MARKETING', 'Marketing'),
        ('OTHER', 'Other'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transactions', null=True, blank=True)
    transaction_number = models.CharField(max_length=50)
    transaction_date = models.DateField(default=timezone.now)
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    description = models.TextField()
    reference = models.CharField(max_length=100, blank=True)  # For external reference
    created_by = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'transactions'
        unique_together = ['company', 'transaction_number']
        ordering = ['-transaction_date']
    
    def __str__(self):
        return f"{self.transaction_number} - {self.description} ({self.company})"
    
    @property
    def signed_amount(self):
        """Return positive for income, negative for expense"""
        return self.amount if self.type == 'INCOME' else -self.amount

class CSVImportLog(models.Model):
    """Track CSV imports for online platforms"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='csv_import_logs', null=True, blank=True)
    selling_channel = models.ForeignKey(SellingChannel, on_delete=models.PROTECT, default=1) # Default to 'OFFLINE'
    file_name = models.CharField(max_length=255)
    records_processed = models.PositiveIntegerField(default=0)
    records_imported = models.PositiveIntegerField(default=0)
    errors = models.TextField(blank=True)
    imported_by = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'csv_import_logs'
        ordering = ['-imported_at']
    
    def __str__(self):
        return f"{self.selling_channel} import - {self.imported_at} ({self.company})"
