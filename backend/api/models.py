from django.db import models
from django.contrib.auth.models import User

from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
from django.db import migrations, models
from django.db.models import Sum
from django.db.models.functions import Coalesce


DATE_INPUT_FORMATS = ['%d-%m-%Y']

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
    """Multi-company support (Our Operating Companies)"""
    name = models.CharField(max_length=200, verbose_name="ชื่อบริษัท")
    nick_name = models.CharField(max_length=100, blank=True, verbose_name="ชื่อย่อ")
    tax_id = models.CharField(max_length=20, blank=True, null=True, verbose_name="เลขผู้เสียภาษี")
    address = models.TextField(blank=True, null=True, verbose_name="ที่อยู่")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="เบอร์โทร")
    email = models.EmailField(blank=True, null=True, verbose_name="อีเมล")
    is_active = models.BooleanField(default=True, verbose_name="สถานะใช้งาน")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'companies'
        verbose_name_plural = 'Companies'
        ordering = ['-is_active', 'name']
    
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

# class Customer(models.Model):
#     """Customer for invoices"""
#     company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='customers', null=True, blank=True)
#     name = models.CharField(max_length=200)
#     phone = models.CharField(max_length=20, blank=True,null=True)
#     email = models.EmailField(blank=True,null=True)
#     address = models.TextField(blank=True,null=True)
#     tax_id = models.CharField(max_length=20, blank=True, null=True)
#     is_active = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         db_table = 'customers'
    
#     def __str__(self):
#         return f"{self.name} ({self.company})"

class Product(models.Model):
    """Product/Item that can be purchased and sold (Your Master Data)"""
    PRODUCT_CATEGORIES = [
        ('SMARTPHONE', 'Smartphone'),
        ('ACCESSORY', 'Accessory'),
        ('TABLET', 'Tablet'),
        ('OTHER', 'Other'),
    ]
    
    # --- Your existing columns ---
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    sku = models.CharField(max_length=50)
    name = models.CharField(max_length=200) # The clean "Master Name"
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)
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
        """
        Calculate current stock: Total Purchased - Total Sold.
        Uses Coalesce ensures we get 0 instead of None if no records exist.
        """
        # Note: We use 'purchase_items' and 'invoice_items' here. 
        # This requires related_name to be set in the child models (see below).
        total_in = self.purchase_items.aggregate(
            total=Coalesce(Sum('quantity'), 0)
        )['total']
        
        total_out = self.invoice_items.aggregate(
            total=Coalesce(Sum('quantity'), 0)
        )['total']
        
        return total_in - total_out

