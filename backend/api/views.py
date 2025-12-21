# Django core
import os

from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string,get_template

# Third-party
import weasyprint
from xhtml2pdf import pisa
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from pybaht import bahttext

# Local apps – models
from .models import (
    Company,
    Invoice,
    InvoiceItem,
    Note,
    Product,
    ProductAlias,
    PurchaseItem,
    PurchaseOrder,
    Transaction,
    Vendor,
)

# Local apps – forms
from .forms import (
    ImportFileForm,
    InvoiceForm,
    InvoiceItemFormSet,
    ProductForm,
    PurchaseItemFormSet,
    PurchaseOrderForm,
    ReportFilterForm,
    TransactionForm,
    VendorForm,
    CompanyForm,
)

# Local apps – serializers
from .serializers import NoteSerializer, UserSerializer

# Local apps – utilities
from .utils_import_core import universal_invoice_import
from .utils_pdf import link_callback
from .utils_processors import (
    process_lazada_orders,
    process_shopee_orders,
    process_tiktok_orders,
)
from .utils_reports import (
    generate_purchase_tax_report,
    generate_sales_tax_report,
    generate_stock_report,
    generate_combined_tax_report,
)



class NoteListCreateView(generics.ListCreateAPIView):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        if serializer.is_valid():
            serializer.save(user=self.request.user)
        else:
            raise serializer.errors.ValidationError("Invalid data")

class NoteDeleteView(generics.DestroyAPIView):
    queryset = Note.objects.all()
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

# Create your views here.
class CreateUserView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]  # Allow anyone to create a user
    
def home(request):
    # Get all Posts
    # Render app template with context
    return render(request, 'base.html')

def help(request):
    # Get all Posts
    # Render app template with context
    return render(request, 'help.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('help')
        else:
            messages.error(request, 'Username หรือ Password ไม่ถูกต้อง')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def purchase_form(request):
    return render(request, 'purchase_form.html')

@login_required
def invoice_form(request):
    """Render the invoice form page."""
    return render(request, 'invoice_form.html')

@login_required
def transaction_form(request):
    return render(request, 'transaction_form.html')

@login_required
def vendor_list(request):
    # 1. Handle Form Submission (POST)
    if request.method == 'POST':
        form = VendorForm(request.POST)
        if form.is_valid():
            vendor = form.save(commit=False)
            
            # --- Logic: Select or Create Company ---
            company_name_input = form.cleaned_data.get('company_selection')
            
            if company_name_input:
                # 'get_or_create' tries to find a company with this name.
                # If not found, it creates a new one.
                company_obj, created = Company.objects.get_or_create(
                    name=company_name_input,
                    defaults={'is_active': True} # Default values for new company
                )
                vendor.company = company_obj
            
            vendor.save()
            return redirect('vendor_list')
    else:
        form = VendorForm()

    # 2. Get Data for Lists
    # We need all companies for the datalist dropdown
    all_companies = Company.objects.filter(is_active=True)
    
    # We need vendors for the table
    vendors = Vendor.objects.all().select_related('company').order_by('-created_at')

    # 3. Search & Filter Logic
    search_query = request.GET.get('q')
    if search_query:
        vendors = vendors.filter(
            Q(name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(company__name__icontains=search_query) # Search by related company name too
        )

    status_filter = request.GET.get('status')
    if status_filter == 'active':
        vendors = vendors.filter(is_active=True)
    elif status_filter == 'inactive':
        vendors = vendors.filter(is_active=False)

    context = {
        'form': form,
        'vendors': vendors,
        'all_companies': all_companies, # Passed to template for <datalist>
        'search_query': search_query
    }
    return render(request, 'vendor_list.html', context)

@login_required
def vendor_view(request, pk=None):
    # 1. Determine Context (Create vs Edit)
    if pk:
        vendor_instance = get_object_or_404(Vendor, pk=pk)
        is_editing = True
    else:
        vendor_instance = None
        is_editing = False

    # 2. Handle Form Submission (POST)
    if request.method == 'POST':
        # Pass the instance if we are editing, otherwise None
        form = VendorForm(request.POST, instance=vendor_instance)
        
        if form.is_valid():
            vendor = form.save(commit=False)
            
            # Logic: Select or Create Company
            company_name_input = form.cleaned_data.get('company_selection')
            if company_name_input:
                company_obj, created = Company.objects.get_or_create(
                    name=company_name_input,
                    defaults={'is_active': True}
                )
                vendor.company = company_obj
            
            vendor.save()
            
            # Redirect to the main list (clears the form)
            return redirect('vendor_list')
    else:
        # Load form with instance (if editing) or blank (if creating)
        form = VendorForm(instance=vendor_instance)

    # 3. Get Data for Table & Search
    all_companies = Company.objects.filter(is_active=True)
    vendors = Vendor.objects.all().select_related('company').order_by('-created_at')

    search_query = request.GET.get('q')
    if search_query:
        vendors = vendors.filter(
            Q(name__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(company__name__icontains=search_query)
        )
    
    # Status Filter
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        vendors = vendors.filter(is_active=True)
    elif status_filter == 'inactive':
        vendors = vendors.filter(is_active=False)

    context = {
        'form': form,
        'vendors': vendors,
        'all_companies': all_companies,
        'search_query': search_query,
        'is_editing': is_editing, # Pass this flag to template
        'editing_vendor': vendor_instance # Pass the object being edited
    }
    return render(request, 'vendor_list.html', context)

@login_required
def product_view(request, pk=None):
    # ---------------------------------------------------------
    # 1. Determine Context (Create vs Edit)
    # ---------------------------------------------------------
    if pk:
        product_instance = get_object_or_404(Product, pk=pk)
        is_editing = True
    else:
        product_instance = None
        is_editing = False

    # ---------------------------------------------------------
    # 2. Handle Form Submission (POST)
    # ---------------------------------------------------------
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product_instance)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product_instance)

    # ---------------------------------------------------------
    # 3. Get Data & Filter (GET)
    # ---------------------------------------------------------
    products = Product.objects.all().select_related('company').order_by('-created_at')
    
    # Search Logic
    search_query = request.GET.get('q')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(sku__icontains=search_query) |
            Q(category__icontains=search_query)
        )

    # Filter by Category (Optional extra filter)
    cat_filter = request.GET.get('category')
    if cat_filter:
        products = products.filter(category=cat_filter)

    # Filter by Status
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        products = products.filter(is_active=True)
    elif status_filter == 'inactive':
        products = products.filter(is_active=False)

    # Get unique categories for the datalist suggestion
    # This combines the defaults from model + any new ones existing in DB
    existing_categories = Product.objects.values_list('category', flat=True).distinct()
    
    context = {
        'form': form,
        'products': products,
        'search_query': search_query,
        'existing_categories': set(existing_categories), # Use set to remove duplicates
        'is_editing': is_editing,
        'editing_product': product_instance
    }
    return render(request, 'product_list.html', context)

