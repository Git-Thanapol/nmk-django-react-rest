from django.contrib import admin
import pandas as pd
import os
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

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
    CSVImportLog,
    ProductAlias
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
    list_display = ['sku', 'name', 'category', 'company', 'selling_price', 'is_active']
    search_fields = ['sku', 'name']
    list_filter = ['category', 'company']
    
    # --- 1. Add Custom URL for the Import Action ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-master-csv/', self.admin_site.admin_view(self.import_master_csv), name='product_import_master_csv'),
        ]
        return custom_urls + urls

    # --- 2. The Logic to Import CSV ---
    def import_master_csv(self, request):
        # A. Find the file path
        # Assuming your file is at: project_root/static/master_products.csv
        file_path = os.path.join(settings.BASE_DIR, 'static', 'master_products.csv')

        if not os.path.exists(file_path):
            self.message_user(request, f"Error: File not found at {file_path}", level=messages.ERROR)
            return HttpResponseRedirect("../")

        try:
            # B. Read CSV
            df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)
            
            # Check columns
            if 'รหัสรุ่น' not in df.columns or 'รหัสชื่อสินค้า' not in df.columns:
                 self.message_user(request, "Error: CSV must have columns 'รหัสรุ่น' and 'รหัสชื่อสินค้า'", level=messages.ERROR)
                 return HttpResponseRedirect("../")

            success_count = 0
            
            # C. Loop and Save
            for _, row in df.iterrows():
                sku = str(row['รหัสรุ่น']).strip()
                name = str(row['รหัสชื่อสินค้า']).strip()
                
                if not sku: continue

                # Determine Category (Simple logic: if 'IPHONE' in name, it's a Smartphone)
                category = 'SMARTPHONE'
                if 'IPHONE' in name.upper() or 'SAMSUNG' in name.upper():
                    category = 'SMARTPHONE'
                
                # Update or Create
                # Note: We set company=None for "Master Data" (Global Products)
                Product.objects.update_or_create(
                    sku=sku,
                    company=None,  # Or set a specific Company ID if required
                    defaults={
                        'name': name,
                        'category': category,
                        'description': name,
                        'is_active': True
                    }
                )
                success_count += 1

            self.message_user(request, f"Successfully imported {success_count} master products.", level=messages.SUCCESS)

        except Exception as e:
            self.message_user(request, f"Import Failed: {str(e)}", level=messages.ERROR)

        # Redirect back to the product list
        return HttpResponseRedirect("../")

    # --- 3. Add the Button to the Admin Template ---
    # We override the existing change_list_template block to inject our button
    change_list_template = "admin/product_change_list.html"

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

@admin.register(ProductAlias)
class ProductAliasAdmin(admin.ModelAdmin):
    list_display = ['external_key', 'platform', 'product', 'created_at']
    search_fields = ['external_key', 'product__sku', 'product__name']
    list_filter = ['platform']

    # --- 1. Custom URL ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-mapping-csv/', self.admin_site.admin_view(self.import_mapping_csv), name='product_alias_import_csv'),
        ]
        return custom_urls + urls

    # --- 2. Import Logic ---
    def import_mapping_csv(self, request):
        file_path = os.path.join(settings.BASE_DIR, 'static', 'product_mapping.csv')

        if not os.path.exists(file_path):
            self.message_user(request, f"Error: File not found at {file_path}", level=messages.ERROR)
            return HttpResponseRedirect("../")

        try:
            # Read CSV
            df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)
            
            # Check required columns
            required_cols = ['external_key', 'platform', 'product_sku']
            if not all(col in df.columns for col in required_cols):
                 self.message_user(request, f"Error: CSV must have columns {required_cols}", level=messages.ERROR)
                 return HttpResponseRedirect("../")

            success_count = 0
            skipped_count = 0
            
            for _, row in df.iterrows():
                external_key = str(row['external_key']).strip()
                target_sku = str(row['product_sku']).strip()
                platform = str(row['platform']).strip().upper() # Ensure uppercase (TIKTOK, SHOPEE)

                if not external_key or not target_sku:
                    continue

                # A. Find the System Product
                # We need the real Product Object to link the Foreign Key
                try:
                    product_obj = Product.objects.get(sku=target_sku)
                except Product.DoesNotExist:
                    # If SKU doesn't exist in our master DB, we can't map it.
                    skipped_count += 1
                    continue

                # B. Create Alias
                ProductAlias.objects.update_or_create(
                    external_key=external_key,
                    defaults={
                        'product': product_obj,
                        'platform': platform
                    }
                )
                success_count += 1

            self.message_user(request, f"Imported {success_count} mappings. Skipped {skipped_count} (SKU not found).", level=messages.SUCCESS)

        except Exception as e:
            self.message_user(request, f"Critical Import Error: {str(e)}", level=messages.ERROR)

        return HttpResponseRedirect("../")

    # --- 3. Link to Template ---
    change_list_template = "admin/product_alias_change_list.html"