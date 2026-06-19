from django.urls import path
from . import views
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

    # --- Standard Paths ---
    # path('admin/', admin.site.urls, name='admin_home'),
    path('notes/', views.NoteListCreateView.as_view(), name='note_list_create'),
    path('notes/<int:pk>/', views.NoteDeleteView.as_view(), name='note_delete'),

    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # --- Purchases ---
    path('purchases/', views.purchase_order_view, name='purchase_list'),
    path('purchases/edit/<int:pk>/', views.purchase_order_view, name='purchase_edit'),
    path('api/purchases/check-duplicate/', views.check_duplicate_po_fields, name='api_check_duplicate_po'),

    # --- Invoices ---
    path('invoices/', views.invoice_view, name='invoice_list'),
    path('invoices/edit/<int:pk>/', views.invoice_view, name='invoice_edit'),
    path('invoice/<int:pk>/pdf/', views.invoice_pdf_view, name='invoice_pdf'),
    path('invoice/<int:pk>/excel/', views.invoice_excel_view, name='invoice_excel'),
    path('invoice/sync-google-sheet/', views.sync_google_sheet_requests, name='invoice_sync_google_sheet'),

    # --- Vendors ---
    path('vendors/', views.vendor_view, name='vendor_list'),
    path('vendors/edit/<int:pk>/', views.vendor_view, name='vendor_edit'),

    # --- Products ---
    path('products/', views.product_view, name='product_list'),
    path('products/edit/<int:pk>/', views.product_view, name='product_edit'),

    # --- Transactions ---
    path('transaction_form/', views.transaction_form, name='transaction_form'),
    path('transactions/', views.transaction_view, name='transaction_list'),
    path('transactions/edit/<int:pk>/', views.transaction_view, name='transaction_edit'),
    path('transactions/attachment/<int:pk>/delete/', views.transaction_attachment_delete, name='transaction_attachment_delete'),

    # --- Imports & Mapping ---
    path('import/platforms/', views.platform_import_view, name='platform_import'),
    path('product_mapping/', views.product_mapping_view, name='product_mapping'),
    path('product_mapping/edit/<int:pk>/', views.product_mapping_view, name='product_mapping_edit'),
    path('api/product-mapping/suggest/', views.product_mapping_suggest_view, name='product_mapping_suggest'),

    # --- Global Search ---
    path('api/search/', views.global_search_view, name='global_search'),

    # --- Bug / Feature Reports ---
    path('bug-reports/', views.bug_report_list, name='bug_report_list'),
    path('bug-reports/<int:pk>/', views.bug_report_detail, name='bug_report_detail'),
    path('bug-reports/<int:pk>/status/', views.bug_report_update_status, name='bug_report_status'),
    path('bug-reports/chat/', views.bug_report_chat, name='bug_report_chat'),
    path('bug-reports/upload-image/', views.bug_report_upload_image, name='bug_report_upload_image'),
    path('bug-reports/submit/', views.bug_report_submit, name='bug_report_submit'),

    # --- Dashboard ---
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/api/kpi-summary/', views.dashboard_kpi_summary, name='dashboard_kpi_summary'),
    path('dashboard/api/sales-trend/', views.dashboard_sales_trend, name='dashboard_sales_trend'),
    path('dashboard/api/top-skus/', views.dashboard_top_skus, name='dashboard_top_skus'),
    path('dashboard/api/purchase-vs-sales/', views.dashboard_purchase_vs_sales, name='dashboard_purchase_vs_sales'),
    path('dashboard/api/stock-alerts/', views.dashboard_stock_alerts, name='dashboard_stock_alerts'),

    # --- Help & Reports ---
    path('help/', views.help, name='help'),
    path('api/help/ask/', views.help_ask_view, name='help_ask'),
    path('reports/', views.report_dashboard_view, name='reports'),

    # --- Companies ---
    path('companies/', views.company_list_view, name='company_list'),
    path('companies/add/', views.company_create_view, name='company_create'),
    path('companies/<int:pk>/edit/', views.company_edit_view, name='company_edit'),

    # --- FIXED: 50 Tawi Path ---
    # Changed from include('...') to direct view reference
    path('tax/50tawi/', views.wht_cert_list_view, name='wht_list'),

    # --- API ---
    path('api/get-source-details/', views.get_source_details, name='api_get_source_details'),
    
    # --- VAT Tracking (Django View + API) ---
    path('vat-tracking/', views.vat_tracking_view, name='vat_tracking'),
    path('vat-buy-summary/', views.vat_buy_summary_view, name='vat_buy_summary'),
    path('api/vat/import/', views.VatImportDataView.as_view(), name='api_vat_import'),
    path('api/vat/report/', views.VatReportView.as_view(), name='api_vat_report'),
    path('api/vat/export/', views.VatExportExcelView.as_view(), name='api_vat_export'),
    path('api/vat/buy-orders/export/', views.VatBuySummaryExportExcelView.as_view(), name='api_vat_buy_orders_export'),
    path('api/vat/buy-orders/', views.VatBuyOrderSummaryView.as_view(), name='api_vat_buy_orders'),
    path('api/vat/buy-orders/<int:pk>/items/', views.VatBuyOrderDetailView.as_view(), name='api_vat_buy_order_items'),
]

# --- Media Files Configuration (For serving PDF in DEBUG mode) ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