@login_required
def transaction_view(request, pk=None):
    # ---------------------------------------------------------
    # 1. Determine Context (Create vs Edit)
    # ---------------------------------------------------------
    if pk:
        transaction_instance = get_object_or_404(Transaction, pk=pk)
        is_editing = True
    else:
        transaction_instance = None
        is_editing = False

    # ---------------------------------------------------------
    # 2. Handle Form Submission (POST)
    # ---------------------------------------------------------
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction_instance)
        if form.is_valid():
            transaction = form.save(commit=False)
            # Assign current user/company logic
            transaction.created_by = request.user 
            transaction.company = Company.objects.first() # Placeholder logic
            transaction.save()
            return redirect('transaction_list')
    else:
        form = TransactionForm(instance=transaction_instance)

    # ---------------------------------------------------------
    # 3. Get Data & Filter (GET)
    # ---------------------------------------------------------
    transactions = Transaction.objects.all().order_by('-transaction_date', '-created_at')

    # --- A. Search (Number, Ref, Desc, Amount) ---
    search_query = request.GET.get('q')
    if search_query:
        transactions = transactions.filter(
            Q(transaction_number__icontains=search_query) | 
            Q(reference__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(amount__icontains=search_query)
        )

    # --- B. Dropdown Filters (Type & Category) ---
    type_filter = request.GET.get('type')
    if type_filter:
        transactions = transactions.filter(type=type_filter)

    cat_filter = request.GET.get('category')
    if cat_filter:
        transactions = transactions.filter(category=cat_filter)

    # --- C. Date Range Filter ---
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if start_date and end_date:
        transactions = transactions.filter(transaction_date__range=[start_date, end_date])
    elif start_date:
        transactions = transactions.filter(transaction_date__gte=start_date)
    elif end_date:
        transactions = transactions.filter(transaction_date__lte=end_date)

    # Pass choices to template for the filter dropdowns
    # (Using the model choices directly)
    type_choices = Transaction.TRANSACTION_TYPES
    category_choices = Transaction.CATEGORY_CHOICES

    context = {
        'form': form,
        'transactions': transactions,
        'search_query': search_query,
        'type_choices': type_choices,
        'category_choices': category_choices,
        'is_editing': is_editing,
        'editing_transaction': transaction_instance
    }
    return render(request, 'transaction_list.html', context)

@login_required
def purchase_order_view(request, pk=None):
    # 1. Setup Context
    if pk:
        po_instance = get_object_or_404(PurchaseOrder, pk=pk)
        is_editing = True
    else:
        po_instance = None
        is_editing = False

    # --- RULE 1: If CANCELLED -> Completely Locked (Read-Only) ---
    if is_editing and po_instance.status == 'CANCELLED': # 'Cancelled' in Thai
        # If user tries to POST (Save) to a cancelled order, block it
        if request.method == 'POST':
            messages.error(request, "Cannot edit a Cancelled order.")
            return redirect('purchase_edit', pk=pk) # Reload page

    # 2. Handle POST (Save Data)
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=po_instance)
        # Note: We don't load formset yet because we might reject the save immediately
        #formset = PurchaseItemFormSet(request.POST, instance=po_instance)
        
        if form.is_valid():
            # --- RULE 2: If 'Paid'/'RECEIVED' -> Allow ONLY 'CANCELLED' ---
            if is_editing and po_instance.status == 'RECEIVED': # Change 'RECEIVED' to 'Paid' if needed
                new_status = form.cleaned_data.get('status')
                
                if new_status != 'CANCELLED':
                    messages.error(request, "Paid/Received orders can only be changed to 'CANCELLED'. Other edits are forbidden.")
                    return redirect('purchase_edit', pk=pk)
            
            # --- Normal Save Logic Continues ---
            formset = PurchaseItemFormSet(request.POST, instance=po_instance)

            if form.is_valid() and formset.is_valid():
                try:
                    with transaction.atomic(): # Use atomic to ensure header & items save together
                        # A. Save Header
                        po = form.save(commit=False)
                        if not is_editing:
                            po.created_by = request.user
                            #po.company = Company.objects.first() # Placeholder logic
                        po.save()
                        
                        # B. Save Items
                        formset.instance = po
                        formset.save()
                        
                        # C. Recalculate Totals (The model method we wrote earlier)
                        po.calculate_totals()
                        
                        return redirect('purchase_list')
                except Exception as e:
                    messages.error(request, str(e))
    else:
        form = PurchaseOrderForm(instance=po_instance)
        formset = PurchaseItemFormSet(instance=po_instance)

    # 3. List View Logic (If viewing list)
    orders = PurchaseOrder.objects.all().order_by('-order_date')
    
    # Simple Filters
    if request.GET.get('q'):
        q = request.GET.get('q')
        orders = orders.filter(Q(po_number__icontains=q) | Q(vendor__name__icontains=q))

    context = {
        'form': form,
        'formset': formset,
        'orders': orders,
        'is_editing': is_editing,
        'editing_po': po_instance
    }
    return render(request, 'purchase_form.html', context)

