import pandas as pd
import os
from django.contrib import admin
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.conf import settings
from django.utils.html import format_html
from django.db.models import Sum

# Import your models
from .models import (
    Note, Company, SellingChannel, Vendor, Product, 
    PurchaseOrder, PurchaseItem, Invoice, InvoiceItem, 
    Transaction, CSVImportLog, ProductAlias, ImportLog, WithholdingTaxCert
)

# --- 1. SETTINGS & STYLING ---
admin.site.site_header = "NMK Admin System"
admin.site.site_title = "NMK Portal"
admin.site.index_title = "ยินดีต้อนรับสู่ระบบจัดการ"

# --- 2. INLINES (รายการย่อยในบิล) ---

class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 1
    fields = ['product', 'quantity', 'unit_cost', 'total_price', 'remaining_quantity']
    readonly_fields = ['total_price']
    verbose_name = "รายการสินค้า"
    verbose_name_plural = "รายการสินค้าในบิล"

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ['product', 'sku', 'item_name', 'quantity', 'unit_price', 'total_price']
    readonly_fields = ['total_price']
    verbose_name = "รายการสินค้า"
    verbose_name_plural = "รายการสินค้าในบิล"

# --- 3. ADMIN CLASSES ---

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['title', 'get_user', 'created_at_thai']
    search_fields = ['title', 'content']

    def get_user(self, obj): return obj.user.username
    get_user.short_description = 'ผู้เขียน'

    def created_at_thai(self, obj): return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_thai.short_description = 'สร้างเมื่อ'

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'nick_name', 'tax_id', 'phone', 'is_active']
    search_fields = ['name', 'tax_id']
    list_filter = ['is_active']

@admin.register(SellingChannel)
class SellingChannelAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'description', 'is_active']

@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'company', 'is_active']
    search_fields = ['name', 'phone']
    list_filter = ['company']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'sku', 'name', 'category_thai', 'company', 
        'cost_price_th', 'selling_price_th', 'stock_show', 'is_active'
    ]
    search_fields = ['sku', 'name']
    list_filter = ['category', 'company', 'is_active']
    readonly_fields = ['current_stock']
    
    # --- Custom Headers (Thai) ---
    def category_thai(self, obj): return obj.category if obj.category else "-"
    category_thai.short_description = 'หมวดหมู่'

    def cost_price_th(self, obj): return f"{obj.cost_price:,.2f}"
    cost_price_th.short_description = 'ราคาทุน'

    def selling_price_th(self, obj): return f"{obj.selling_price:,.2f}"
    selling_price_th.short_description = 'ราคาขาย'

    def stock_show(self, obj): 
        stock = obj.current_stock
        color = "green" if stock > 0 else "red"
        return format_html(f'<span style="color: {color}; font-weight: bold;">{stock}</span>')
    stock_show.short_description = 'คงเหลือ'

    # --- Import Logic ---
    change_list_template = "admin/product_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-master-csv/', self.admin_site.admin_view(self.import_master_csv), name='product_import_master_csv'),
        ]
        return custom_urls + urls

    def import_master_csv(self, request):
        file_path = os.path.join(settings.BASE_DIR, 'static', 'master_products.csv')
        if not os.path.exists(file_path):
            self.message_user(request, f"ไม่พบไฟล์: {file_path}", level=messages.ERROR)
            return HttpResponseRedirect("../")

        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)
            if 'รหัสรุ่น' not in df.columns or 'รหัสชื่อสินค้า' not in df.columns:
                 self.message_user(request, "ไฟล์ CSV ต้องมีคอลัมน์ 'รหัสรุ่น' และ 'รหัสชื่อสินค้า'", level=messages.ERROR)
                 return HttpResponseRedirect("../")

            count = 0
            for _, row in df.iterrows():
                sku = str(row['รหัสรุ่น']).strip()
                name = str(row['รหัสชื่อสินค้า']).strip()
                if not sku: continue
                
                cat = 'OTHER'
                if 'IPHONE' in name.upper() or 'SAMSUNG' in name.upper(): cat = 'SMARTPHONE'
                elif 'IPAD' in name.upper(): cat = 'TABLET'

                Product.objects.update_or_create(
                    sku=sku,
                    company=None, 
                    defaults={'name': name, 'category': cat, 'is_active': True}
                )
                count += 1
            self.message_user(request, f"นำเข้าข้อมูลสำเร็จ {count} รายการ", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"เกิดข้อผิดพลาด: {str(e)}", level=messages.ERROR)
        return HttpResponseRedirect("../")

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number', 'vendor', 'order_date_th', 'status_th', 'total_amount_th', 'created_by']
    list_filter = ['status', 'order_date', 'company']
    search_fields = ['po_number', 'vendor__name']
    inlines = [PurchaseItemInline]

    def order_date_th(self, obj): return obj.order_date.strftime('%d/%m/%Y')
    order_date_th.short_description = 'วันที่สั่งซื้อ'

    def status_th(self, obj): return obj.get_status_display()
    status_th.short_description = 'สถานะ'

    def total_amount_th(self, obj): return f"{obj.total_amount:,.2f}"
    total_amount_th.short_description = 'ยอดรวมสุทธิ'

    # ... existing code ...
    actions = ['create_50_tawi']

    def create_50_tawi(self, request, queryset):
        count = 0
        for po in queryset:
            # Only creating for PAID status usually
            if po.status != 'PAID': 
                continue 
            
            # Check if exists
            if hasattr(po, 'wht_cert'):
                continue
                
            # Create logic
            WithholdingTaxCert.objects.create(
                company=po.company,
                vendor=po.vendor,
                purchase_order=po,
                amount_before_tax=po.subtotal,
                tax_amount=po.tax_amount, # Assuming this field tracks the WHT amount in your PO logic
                created_by=request.user
            )
            count += 1
        self.message_user(request, f"Created {count} WHT Certificates.")
    create_50_tawi.short_description = "📝 Generate 50 Tawi for selected POs"

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'platform_name', 'invoice_date_th', 'status', 'grand_total_th', 'item_count']
    list_filter = ['status', 'invoice_date', 'platform_name']
    search_fields = ['invoice_number', 'platform_order_id', 'recipient_name']
    inlines = [InvoiceItemInline]
    readonly_fields = ['tax_amount', 'subtotal', 'grand_total']

    def invoice_date_th(self, obj): return obj.invoice_date.strftime('%d/%m/%Y')
    invoice_date_th.short_description = 'วันที่'

    def grand_total_th(self, obj): return f"{obj.grand_total:,.2f}"
    grand_total_th.short_description = 'ยอดสุทธิ'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_number', 'transaction_date', 'type_th', 'category_th', 'amount_th', 'description']
    list_filter = ['type', 'category', 'transaction_date']
    search_fields = ['transaction_number', 'description']

    def type_th(self, obj): 
        color = "green" if obj.type == 'INCOME' else "red"
        label = "รายรับ" if obj.type == 'INCOME' else "รายจ่าย"
        return format_html(f'<span style="color:{color}">{label}</span>')
    type_th.short_description = 'ประเภท'

    def category_th(self, obj): return obj.get_category_display()
    category_th.short_description = 'หมวดหมู่'

    def amount_th(self, obj): return f"{obj.amount:,.2f}"
    amount_th.short_description = 'จำนวนเงิน'

