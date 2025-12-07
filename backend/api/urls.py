from django.urls import path
from . import views
from django.contrib import admin

urlpatterns = [

    path('admin/', admin.site.urls, name='admin_home'),
    #path('api/user/register/', CreateUserView.as_view(), name='create_user'),
    path('notes/', views.NoteListCreateView.as_view(), name='note_list_create'),
    path('notes/<int:pk>/', views.NoteDeleteView.as_view(), name='note_delete'),

    #path('', views.home, name='home'),
    path('', views.login_view, name='login'),

    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    #path('purchase_form/', views.purchase_form, name='purchase_form'),
    path('purchases/', views.purchase_order_view, name='purchase_list'),
    path('purchases/edit/<int:pk>/', views.purchase_order_view, name='purchase_edit'),

    # Customer Management
    path('customer_list/', views.customer_list, name='customer_list'),
    path('customers/', views.customer_view, name='customer_list'),
    path('customers/edit/<int:pk>/', views.customer_view, name='customer_edit'),

    # Invoice Management
    #path('invoice_form/', views.invoice_form, name='invoice_form'),
    path('invoices/', views.invoice_view, name='invoice_list'),
    path('invoices/edit/<int:pk>/', views.invoice_view, name='invoice_edit'),

    # Vendor Management
    #path('vendor_list/', views.vendor_list, name='vendor_list'),
    path('vendors/', views.vendor_view, name='vendor_list'),
    path('vendors/edit/<int:pk>/', views.vendor_view, name='vendor_edit'),

    # Product Management
    path('products/', views.product_view, name='product_list'),
    path('products/edit/<int:pk>/', views.product_view, name='product_edit'),

    # Transaction Management
    path('transaction_form/', views.transaction_form, name='transaction_form'),
    path('transactions/', views.transaction_view, name='transaction_list'),
    path('transactions/edit/<int:pk>/', views.transaction_view, name='transaction_edit'),

    # Platform Import
    path('import/platforms/', views.platform_import_view, name='platform_import'),

    path('product_mapping/', views.product_mapping_view, name='product_mapping'),
    path('product_mapping/edit/<int:pk>/', views.product_mapping_view, name='product_mapping_edit'),

    # Help Page
    path('help/', views.help, name='help'),

    path('reports/', views.report_dashboard_view, name='reports'),
]