@login_required
def invoice_view(request, pk=None):
    """
    Combined List + Create + Edit View.
    Handles complex Stock Logic (FIFO, Manual Batch, Restore on Edit).
    """
    # 1. Determine Mode (Create vs Edit)
    if pk:
        invoice_instance = get_object_or_404(Invoice, pk=pk)
        is_editing = True
    else:
        invoice_instance = None
        is_editing = False

    # 2. Handle Form Submission
    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice_instance)
        formset = InvoiceItemFormSet(request.POST, instance=invoice_instance)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # --- A. Save Header ---
                    invoice = form.save(commit=False)
                    if not is_editing:
                        invoice.created_by = request.user
                        # Assign default company if not set
                        if not invoice.company:
                            invoice.company = Company.objects.first() 
                    invoice.save()
                    
                    # --- B. Process Items (The "Service" Layer Logic) ---
                    items = formset.save(commit=False)
                    
                    # B1. Handle Deletions (Restore Stock)
                    for obj in formset.deleted_objects:
                        if obj.purchase_item:
                            obj.purchase_item.remaining_quantity += obj.quantity
                            obj.purchase_item.save()
                        obj.delete()

                    # B2. Handle Updates/Inserts
                    for item in items:
                        selected_batch = item.purchase_item # Might be None (if user left blank)
                        selected_product = item.product     # Always set (required by form)
                        
                        # --- SCENARIO 1: User left Batch BLANK (Auto-Assign FIFO) ---
                        if not selected_batch:
                            # Find oldest batch for this product with stock
                            stock_batch = PurchaseItem.objects.filter(
                                product=selected_product, 
                                remaining_quantity__gt=0
                            ).order_by('id').first()
                            
                            if not stock_batch:
                                raise Exception(f"No stock available for Product: {selected_product.name}")
                            
                            # Check if that batch has enough
                            if item.quantity > stock_batch.remaining_quantity:
                                raise Exception(f"Auto-assign failed. Batch {stock_batch} only has {stock_batch.remaining_quantity} left, but you requested {item.quantity}.")
                                
                            item.purchase_item = stock_batch
                            
                        # --- SCENARIO 2: User SELECTED a specific Batch ---
                        else:
                            # Integrity check: Does batch match product?
                            if selected_batch.product != selected_product:
                                raise Exception(f"Mismatch: Batch {selected_batch} does not belong to product {selected_product.name}")
                            
                            # If editing, we need to revert the *original* quantity first to check math
                            if item.pk:
                                original_item = InvoiceItem.objects.get(pk=item.pk)
                                # Only restore if the batch hasn't changed (or logic gets too complex)
                                if original_item.purchase_item == selected_batch:
                                    selected_batch.remaining_quantity += original_item.quantity

                            if item.quantity > selected_batch.remaining_quantity:
                                raise Exception(f"Not enough stock in selected batch {selected_batch}. Available: {selected_batch.remaining_quantity}")

                            item.purchase_item = selected_batch

                        # --- C. Deduct Stock & Save ---
                        # Note: Ensure InvoiceItem.save() in models.py DOES NOT deduct stock again.
                        item.purchase_item.remaining_quantity -= item.quantity
                        item.purchase_item.save()
                        
                        item.invoice = invoice
                        item.save() # This triggers calculate_totals via Model, but that's fine.
                    
                    # --- D. Final Totals ---
                    invoice.calculate_totals()
                    
                    messages.success(request, "Invoice saved successfully.")
                    return redirect('invoice_list') # Redirect to clear POST data

            except Exception as e:
                # If anything fails, transaction rolls back automatically
                messages.error(request, f"Error: {str(e)}")
        else:
            messages.error(request, "Please check the form for errors.")
    
    # 3. Handle GET Request (Display Form)
    else:
        form = InvoiceForm(instance=invoice_instance)
        formset = InvoiceItemFormSet(instance=invoice_instance)

    # 4. Fetch Recent Data for the Table
    # Optimized with select_related to prevent N+1 queries on Customer
    invoices = Invoice.objects.select_related('vendor').order_by('-invoice_date', '-created_at')
    
    # Optional Server-Side Search (in addition to JS filter)
    if request.GET.get('q'):
        q = request.GET.get('q')
        invoices = invoices.filter(
            Q(invoice_number__icontains=q) | 
            Q(vendor__name__icontains=q)
        )
    
    # Limit to last 1000 for performance
    invoices = invoices[:1000]
    # get second element (display labels) from STATUS_CHOICES
    schoices = [label for _, label in Invoice.STATUS_CHOICES]

    context = {
        'form': form,
        'formset': formset,
        'invoices': invoices,
        'is_editing': is_editing,
        'editing_invoice': invoice_instance,
        'status_choices': [1,2,3]
    }
    return render(request, 'invoice_form.html', context)

