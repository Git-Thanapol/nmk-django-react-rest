from django.shortcuts import render,redirect, get_object_or_404
from django.contrib.auth.models import User
from rest_framework import generics
from .serializers import UserSerializer, NoteSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Note, Customer, Company, Vendor, Product, Transaction, PurchaseOrder, PurchaseItem,Invoice, InvoiceItem
from .forms import CustomerForm, VendorForm, ProductForm, TransactionForm, PurchaseOrderForm, PurchaseItemFormSet,InvoiceForm, InvoiceItemFormSet, ImportFileForm
from django.db import transaction
from django.db.models import Q
from django import forms
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .utils_import import process_tiktok_orders, import_tiktok_invoices

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

def purchase_form(request):
    return render(request, 'purchase_form.html')

def invoice_form(request):
    """Render the invoice form page."""
    return render(request, 'invoice_form.html')

def transaction_form(request):
    return render(request, 'transaction_form.html')

#@login_required
def customer_list(request):
    # ---------------------------------------------------------
    # 1. Context Setup (Multi-company logic)
    # ---------------------------------------------------------
    # Assuming you have a way to get the current user's company. 
    # For now, we'll just pick the first one or None if not set.
    # In a real app, this might come from request.session['company_id']
    current_company = Company.objects.first() 
    
    # ---------------------------------------------------------
    # 2. Handle Form Submission (POST)
    # ---------------------------------------------------------
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            if current_company:
                customer.company = current_company
            customer.save()
            return redirect('customer_list')
    else:
        form = CustomerForm()

    # ---------------------------------------------------------
    # 3. Get Data & Filter (GET)
    # ---------------------------------------------------------
    customers = Customer.objects.all().order_by('-created_at')
    
    # Filter by Company (Multi-tenancy)
    if current_company:
        customers = customers.filter(company=current_company)

    # Search Logic
    search_query = request.GET.get('q')
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) | 
            Q(phone__icontains=search_query) | 
            Q(tax_id__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Status Filter
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        customers = customers.filter(is_active=True)
    elif status_filter == 'inactive':
        customers = customers.filter(is_active=False)

    context = {
        'form': form,
        'customers': customers,
        'search_query': search_query
    }
    return render(request, 'customer_list.html', context)

#@login_required
def customer_view(request, pk=None):
    # ---------------------------------------------------------
    # 1. Determine Context (Create vs Edit)
    # ---------------------------------------------------------
    if pk:
        customer_instance = get_object_or_404(Customer, pk=pk)
        is_editing = True
    else:
        customer_instance = None
        is_editing = False

    # Get current company (logic placeholder)
    current_company = Company.objects.first()

    # ---------------------------------------------------------
    # 2. Handle Form Submission (POST)
    # ---------------------------------------------------------
    if request.method == 'POST':
        # Pass 'instance' to update existing record, otherwise creates new
        form = CustomerForm(request.POST, instance=customer_instance)
        
        if form.is_valid():
            customer = form.save(commit=False)
            
            # If creating a new customer, assign the company
            if not is_editing and current_company:
                customer.company = current_company
            
            customer.save()
            return redirect('customer_list')
    else:
        # Load form with data (if editing) or blank (if creating)
        form = CustomerForm(instance=customer_instance)

    # ---------------------------------------------------------
    # 3. Get Data & Filter (GET)
    # ---------------------------------------------------------
    customers = Customer.objects.all().order_by('-created_at')
    
    if current_company:
        customers = customers.filter(company=current_company)

    # Search Logic
    search_query = request.GET.get('q')
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query) | 
            Q(phone__icontains=search_query) | 
            Q(tax_id__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    # Status Filter
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        customers = customers.filter(is_active=True)
    elif status_filter == 'inactive':
        customers = customers.filter(is_active=False)

    context = {
        'form': form,
        'customers': customers,
        'search_query': search_query,
        'is_editing': is_editing,             # Flag for Template
        'editing_customer': customer_instance # Object for Template
    }
    return render(request, 'customer_list.html', context)

#@login_required
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

#@login_required
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

#@login_required
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

#@login_required
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


#@login_required
def purchase_order_view(request, pk=None):
    # 1. Setup Context
    if pk:
        po_instance = get_object_or_404(PurchaseOrder, pk=pk)
        is_editing = True
    else:
        po_instance = None
        is_editing = False

    # 2. Handle POST (Save Data)
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, instance=po_instance)
        formset = PurchaseItemFormSet(request.POST, instance=po_instance)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic(): # Use atomic to ensure header & items save together
                # A. Save Header
                po = form.save(commit=False)
                if not is_editing:
                    po.created_by = request.user
                    po.company = Company.objects.first() # Placeholder logic
                po.save()
                
                # B. Save Items
                formset.instance = po
                formset.save()
                
                # C. Recalculate Totals (The model method we wrote earlier)
                po.calculate_totals()
                
                return redirect('purchase_list')
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


