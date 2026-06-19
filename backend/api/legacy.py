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
# def invoice_view(request, pk=None):
#     if pk:
#         invoice_instance = get_object_or_404(Invoice, pk=pk)
#         is_editing = True
#     else:
#         invoice_instance = None
#         is_editing = False

#     if request.method == 'POST':
#         form = InvoiceForm(request.POST, instance=invoice_instance)
#         formset = InvoiceItemFormSet(request.POST, instance=invoice_instance)
        
#         if form.is_valid() and formset.is_valid():
#             try:
#                 with transaction.atomic():
#                     # 1. Save Header
#                     invoice = form.save(commit=False)
#                     if not is_editing:
#                         invoice.created_by = request.user
#                         # Assign default company if not set
#                         invoice.company = Company.objects.first() 
#                     invoice.save()
                    
#                     # 2. Process Items
#                     items = formset.save(commit=False)
                    
#                     # A. Handle Deletions (Restore Stock)
#                     for obj in formset.deleted_objects:
#                         if obj.purchase_item:
#                             obj.purchase_item.remaining_quantity += obj.quantity
#                             obj.purchase_item.save()
#                         obj.delete()

#                     # B. Handle Updates/Inserts
#                     for item in items:
#                         selected_batch = item.purchase_item # Might be None (if user left blank)
#                         selected_product = item.product     # Always set (required by form)
                        
#                         # --- SCENARIO A: User left Batch BLANK (Auto-Assign FIFO) ---
#                         if not selected_batch:
#                             # Find oldest batch for this product with stock
#                             stock_batch = PurchaseItem.objects.filter(
#                                 product=selected_product, 
#                                 remaining_quantity__gt=0
#                             ).order_by('id').first()
                            
#                             if not stock_batch:
#                                 raise Exception(f"No stock available for Product: {selected_product.name}")
                            
#                             # Check if that batch has enough for this requested amount
#                             if item.quantity > stock_batch.remaining_quantity:
#                                 raise Exception(f"Auto-assign failed. Batch {stock_batch} only has {stock_batch.remaining_quantity} left, but you requested {item.quantity}.")
                                
#                             item.purchase_item = stock_batch
                            
#                         # --- SCENARIO B: User SELECTED a specific Batch ---
#                         else:
#                             # Integrity check: Does batch match product?
#                             if selected_batch.product != selected_product:
#                                 raise Exception(f"Mismatch: Batch {selected_batch} does not belong to product {selected_product.name}")
                            
#                             # If editing, we need to revert the *original* quantity first to check math
#                             # (Otherwise we might falsely flag "not enough stock")
#                             if item.pk:
#                                 original_item = InvoiceItem.objects.get(pk=item.pk)
#                                 # Only restore if the batch hasn't changed
#                                 if original_item.purchase_item == selected_batch:
#                                     selected_batch.remaining_quantity += original_item.quantity

#                             if item.quantity > selected_batch.remaining_quantity:
#                                 raise Exception(f"Not enough stock in selected batch {selected_batch}. Available: {selected_batch.remaining_quantity}")

#                             item.purchase_item = selected_batch

#                         # Deduct Stock & Save
#                         item.purchase_item.remaining_quantity -= item.quantity
#                         item.purchase_item.save()
                        
#                         item.invoice = invoice
#                         item.save()
                    
#                     # 3. Final Totals
#                     invoice.calculate_totals()
                    
#                     messages.success(request, "Invoice saved successfully.")
#                     return redirect('invoice_list')

#             except Exception as e:
#                 # If anything fails, transaction rolls back automatically
#                 messages.error(request, f"Error: {str(e)}")
#         else:
#             messages.error(request, "Please check the form for errors.")
#     else:
#         form = InvoiceForm(instance=invoice_instance)
#         formset = InvoiceItemFormSet(instance=invoice_instance)

#     # List View Logic
#     invoices = Invoice.objects.all().order_by('-invoice_date')
    
#     if request.GET.get('q'):
#         q = request.GET.get('q')
#         invoices = invoices.filter(
#             Q(invoice_number__icontains=q) | 
#             Q(customer__name__icontains=q)
#         )

#     context = {
#         'form': form,
#         'formset': formset,
#         'invoices': invoices,
#         'is_editing': is_editing,
#         'editing_invoice': invoice_instance
#     }
#     return render(request, 'invoice_form.html', context)

# @login_required
# def platform_import_view(request):
#     """
#     View for importing TikTok/Shopee data via CSV.
#     """
#     context = {
#         'page_title': 'Platform Data Import',
#         'form': ImportFileForm()
#     }

#     if request.method == 'POST':
#         form = ImportFileForm(request.POST, request.FILES)
        
#         if form.is_valid():
#             uploaded_file = request.FILES['import_file']
#             platform = form.cleaned_data['platform']
            