@login_required
def platform_import_view(request):
    # Standard Context for GET requests (Dropdowns etc.)
    #companies = Company.objects.filter(is_active=True)
    companies = Company.objects.all()
    context = {
        'page_title': 'Platform Data Import',
        'form': ImportFileForm(),
        'companies': companies
    }

    if request.method == 'POST':
        # We manually check the request.FILES and POST data here for flexibility, 
        # but you can also bind it to the form if preferred.
        
        # 1. Validation: Check if file and company are present
        uploaded_file = request.FILES.get('import_file')
        platform = request.POST.get('platform')
        company_id = request.POST.get('company_id')

        if not uploaded_file or not platform or not company_id:
            messages.error(request, "Missing required data. Please select a file, platform, and company.")
            return redirect('platform_import')

        file_path = None

        try:
            # --- 1. SAVE FILE TEMPORARILY ---
            # Get the target company object (validates ID exists)
            target_company = get_object_or_404(Company, pk=company_id)
            
            fs = FileSystemStorage()
            # Clean filename to avoid OS issues
            clean_name = f"temp_{platform}_{uploaded_file.name.replace(' ', '_')}"
            filename = fs.save(clean_name, uploaded_file)
            file_path = fs.path(filename)
            
            # --- 2. PROCESS & IMPORT ---
            header_df = None
            items_df = None
            target_platform_name = ''

            # A. Select Processor based on Platform
            if platform == 'tiktok':
                header_df, items_df = process_tiktok_orders(file_path)
                target_platform_name = 'TikTok Shop'
                
            elif platform == 'shopee':
                header_df, items_df = process_shopee_orders(file_path)
                target_platform_name = 'Shopee'
            
            elif platform == 'lazada':
                header_df, items_df = process_lazada_orders(file_path)
                target_platform_name = 'Lazada'

            else:
                raise ValueError(f"Platform '{platform}' is not yet supported.")

            # B. Run Universal Import
            if header_df is not None and items_df is not None:
                result = universal_invoice_import(
                    header_df, 
                    items_df, 
                    target_company.id,  # Use the ID from the selected company
                    request.user.id, 
                    platform_name=target_platform_name
                )

                # C. Feedback
                if result['status'] == 'completed':
                    msg = f"Import Successful for {target_company.name}! Imported {result['imported']} orders. Failed: {result['failed']}."
                    if result['failed'] > 0:
                        msg += f" First error: {result['error_log'][0]}"
                    messages.success(request, msg)
                else:
                    messages.error(request, f"Import Error: {result['message']}")
            else:
                messages.error(request, "Data Processing returned empty results.")

        except Exception as e:
            # Catch processing errors (e.g. wrong columns in CSV)
            messages.error(request, f"Processing Error: {str(e)}")

        finally:
            # --- 3. CLEANUP ---
            # Always remove the temp file, even if import fails
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass # Log failure to delete if necessary
            
        return redirect('platform_import')

    # GET Request
    return render(request, 'platforms.html', context)

