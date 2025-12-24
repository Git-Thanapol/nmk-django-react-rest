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

    # --- Invoices ---
    path('invoices/', views.invoice_view, name='invoice_list'),
    path('invoices/edit/<int:pk>/', views.invoice_view, name='invoice_edit'),
    path('invoice/<int:pk>/pdf/', views.invoice_pdf_view, name='invoice_pdf'),

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

    # --- Imports & Mapping ---
    path('import/platforms/', views.platform_import_view, name='platform_import'),
    path('product_mapping/', views.product_mapping_view, name='product_mapping'),
    path('product_mapping/edit/<int:pk>/', views.product_mapping_view, name='product_mapping_edit'),

    # --- Help & Reports ---
    path('help/', views.help, name='help'),
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
]

# --- Media Files Configuration (For serving PDF in DEBUG mode) ---
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)