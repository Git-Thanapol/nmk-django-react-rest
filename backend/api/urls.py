from django.urls import path
from . import views
from django.contrib import admin

urlpatterns = [
    #path('admin/', admin.site.urls),
    #path('api/user/register/', CreateUserView.as_view(), name='create_user'),
    path('notes/', views.NoteListCreateView.as_view(), name='note_list_create'),
    path('notes/<int:pk>/', views.NoteDeleteView.as_view(), name='note_delete'),
    #path('', views.index, name='index'),
    path('purchase_form/', views.purchase_form, name='purchase_form'),
    path('invoice_form/', views.invoice_form, name='invoice_form'),
    path('transaction_form/', views.transaction_form, name='transaction_form'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