@login_required
def product_mapping_view(request):
    """
    Dashboard to map Unknown External Keys to Internal Products.
    """
    # 1. Handle Mapping Submission
    if request.method == 'POST':
        external_key = request.POST.get('external_key')
        internal_product_id = request.POST.get('product_id')
        
        if external_key and internal_product_id:
            product = Product.objects.get(id=internal_product_id)
            
            # A. Create the Alias (Future proofing)
            ProductAlias.objects.get_or_create(
                external_key=external_key,
                defaults={'product': product}
            )
            
            # B. Retroactively Fix Existing InvoiceItems
            # Find all items with this SKU string that have NO product yet
            InvoiceItem.objects.filter(sku=external_key, product__isnull=True).update(product=product)
            
            messages.success(request, f"Mapped '{external_key}' to '{product.name}' successfully.")
            return redirect('product_mapping')

    # 2. Find Unmapped Items
    # Group by 'sku' (which holds our External Key) and count occurences
    unmapped_groups = InvoiceItem.objects.filter(product__isnull=True) \
        .values('sku', 'item_name') \
        .annotate(count=Count('id')) \
        .order_by('-count')\
        [:20]

    # Get all active products for the dropdown
    products = Product.objects.filter(is_active=True)

    context = {
        'unmapped_items': unmapped_groups,
        'products': products
    }
    return render(request, 'product_mapping.html', context)