#             if platform == 'tiktok':
#                 try:
#                     # Save temp file
#                     fs = FileSystemStorage()
#                     filename = fs.save(f"temp_{uploaded_file.name}", uploaded_file)
#                     file_path = fs.path(filename)
                    
#                     # Process & Import
#                     # 1. Parse CSV/Excel
#                     header_df, items_df = process_tiktok_orders(file_path)
                    
#                     # 2. Save to DB
#                     # TODO: Make company dynamic based on user profile
#                     company_id = 1 
#                     result = import_tiktok_invoices(header_df, items_df, company_id, request.user.id)
                    
#                     # Cleanup
#                     os.remove(file_path)

#                     if result['status'] == 'completed':
#                         msg = f"Import Successful! Imported {result['imported']} orders. Failed: {result['failed']}."
#                         if result['failed'] > 0:
#                             msg += f" First error: {result['error_log'][0]}"
#                         messages.success(request, msg)
#                     else:
#                         messages.error(request, f"Import Error: {result['message']}")

#                 except Exception as e:
#                     messages.error(request, f"Critical Error: {str(e)}")
            
#             else:
#                 messages.warning(request, f"Import for {platform} is coming soon!")
                
#             return redirect('platform_import')
            
#         else:
#             messages.error(request, "Invalid file format.")

#     return render(request, 'platforms.html', context)



# class CustomerForm(forms.ModelForm):
#     class Meta:
#         model = Customer
#         # Note: 'company' is excluded here as it's usually set automatically based on the logged-in user
#         fields = ['name', 'tax_id', 'phone', 'email', 'address', 'is_active']
#         widgets = {
#             'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer or Company Name'}),
#             'tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tax Identification ID'}),
#             'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '081-234-5678'}),
#             'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}),
#             'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Billing/Shipping Address'}),
#             'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#         }
#         labels = {
#             'name': 'Customer / Company Name',
#         } 

@login_required
def platform_import_view(request):
    # Standard Context for GET requests (Dropdowns etc.)
    companies = Company.objects.filter(is_active=True)
    
    context = {
        'page_title': 'Platform Data Import',
        'form': ImportFileForm(),
        'companies': companies
    }

    if request.method == 'POST':
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
                    target_company.id, 
                    request.user.id, 
                    platform_name=target_platform_name
                )

                # =========================================================
                # C. Check Results & Generate Error Report if needed
                # =========================================================
                if result['failed'] > 0:
                    # 1. Create Excel Workbook
                    wb = openpyxl.Workbook()
                    ws = wb.active
                    ws.title = "Import Errors"
                    
                    # 2. Styling
                    header_font = Font(bold=True, color="FFFFFF")
                    header_fill = PatternFill(start_color="DC3545", end_color="DC3545", fill_type="solid") # Red background
                    
                    # 3. Add Headers
                    headers = ["Excel Row", "Order ID", "Error Message", "Suggestion"]
                    ws.append(headers)
                    for cell in ws[1]:
                        cell.font = header_font
                        cell.fill = header_fill

                    # 4. Fill Data from error_log
                    for err in result['error_log']:
                        # Handle structured dict from updated utils
                        if isinstance(err, dict):
                            row_idx = err.get('row_index', '-')
                            order_id = err.get('order_id', '-')
                            reason = err.get('reason', '-')
                        else:
                            # Fallback if utils return string
                            row_idx = "-"
                            order_id = "Unknown"
                            reason = str(err)

                        # Simple Suggestions
                        suggestion = ""
                        if "numeric field overflow" in reason:
                            suggestion = "Amount too large (> 10 Billion). Check columns."
                        elif "unique constraint" in reason:
                            suggestion = "Order ID already exists."
                        elif "matches query" in reason:
                            suggestion = "Missing related data."

                        ws.append([row_idx, order_id, reason, suggestion])

                    # 5. Adjust Column Widths
                    ws.column_dimensions['A'].width = 15
                    ws.column_dimensions['B'].width = 25
                    ws.column_dimensions['C'].width = 50
                    ws.column_dimensions['D'].width = 40

                    # 6. Prepare Response (Download)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                    filename = f"error_import_{platform}_{timestamp}.xlsx"
                    
                    response = HttpResponse(
                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                    response['Content-Disposition'] = f'attachment; filename="{filename}"'
                    
                    wb.save(response)
                    
                    # Add a warning message (might show on next page load)
                    messages.warning(request, f"Import finished with errors. Downloading report... (Success: {result['imported']}, Failed: {result['failed']})")
                    
                    # IMPORTANT: We return 'response' here to trigger download, redirect stops happening.
                    return response

                elif result['status'] == 'completed':
                    messages.success(request, f"Import Successful for {target_company.name}! Imported {result['imported']} orders.")
                
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
                    pass 
            
        return redirect('platform_import')

    # GET Request
    return render(request, 'platforms.html', context)

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