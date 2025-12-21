from django.contrib import admin

# Register your models here.
from .models import (
    Company,
    SellingChannel,
    Vendor,
    #Customer,
    Product,
    PurchaseOrder,
    PurchaseItem,
    Invoice,
    InvoiceItem,
    Transaction,
    CSVImportLog
)


admin.site.site_header = "WebApp Administration"
admin.site.site_title = "WebApp Admin Portal"   
admin.site.index_title = "Welcome to WebApp Admin"



@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'tax_id', 'phone', 'email', 'is_active']
    search_fields = ['name', 'tax_id']
    list_filter = ['is_active']

@admin.register(SellingChannel)
class SellingChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active']
    search_fields = ['name', 'code']
    list_filter = ['is_active']

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'company', 'contact_person', 'phone', 'email', 'is_active']
    search_fields = ['name', 'contact_person']
    list_filter = ['company', 'is_active']

# @admin.register(Customer)
# class CustomerAdmin(admin.ModelAdmin):
#     list_display = ['name', 'company', 'phone', 'email', 'is_active']
#     search_fields = ['name', 'phone', 'email']
#     list_filter = ['company', 'is_active']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['sku', 'name', 'company', 'category', 'cost_price', 'selling_price', 'is_active']
    search_fields = ['sku', 'name']
    list_filter = ['company', 'category', 'is_active']

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['vendor_invoice_number','tax_sequence_number', 'po_number', 'company', 'vendor', 'order_date', 'status', 'total_amount', 'purchase_type']
    search_fields = ['po_number', 'vendor__name','vendor_invoice_number','tax_sequence_number']
    list_filter = ['company', 'status', 'order_date']
    date_hierarchy = 'order_date'

@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ['purchase_order', 'product', 'quantity', 'unit_cost', 'total_price', 'remaining_quantity']
    search_fields = ['purchase_order__po_number', 'product__name']
    list_filter = ['purchase_order__status']

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'company', 'vendor', 'invoice_date', 'platform_name', 'status', 'grand_total','tax_sequence_number','platform_tracking_number','platform_order_id','saleperson']
    search_fields = ['tax_sequence_number','platform_tracking_number','platform_order_id','invoice_number', 'vendor__name']
    list_filter = ['company', 'platform_name', 'status', 'invoice_date']
    date_hierarchy = 'invoice_date'

@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ['invoice', 'product', 'quantity', 'unit_price', 'total_price']
    search_fields = ['invoice__invoice_number', 'product__name']
    list_filter = ['invoice__status']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_number', 'company', 'transaction_date', 'type', 'category', 'amount']
    search_fields = ['transaction_number', 'description']
    list_filter = ['company', 'type', 'category', 'transaction_date']
    date_hierarchy = 'transaction_date'

@admin.register(CSVImportLog)
class CSVImportLogAdmin(admin.ModelAdmin):
    list_display = ['company', 'selling_channel', 'file_name', 'records_processed', 'records_imported', 'imported_at']
    search_fields = ['file_name']
    list_filter = ['company', 'selling_channel', 'imported_at']
    date_hierarchy = 'imported_at'