def report_dashboard_view(request):
    form = ReportFilterForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        report_type = request.POST.get('report_type')
        company_id = form.cleaned_data['company']
        start_date = form.cleaned_data['start_date']
        end_date = form.cleaned_data['end_date']
        report_basis = form.cleaned_data['report_basis']

        # --- 1. Handle "All Companies" Logic ---
        target_company = None
        if company_id == 'all':
            company_filter = {} # Empty dict means no filter (All)
            company_name_for_report = "รวมทุกบริษัท (All Companies)"
        else:
            target_company = Company.objects.get(pk=company_id)
            company_filter = {'company': target_company}
            company_name_for_report = target_company.name

        # --- Report 1: Purchase Tax ---
        if report_type == 'purchase_tax':
            queryset = PurchaseOrder.objects.filter(status='PAID', **company_filter)

            if report_basis == 'create_date':
                queryset = queryset.filter(order_date__range=[start_date, end_date]).order_by('order_date')
            else:
                queryset = queryset.filter(tax_sender_date__range=[start_date, end_date]) \
                                   .exclude(tax_sender_date__isnull=True) \
                                   .order_by('tax_sender_date')

            return generate_purchase_tax_report(queryset, company_name_for_report, start_date, end_date, report_basis)
            
        # --- Report 2: Sales Tax ---
        elif report_type == 'sales_tax':
            queryset = Invoice.objects.filter(status='BILLED', **company_filter)

            if report_basis == 'create_date':
                queryset = queryset.filter(invoice_date__range=[start_date, end_date]).order_by('invoice_date', 'invoice_number')
            else:
                queryset = queryset.filter(tax_sender_date__range=[start_date, end_date]) \
                                   .exclude(tax_sender_date__isnull=True) \
                                   .order_by('tax_sender_date', 'invoice_number')
            
            return generate_sales_tax_report(queryset, company_name_for_report, start_date, end_date, report_basis)

        # --- Report 3: Stock Report ---
        elif report_type == 'stock_report':
            # Note: Stock report usually needs a specific company to make sense of 'Actual Stock'.
            # If 'all', it aggregates everything.
            return generate_stock_report(target_company, start_date, end_date) # target_company might be None

        # --- Report 4: Combined Tax Report (NEW) ---
        elif report_type == 'combined_tax':
            # We fetch both lists here and pass them to the generator
            
            # A. Purchases
            po_qs = PurchaseOrder.objects.filter(status='PAID', **company_filter)
            
            # B. Sales
            inv_qs = Invoice.objects.filter(status='BILLED', **company_filter)

            # Apply Date Filters
            if report_basis == 'create_date':
                po_qs = po_qs.filter(order_date__range=[start_date, end_date])
                inv_qs = inv_qs.filter(invoice_date__range=[start_date, end_date])
            else:
                po_qs = po_qs.filter(tax_sender_date__range=[start_date, end_date]).exclude(tax_sender_date__isnull=True)
                inv_qs = inv_qs.filter(tax_sender_date__range=[start_date, end_date]).exclude(tax_sender_date__isnull=True)

            return generate_combined_tax_report(po_qs, inv_qs, company_name_for_report, start_date, end_date, report_basis)

    context = {
        'form': form,
        'page_title': 'Reports Center'
    }
    return render(request, 'reports.html', context)

@login_required
def invoice_pdf_view(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    
    context = {
        'invoice': invoice,
        'items': invoice.invoice_items.all(),
        'company': invoice.company,
    }

    # 1. Render HTML
    html_string = render_to_string('pdf/invoice_print.html', context)

    # 2. Base URL for static files
    # WeasyPrint needs to know where to find /static/ files on disk
    base_url = request.build_absolute_uri('/')

    # 3. Generate PDF
    # WeasyPrint handles fonts and images automatically if base_url is correct
    pdf_file = weasyprint.HTML(string=html_string, base_url=base_url).write_pdf()

    # 4. Return Response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"Invoice_{invoice.invoice_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def company_list_view(request):
    companies = Company.objects.all()
    return render(request, 'company/company_list.html', {'companies': companies})

@login_required
def company_create_view(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'เพิ่มข้อมูลบริษัทเรียบร้อยแล้ว')
            return redirect('company_list')
    else:
        form = CompanyForm()
    
    return render(request, 'company/company_form.html', {
        'form': form,
        'title': 'เพิ่มข้อมูลบริษัทใหม่'
    })

@login_required
def company_edit_view(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, 'บันทึกข้อมูลเรียบร้อยแล้ว')
            return redirect('company_list')
    else:
        form = CompanyForm(instance=company)
    
    return render(request, 'company/company_form.html', {
        'form': form, 
        'title': f'แก้ไขข้อมูล: {company.name}',
        'is_editing': True
    })