#@login_required
def invoice_view(request, pk=None):
    if pk:
        invoice_instance = get_object_or_404(Invoice, pk=pk)
        is_editing = True
    else:
        invoice_instance = None
        is_editing = False

    if request.method == 'POST':
        form = InvoiceForm(request.POST, instance=invoice_instance)
        formset = InvoiceItemFormSet(request.POST, instance=invoice_instance)
        
        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    # 1. Save Header
                    invoice = form.save(commit=False)
                    if not is_editing:
                        invoice.created_by = request.user
                        # Assign default company if not set
                        invoice.company = Company.objects.first() 
                    invoice.save()
                    
                    # 2. Process Items
                    items = formset.save(commit=False)
                    
                    # A. Handle Deletions (Restore Stock)
                    for obj in formset.deleted_objects:
                        if obj.purchase_item:
                            obj.purchase_item.remaining_quantity += obj.quantity
                            obj.purchase_item.save()
                        obj.delete()

                    # B. Handle Updates/Inserts
                    for item in items:
                        selected_batch = item.purchase_item # Might be None (if user left blank)
                        selected_product = item.product     # Always set (required by form)
                        
                        # --- SCENARIO A: User left Batch BLANK (Auto-Assign FIFO) ---
                        if not selected_batch:
                            # Find oldest batch for this product with stock
                            stock_batch = PurchaseItem.objects.filter(
                                product=selected_product, 
                                remaining_quantity__gt=0
                            ).order_by('id').first()
                            
                            if not stock_batch:
                                raise Exception(f"No stock available for Product: {selected_product.name}")
                            
                            # Check if that batch has enough for this requested amount
                            if item.quantity > stock_batch.remaining_quantity:
                                raise Exception(f"Auto-assign failed. Batch {stock_batch} only has {stock_batch.remaining_quantity} left, but you requested {item.quantity}.")
                                
                            item.purchase_item = stock_batch
                            
                        # --- SCENARIO B: User SELECTED a specific Batch ---
                        else:
                            # Integrity check: Does batch match product?
                            if selected_batch.product != selected_product:
                                raise Exception(f"Mismatch: Batch {selected_batch} does not belong to product {selected_product.name}")
                            
                            # If editing, we need to revert the *original* quantity first to check math
                            # (Otherwise we might falsely flag "not enough stock")
                            if item.pk:
                                original_item = InvoiceItem.objects.get(pk=item.pk)
                                # Only restore if the batch hasn't changed
                                if original_item.purchase_item == selected_batch:
                                    selected_batch.remaining_quantity += original_item.quantity

                            if item.quantity > selected_batch.remaining_quantity:
                                raise Exception(f"Not enough stock in selected batch {selected_batch}. Available: {selected_batch.remaining_quantity}")

                            item.purchase_item = selected_batch

                        # Deduct Stock & Save
                        item.purchase_item.remaining_quantity -= item.quantity
                        item.purchase_item.save()
                        
                        item.invoice = invoice
                        item.save()
                    
                    # 3. Final Totals
                    invoice.calculate_totals()
                    
                    messages.success(request, "Invoice saved successfully.")
                    return redirect('invoice_list')

            except Exception as e:
                # If anything fails, transaction rolls back automatically
                messages.error(request, f"Error: {str(e)}")
        else:
            messages.error(request, "Please check the form for errors.")
    else:
        form = InvoiceForm(instance=invoice_instance)
        formset = InvoiceItemFormSet(instance=invoice_instance)

    # List View Logic
    invoices = Invoice.objects.all().order_by('-invoice_date')
    
    if request.GET.get('q'):
        q = request.GET.get('q')
        invoices = invoices.filter(
            Q(invoice_number__icontains=q) | 
            Q(customer__name__icontains=q)
        )

    context = {
        'form': form,
        'formset': formset,
        'invoices': invoices,
        'is_editing': is_editing,
        'editing_invoice': invoice_instance
    }
    return render(request, 'invoice_form.html', context)


#@login_required
def platform_import_view(request):
    # Context for the template
    context = {
        'page_title': 'Platform Data Import',
        'form': ImportFileForm()
    }

    if request.method == 'POST':
        form = ImportFileForm(request.POST, request.FILES)
        
        if form.is_valid():
            uploaded_file = request.FILES['import_file']
            platform = form.cleaned_data['platform']
            
            # --- TIKTOK IMPORT LOGIC ---
            if platform == 'tiktok':
                try:
                    # 1. Save file temporarily to disk so Pandas can read it
                    # (Pandas can read directly from memory, but saving is safer for large files/debugging)
                    import os
                    from django.core.files.storage import FileSystemStorage
                    
                    fs = FileSystemStorage()
                    filename = fs.save(f"temp_{uploaded_file.name}", uploaded_file)
                    file_path = fs.path(filename)
                    
                    # 2. Process Data (The function we wrote earlier)
                    # This returns TWO dataframes
                    header_df, items_df = process_tiktok_orders(file_path)
                    
                    # 3. Import to Database (The function we wrote earlier)
                    # Hardcoding Company ID 1 for now, or get from request.user.company if you have that logic
                    company_id = 1 
                    result = import_tiktok_invoices(header_df, items_df, company_id, request.user.id)
                    
                    # 4. Clean up temp file
                    os.remove(file_path)

                    # 5. User Feedback
                    if result['status'] == 'completed':
                        msg = f"Import Successful! Imported {result['imported']} orders. Failed: {result['failed']}."
                        if result['failed'] > 0:
                            msg += f" First error: {result['error_log'][0]}"
                        messages.success(request, msg)
                    else:
                        messages.error(request, f"Import Error: {result['message']}")

                except Exception as e:
                    messages.error(request, f"Critical Error during processing: {str(e)}")
            
            # --- OTHER PLATFORMS (Mockup) ---
            else:
                messages.warning(request, f"Import for {platform} is coming soon!")
                
            return redirect('platform_import') # Redirect back to clear form
            
        else:
            messages.error(request, "Invalid file format. Please check your selection.")

    return render(request, 'platforms.html', context)