class PurchaseOrder(models.Model):
    """Purchase order from vendors"""
    STATUS_CHOICES = [
        ('DRAFT', 'แบบร่าง'),
        ('PAID', 'ชำระเงินแล้ว'),
        ('CANCELLED', 'ยกเลิก'),
    ]

    PURCHASE_TYPE_CHOICES = [
        ('Credit', 'เครดิต'),
        ('Cash', 'เงินสด'),
        ('Check', 'เงินเช็ค'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='purchase_orders')
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

    tax_sender_date = models.DateField(null=True, blank=True)
    tax_sequence_number = models.CharField(max_length=100, blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    
    
    class Meta:
        db_table = 'purchase_orders'
        #unique_together = ['company', 'po_number'] # Changed 12-12-2025 Allow duplicate PO numbers for testing
        ordering = ['-order_date']
    
    def __str__(self):
        return f"{self.po_number} ({self.company})"
    
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
    product = models.ForeignKey(Product, on_delete=models.PROTECT,related_name='purchase_items')
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
    """Sales Invoice with platform integration fields"""
    STATUS_CHOICES = [
        ('DRAFT', 'แบบร่าง'),
        ('BILLED', 'ออกใบกำกับภาษีแล้ว'),
        ('CANCELLED', 'ยกเลิก'),
    ]
    
    # Identifiers
    invoice_number = models.CharField(max_length=50) # Unique per company
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='invoices')    
    
    # Customer - Nullable for high volume platform imports
    vendor = models.ForeignKey('Vendor', on_delete=models.PROTECT, related_name='invoices', null=True, blank=True)
    
    invoice_date = models.DateField(default=timezone.now)      
    
    tax_sender_date = models.DateField(null=True, blank=True)
    tax_sequence_number = models.CharField(max_length=100, blank=True, null=True)
    saleperson = models.CharField(max_length=100, blank=True)
    #status = models.CharField(max_length=100, default='DRAFT') 
    status = models.CharField(choices=STATUS_CHOICES, default='DRAFT')

    # Financials
    tax_include = models.BooleanField(default=True)
    tax_percent = models.DecimalField(max_digits=5, decimal_places=2, default=7)  
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)    

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)    
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Renamed from total_amount
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Platform Fields
    platform_name = models.CharField(max_length=100, blank=True) 
    platform_order_id = models.CharField(max_length=100, blank=True) 
    platform_order_status = models.CharField(max_length=100, blank=True) 
    platform_tracking_number = models.CharField(max_length=100, blank=True) 
    recipient_name = models.CharField(max_length=200, blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    recipient_address = models.TextField(blank=True)
    warehouse_name = models.CharField(max_length=100, blank=True) 
    
    class Meta:
        db_table = 'invoices'
        unique_together = ['company', 'invoice_number']
        ordering = ['-invoice_date']
    
    def __str__(self):
        return f"{self.invoice_number} ({self.company})"
    
    def calculate_totals(self):
        """
        Standard calculation logic for MANUAL inputs.
        Import logic bypasses this.
        """
        from .models import InvoiceItem
        items = InvoiceItem.objects.filter(invoice=self)
        self.subtotal = sum(item.total_price for item in items)

        if self.tax_include:
            # Reverse Calc: Tax = Subtotal - (Subtotal / 1.07)
            self.tax_amount = self.subtotal - (self.subtotal / (1 + self.tax_percent / 100))
        else:
            # Forward Calc
            self.tax_amount = self.subtotal * (self.tax_percent / 100)

        # Logic for manual input: Grand Total = Subtotal + Tax (if excluded) + Shipping
        # If included, Subtotal already has tax, so we just add shipping? 
        # Usually for manual entry:
        if self.tax_include:
             # Subtotal acts as the base with tax, we just add shipping
            self.grand_total = self.subtotal + self.shipping_cost - self.discount_amount
        else:
            self.grand_total = self.subtotal + self.tax_amount + self.shipping_cost - self.discount_amount
            
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
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True, related_name='invoice_items')
    purchase_item = models.ForeignKey(PurchaseItem, on_delete=models.PROTECT, related_name='invoice_items', null=True, blank=True)

    sku = models.CharField(max_length=100, blank=True)  # Store platform SKU/name for reference
    item_name = models.TextField(blank=True)    
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
        # 1. Ensure total_price is set (vital for manual saves)
        self.total_price = self.quantity * self.unit_price
        
        # 2. Validate
        self.clean()
        
        # 3. STOCK LOGIC WARNING: 
        # Ideally, move stock deduction to a Signal or Service. 
        # Kept here as requested, but added a check to prevent crash if purchase_item is None.

        ##Temporarily disabled to prevent stock issues during testing
        # if self.pk is None and self.purchase_item:
        #     # Only deduct on CREATE (pk is None), not on every update.
        #     # This prevents double-deduction on simple edits, though it prevents 
        #     # adjusting stock if you change quantity later.
        #     self.purchase_item.remaining_quantity -= self.quantity
        #     self.purchase_item.save()

        super().save(*args, **kwargs)
        
        # 4. Trigger Parent Update
        self.invoice.calculate_totals()

    # --- SAFE PROPERTIES ---
    @property
    def unit_cost(self):
        if self.purchase_item:
            return self.purchase_item.unit_cost
        return 0 # Or Decimal(0)

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost

    @property
    def profit(self):
        return self.total_price - self.total_cost

    @property
    def profit_margin_percentage(self):
        if self.total_price > 0:
            return (self.profit / self.total_price) * 100
        return 0

class Transaction(models.Model):
    """Other income/expense transactions"""
    TRANSACTION_TYPES = [
        ('INCOME', 'รายรับ'),
        ('EXPENSE', 'รายจ่าย'),
    ]
    
    CATEGORY_CHOICES = [
        ('REPAIR_SERVICE', 'ค่าซ่อมบริการ'),
        ('DELIVERY', 'ค่าส่งสินค้า'),
        ('SALARY', 'เงินเดือนพนักงาน'),
        ('RENT', 'ค่าเช่า'),
        ('UTILITY', 'ค่าสาธารณูปโภค'),
        ('MARKETING', 'ค่าโฆษณา'),
        ('OTHER', 'อื่นๆ'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='transactions')
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='transactions', null=True, blank=True) 
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

class ProductMapping(models.Model):
    """
    Maps external platform names to internal Products.
    Example: "Airpods 4/07 (ANC)" -> Product ID 1 (AirPods 4)
    """
    PLATFORMS = [
        ('SHOPEE', 'Shopee'),
        ('LAZADA', 'Lazada'),
        ('TIKTOK', 'TikTok'),
        ('OTHER', 'Other'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='mappings')
    platform_name = models.CharField(max_length=500, db_index=True) # The messy name from Shopee/Lazada

    platform = models.CharField(max_length=20, choices=PLATFORMS, default='OTHER')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'product_mappings'
        # Ensure one platform name doesn't map to multiple internal products
        unique_together = ['platform_name', 'platform'] 

    def __str__(self):
        return f"{self.platform}: {self.platform_name} -> {self.product.sku}"

class ProductAlias(models.Model):
    """
    Maps external platform names/SKUs to internal Django Products.
    """
    # The string we receive from the CSV (e.g., "iPhone 15 Black" or "TT-SKU-001")

    PLATFORMS = [
        ('SHOPEE', 'Shopee'),
        ('LAZADA', 'Lazada'),
        ('TIKTOK', 'TikTok'),
        ('OTHER', 'Other'),
    ]

    external_key = models.CharField(max_length=255, db_index=True) 
    
    # The actual product in your warehouse
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='aliases')
    platform = models.CharField(max_length=20, choices=PLATFORMS, default='OTHER')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevent duplicate mappings for the same external string
        unique_together = ['external_key'] 
        verbose_name_plural = "Product Aliases"

    def __str__(self):
        return f"{self.external_key} -> {self.product.name}"