@admin.register(ProductAlias)
class ProductAliasAdmin(admin.ModelAdmin):
    list_display = ['external_key', 'platform', 'product_link', 'created_at']
    search_fields = ['external_key', 'product__sku', 'product__name']
    list_filter = ['platform']

    def product_link(self, obj):
        return f"{obj.product.sku} - {obj.product.name}"
    product_link.short_description = 'สินค้าในระบบ (Internal)'

    # --- Import Logic ---
    change_list_template = "admin/product_alias_change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-mapping-csv/', self.admin_site.admin_view(self.import_mapping_csv), name='product_alias_import_csv'),
        ]
        return custom_urls + urls

    def import_mapping_csv(self, request):
        file_path = os.path.join(settings.BASE_DIR, 'static', 'product_mapping.csv')
        if not os.path.exists(file_path):
            self.message_user(request, f"ไม่พบไฟล์: {file_path}", level=messages.ERROR)
            return HttpResponseRedirect("../")

        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)
            req_cols = ['external_key', 'platform', 'product_sku']
            if not all(col in df.columns for col in req_cols):
                 self.message_user(request, f"CSV ต้องมีคอลัมน์ {req_cols}", level=messages.ERROR)
                 return HttpResponseRedirect("../")

            success, skipped = 0, 0
            for _, row in df.iterrows():
                ext_key = str(row['external_key']).strip()
                p_sku = str(row['product_sku']).strip()
                platform = str(row['platform']).strip().upper()

                if not ext_key or not p_sku: continue

                try:
                    product_obj = Product.objects.get(sku=p_sku)
                    ProductAlias.objects.update_or_create(
                        external_key=ext_key,
                        defaults={'product': product_obj, 'platform': platform}
                    )
                    success += 1
                except Product.DoesNotExist:
                    skipped += 1

            self.message_user(request, f"นำเข้าสำเร็จ {success} รายการ (ข้าม {skipped} เนื่องจากไม่พบ SKU)", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"เกิดข้อผิดพลาด: {str(e)}", level=messages.ERROR)

        return HttpResponseRedirect("../")

@admin.register(ImportLog)
class ImportLogAdmin(admin.ModelAdmin):
    list_display = ['created_at_th', 'platform', 'filename', 'status_th', 'stats_display', 'error_file']
    list_filter = ['status', 'platform']
    
    def created_at_th(self, obj): return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_th.short_description = 'เวลา'

    def status_th(self, obj): 
        colors = {
            'PENDING': 'orange', 'PROCESSING': 'blue', 
            'COMPLETED': 'green', 'FAILED': 'red', 'COMPLETED_WITH_ERRORS': 'darkred'
        }
        return format_html(f'<span style="color:{colors.get(obj.status, "black")}">{obj.get_status_display()}</span>')
    status_th.short_description = 'สถานะ'

    def stats_display(self, obj):
        return f"OK: {obj.success_count} / Fail: {obj.failed_count}"
    stats_display.short_description = 'ผลลัพธ์'

@admin.register(CSVImportLog)
class CSVImportLogAdmin(admin.ModelAdmin):
    list_display = ['imported_at', 'company', 'selling_channel', 'file_name', 'records_imported']
    list_filter = ['selling_channel']


@admin.register(WithholdingTaxCert)
class WithholdingTaxCertAdmin(admin.ModelAdmin):
    list_display = ['cert_number', 'vendor', 'date_issued', 'amount_before_tax', 'tax_amount', 'download_pdf']
    list_filter = ['date_issued', 'company']
    
    def download_pdf(self, obj):
        if obj.pdf_file:
            return format_html(f'<a href="{obj.pdf_file.url}" target="_blank" class="button">📄 Download PDF</a>')
        return "-"
    download_pdf.short_description = "PDF"

    # Action to regenerate PDF if data changes
    actions = ['regenerate_pdf']
    
    def regenerate_pdf(self, request, queryset):
        from .utils_pdf import generate_wht_pdf
        for cert in queryset:
            generate_wht_pdf(cert)
        self.message_user(request, "Regenerated PDFs successfully.")
    regenerate_pdf.short_description = "🔄 Re-generate PDF for selected"