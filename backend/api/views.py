# Django core
import os

from django import forms
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.db.models import Count, F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string,get_template
from django.http import JsonResponse,HttpResponseRedirect
from django.utils import timezone

# Third-party
import weasyprint
from xhtml2pdf import pisa
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from pybaht import bahttext
import openpyxl
from openpyxl.styles import Font, PatternFill
from datetime import datetime
import threading

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
    PurchaseAttachment,
    Transaction,
    Vendor,
    ImportLog,
    WithholdingTaxCert,
    BugReport,
    BugReportImage,
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
from .utils_pdf import link_callback, generate_wht_pdf_4_copies
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
from .tasks import run_import_background # Import the function from step 2
from .utils_llm import chat as llm_chat, help_ask as llm_help_ask, suggest_product_matches, LLMUnavailable
from .utils_dashboard import (
    resolve_date_range,
    get_kpi_summary,
    get_sales_trend,
    get_top_skus,
    get_purchase_vs_sales,
    get_stock_alerts,
)


def _apply_cancel_suffix(obj, fields):
    """Suffix specified fields with -Cancelled-DDMMYYHHMMSSffffff to free up unique keys."""
    now = timezone.localtime()
    suffix = f"-Cancelled-{now.strftime('%d%m%y%H%M%S')}{now.microsecond:06d}"
    for field_name in fields:
        val = getattr(obj, field_name, None)
        if val and '-Cancelled-' not in val:
            max_len = obj._meta.get_field(field_name).max_length or 255
            # Truncate original value first so suffix is never cut off
            setattr(obj, field_name, val[:max_len - len(suffix)] + suffix)


def _reverse_po_stock(po):
    """Cancel PO → subtract back the qty that was added when PO was created."""
    for item in po.purchase_items.select_for_update().order_by('id'):
        if item.remaining_quantity < item.quantity:
            raise Exception(
                f"ไม่สามารถยกเลิก: สินค้า '{item.product.name}' มีการขายไปแล้วบางส่วน "
                f"(เหลือ {item.remaining_quantity}/{item.quantity}). "
                f"กรุณายกเลิกใบขายที่ใช้ batch นี้ก่อน"
            )
        # Use .update() to bypass PurchaseItem.save() which triggers PO recalc cascade
        PurchaseItem.objects.filter(pk=item.pk).update(remaining_quantity=item.remaining_quantity - item.quantity)


def _restore_invoice_stock(invoice):
    """Cancel Invoice → add qty back to the source purchase batch."""
    for inv_item in invoice.invoice_items.select_related('purchase_item').order_by('id'):
        if inv_item.purchase_item_id:
            # Use .update() to bypass PurchaseItem.save() which triggers PO recalc cascade
            PurchaseItem.objects.select_for_update().filter(pk=inv_item.purchase_item_id).update(
                remaining_quantity=F('remaining_quantity') + inv_item.quantity
            )


def _apply_cancellation(obj, request, suffix_fields, stock_reverser):
    """Orchestrate cancellation: set audit fields → suffix keys → save → reverse stock."""
    obj.cancelled_at = timezone.now()
    obj.cancelled_by = request.user
    obj.cancel_reason = request.POST.get('cancel_reason', '')[:255]
    _apply_cancel_suffix(obj, suffix_fields)
    obj.save()
    stock_reverser(obj)




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
    return render(request, 'help.html')


@login_required
def help_ask_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json as _json
    try:
        body = _json.loads(request.body)
    except _json.JSONDecodeError:
        return JsonResponse({'error': 'invalid JSON'}, status=400)
    question = body.get('question', '').strip()
    if not question:
        return JsonResponse({'error': 'question required'}, status=400)
    try:
        result = llm_help_ask(question)
        return JsonResponse(result)
    except LLMUnavailable as e:
        from django.conf import settings as dj_settings
        resp = {'degraded': True, 'answer': 'ขออภัย ระบบ AI ไม่พร้อมใช้งานตอนนี้ กรุณาดูคำตอบในคู่มือด้านบนได้เลย'}
        if dj_settings.DEBUG:
            resp['debug_reason'] = str(e)
        return JsonResponse(resp)


# ─── Dashboard ──────────────────────────────────────────────────────────────

@login_required
def dashboard_view(request):
    companies = Company.objects.filter(is_active=True).order_by('name')
    return render(request, 'api/dashboard.html', {'companies': companies})


@login_required
def dashboard_kpi_summary(request):
    company_id = request.GET.get('company') or None
    period = request.GET.get('period', 'this_month')
    from_date_str = request.GET.get('from')
    to_date_str = request.GET.get('to')
    from_date_obj = None
    to_date_obj = None
    if from_date_str:
        try:
            from datetime import date
            from_date_obj = date.fromisoformat(from_date_str)
        except ValueError:
            pass
    if to_date_str:
        try:
            from datetime import date
            to_date_obj = date.fromisoformat(to_date_str)
        except ValueError:
            pass
    start, end = resolve_date_range(period, from_date_obj, to_date_obj)
    data = get_kpi_summary(company_id=company_id, from_date=start, to_date=end)
    return JsonResponse(data)


@login_required
def dashboard_sales_trend(request):
    company_id = request.GET.get('company') or None
    try:
        days = int(request.GET.get('days', 30))
    except ValueError:
        days = 30
    data = get_sales_trend(company_id=company_id, days=days)
    return JsonResponse(data, safe=False)


@login_required
def dashboard_top_skus(request):
    company_id = request.GET.get('company') or None
    period = request.GET.get('period', 'this_month')
    from_date_str = request.GET.get('from')
    to_date_str = request.GET.get('to')
    from_date_obj = to_date_obj = None
    if from_date_str:
        try:
            from datetime import date
            from_date_obj = date.fromisoformat(from_date_str)
        except ValueError:
            pass
    if to_date_str:
        try:
            from datetime import date
            to_date_obj = date.fromisoformat(to_date_str)
        except ValueError:
            pass
    start, end = resolve_date_range(period, from_date_obj, to_date_obj)
    try:
        limit = int(request.GET.get('limit', 10))
    except ValueError:
        limit = 10
    data = get_top_skus(company_id=company_id, from_date=start, to_date=end, limit=limit)
    return JsonResponse(data, safe=False)


@login_required
def dashboard_purchase_vs_sales(request):
    company_id = request.GET.get('company') or None
    try:
        months = int(request.GET.get('months', 6))
    except ValueError:
        months = 6
    data = get_purchase_vs_sales(company_id=company_id, months=months)
    return JsonResponse(data, safe=False)


@login_required
def dashboard_stock_alerts(request):
    company_id = request.GET.get('company') or None
    try:
        threshold = int(request.GET.get('threshold', 5))
    except ValueError:
        threshold = 5
    data = get_stock_alerts(company_id=company_id, threshold=threshold)
    return JsonResponse(data, safe=False)


# ─── Bug / Feature Request ───────────────────────────────────────────────────

@login_required
def bug_report_chat(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json as _json
    try:
        body = _json.loads(request.body)
    except _json.JSONDecodeError:
        return JsonResponse({'degraded': True})
    history = body.get('history', [])
    message = body.get('message', '').strip()
    if not message:
        return JsonResponse({'degraded': True})
    try:
        result = llm_chat(history, message)
        return JsonResponse(result)
    except LLMUnavailable as e:
        from django.conf import settings as dj_settings
        resp = {'degraded': True}
        if dj_settings.DEBUG:
            resp['debug_reason'] = str(e)
        return JsonResponse(resp)


@login_required
def bug_report_upload_image(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    image_file = request.FILES.get('image')
    if not image_file:
        return JsonResponse({'error': 'no image'}, status=400)
    img = BugReportImage.objects.create(
        image=image_file,
        session_key=request.session.session_key or '',
    )
    return JsonResponse({'id': img.pk, 'url': img.image.url})


@login_required
def bug_report_submit(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    import json as _json
    try:
        body = _json.loads(request.body)
    except _json.JSONDecodeError:
        return JsonResponse({'error': 'invalid JSON'}, status=400)

    title = body.get('title', '').strip()
    summary = body.get('summary', '').strip()
    report_type = body.get('type', 'BUG')
    conversation = body.get('conversation', [])
    is_degraded = body.get('degraded', False)
    image_ids = body.get('image_ids', [])

    if not title or not summary:
        return JsonResponse({'error': 'title and summary required'}, status=400)

    report = BugReport.objects.create(
        title=title,
        summary=summary,
        report_type=report_type if report_type in ('BUG', 'FEATURE') else 'BUG',
        conversation=conversation,
        degraded=bool(is_degraded),
        created_by=request.user,
    )

    # Link uploaded images; delete orphans from this session
    session_key = request.session.session_key or ''
    if image_ids:
        BugReportImage.objects.filter(pk__in=image_ids).update(bug_report=report, session_key='')
    # Clean up other uploads from this session that weren't chosen
    if session_key:
        BugReportImage.objects.filter(session_key=session_key, bug_report__isnull=True).delete()

    return JsonResponse({'id': report.pk, 'url': f'/bug-reports/{report.pk}/'})


@login_required
def bug_report_list(request):
    status_filter = request.GET.get('status', '')
    if request.user.is_staff:
        qs = BugReport.objects.all()
    else:
        qs = BugReport.objects.filter(created_by=request.user)
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'api/bug_reports/list.html', {
        'reports': qs,
        'status_filter': status_filter,
    })


@login_required
def bug_report_detail(request, pk):
    if request.user.is_staff:
        report = get_object_or_404(BugReport, pk=pk)
    else:
        report = get_object_or_404(BugReport, pk=pk, created_by=request.user)
    return render(request, 'api/bug_reports/detail.html', {
        'report': report,
        'status_choices': BugReport.STATUS_CHOICES,
    })


@login_required
def bug_report_update_status(request, pk):
    if not request.user.is_staff:
        return JsonResponse({'error': 'forbidden'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    report = get_object_or_404(BugReport, pk=pk)
    new_status = request.POST.get('status')
    admin_notes = request.POST.get('admin_notes', '')
    if new_status in dict(BugReport.STATUS_CHOICES):
        report.status = new_status
    report.admin_notes = admin_notes
    if new_status == 'RESOLVED' and not report.resolved_at:
        from django.utils import timezone as tz
        report.resolved_at = tz.now()
    report.save()
    messages.success(request, 'อัปเดตสถานะเรียบร้อยแล้ว')
    return redirect('bug_report_detail', pk=pk)


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Username หรือ Password ไม่ถูกต้อง')
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')


# ─── Global Search ───────────────────────────────────────────────────────────

@login_required
def global_search_view(request):
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({
            'products': [], 'vendors': [], 'invoices': [], 'purchases': [], 'companies': []
        })

    def _fmt_products():
        qs = Product.objects.filter(
            Q(sku__icontains=q) | Q(name__icontains=q) | Q(category__icontains=q)
        ).order_by('-created_at')[:5]
        return [{'id': p.pk, 'label': f'{p.sku} — {p.name}', 'url': f'/products/edit/{p.pk}/'} for p in qs]

    def _fmt_vendors():
        qs = Vendor.objects.filter(
            Q(name__icontains=q) | Q(phone__icontains=q)
        ).order_by('-created_at')[:5]
        return [{'id': v.pk, 'label': v.name, 'url': f'/vendors/edit/{v.pk}/'} for v in qs]

    def _fmt_invoices():
        qs = Invoice.objects.filter(
            Q(invoice_number__icontains=q) | Q(recipient_name__icontains=q) | Q(vendor__name__icontains=q)
        ).order_by('-invoice_date')[:5]
        return [{'id': i.pk, 'label': f'{i.invoice_number} — {i.recipient_name or ""}', 'url': f'/invoices/edit/{i.pk}/'} for i in qs]

    def _fmt_purchases():
        qs = PurchaseOrder.objects.filter(
            Q(po_number__icontains=q) | Q(vendor__name__icontains=q)
        ).order_by('-order_date')[:5]
        return [{'id': p.pk, 'label': f'{p.po_number} — {p.vendor.name}', 'url': f'/purchases/edit/{p.pk}/'} for p in qs]

    def _fmt_companies():
        qs = Company.objects.filter(name__icontains=q).order_by('name')[:5]
        return [{'id': c.pk, 'label': c.name, 'url': f'/companies/{c.pk}/edit/'} for c in qs]

    return JsonResponse({
        'products': _fmt_products(),
        'vendors': _fmt_vendors(),
        'invoices': _fmt_invoices(),
        'purchases': _fmt_purchases(),
        'companies': _fmt_companies(),
    })

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
    old_status = po_instance.status if is_editing else None

    # --- RULE 1: If CANCELLED -> Completely Locked (Read-Only) ---
    if is_editing and po_instance.status == 'CANCELLED': # 'Cancelled' in Thai
        # If user tries to POST (Save) to a cancelled order, block it
        if request.method == 'POST':
            messages.error(request, "Cannot edit a Cancelled order.")
            return redirect('purchase_edit', pk=pk) # Reload page

    # 2. Handle POST (Save Data)
    if request.method == 'POST':
        form = PurchaseOrderForm(request.POST, request.FILES, instance=po_instance)
        formset = PurchaseItemFormSet(request.POST, request.FILES, instance=po_instance)

        if form.is_valid() and formset.is_valid():
            # --- RULE 2: If 'PAID' -> Allow ONLY 'CANCELLED' or Adding Attachments ---
            is_paid = is_editing and po_instance.status == 'PAID'
            new_status = form.cleaned_data.get('status')
            has_new_files = bool(request.FILES.getlist('attachments'))
            
            # If it's PAID and they changed something other than status to CANCELLED 
            # (Note: adding files is handled separately below)
            if is_paid and new_status != 'CANCELLED':
                # Check if any other data changed besides status? 
                # ModelForm.has_changed() checks all fields.
                # If they ONLY added files, we want to allow it.
                # But Django's form.save() will save everything.
                # To be safe, if it's PAID, we only allow saving if status is CANCELLED OR they are just adding files.
                # However, the user wants the record to update.
                pass 

            try:
                with transaction.atomic():
                    # A. Save Header
                    po = form.save(commit=False)
                    if not is_editing:
                        po.created_by = request.user

                    just_cancelled = is_editing and (new_status == 'CANCELLED' and old_status != 'CANCELLED')

                    if just_cancelled:
                        wht = getattr(po_instance, 'wht_cert', None)
                        if wht and wht.status == 'ISSUED':
                            raise Exception(
                                f"ไม่สามารถยกเลิก: มีใบหัก ณ ที่จ่ายสถานะ ISSUED ผูกอยู่ "
                                f"(เล่ม {wht.book_number} เลขที่ {wht.cert_number}). กรุณาจัดการ WHT ก่อน"
                            )
                        _apply_cancellation(po, request,
                                            suffix_fields=['po_number', 'tax_sequence_number'],
                                            stock_reverser=_reverse_po_stock)
                        messages.success(request, "ยกเลิกรายการซื้อเรียบร้อย — Stock ถูกลดกลับแล้ว")
                        return redirect('purchase_list')

                    po.save()

                    # B. Save Items
                    formset.instance = po
                    formset.save()

                    # B2. Save Attachments (Always process if present)
                    files = request.FILES.getlist('attachments')
                    for f in files:
                        PurchaseAttachment.objects.create(purchase_order=po, file=f)
                    
                    # C. Recalculate Totals
                    po.calculate_totals()
                    
                    if files:
                        messages.success(request, f"เพิ่มไฟล์แนบ {len(files)} ไฟล์ และบันทึกข้อมูลเรียบร้อยแล้ว")
                    else:
                        messages.success(request, f"บันทึกข้อมูล '{po.po_number}' เรียบร้อยแล้ว")
                        
                    return redirect('purchase_list')
            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาดในการบันทึก: {str(e)}")
        else:
            # Better error reporting
            for error in form.non_field_errors():
                messages.error(request, f"Form error: {error}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            
            if not formset.is_valid():
                for error in formset.non_form_errors():
                    messages.error(request, f"Items error: {error}")
                for i, f in enumerate(formset.forms):
                    for field, errors in f.errors.items():
                        for error in errors:
                            messages.error(request, f"รายการที่ {i+1} - {field}: {error}")
    else:
        form = PurchaseOrderForm(instance=po_instance)
        formset = PurchaseItemFormSet(instance=po_instance)

    # 3. List View Logic (If viewing list)
    orders = PurchaseOrder.objects.all().order_by('-order_date')
    if request.GET.get('show_cancelled') != '1':
        orders = orders.exclude(status='CANCELLED')
    
    # Simple Filters
    if request.GET.get('q'):
        q = request.GET.get('q')
        orders = orders.filter(Q(po_number__icontains=q) | Q(vendor__name__icontains=q))

    context = {
        'form': form,
        'formset': formset,
        'orders': orders,
        'is_editing': is_editing,
        'editing_po': po_instance,
        'attachments': po_instance.attachments.all() if po_instance else []
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
    old_status = invoice_instance.status if is_editing else None

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
                        if not invoice.company:
                            invoice.company = Company.objects.first()

                    new_status = form.cleaned_data.get('status')
                    just_cancelled = is_editing and (new_status == 'CANCELLED' and old_status != 'CANCELLED')

                    if just_cancelled:
                        _apply_cancellation(invoice, request,
                                            suffix_fields=['invoice_number', 'tax_sequence_number'],
                                            stock_reverser=_restore_invoice_stock)
                        messages.success(request, "ยกเลิกใบกำกับเรียบร้อย — Stock คืนกลับให้แล้ว")
                        return redirect('invoice_list')

                    invoice.save()

                    # --- B. Process Items ---
                    # Use a dictionary to track batch updates in memory before final save
                    # to ensure multiple items for the same batch work correctly.
                    # Dictionary structure: {purchase_item_id: purchase_item_object}
                    batch_cache = {}

                    def get_locked_batch(batch_id):
                        if batch_id not in batch_cache:
                            batch_cache[batch_id] = PurchaseItem.objects.select_for_update().get(id=batch_id)
                        return batch_cache[batch_id]

                    # B1+B2. Call save(commit=False) first — this populates
                    # formset.deleted_objects and returns new/changed items.
                    items_to_save = formset.save(commit=False)

                    # B1. Handle Deletions (Restore Stock)
                    for obj in formset.deleted_objects:
                        if obj.pk and obj.purchase_item:
                            batch = get_locked_batch(obj.purchase_item.id)
                            batch.remaining_quantity += obj.quantity
                        obj.delete()
                    
                    for item in items_to_save:
                        selected_product = item.product
                        
                        # --- SKIP STOCK LOGIC FOR IMPORTED ITEMS WITHOUT PRODUCT ---
                        if not selected_product:
                            item.invoice = invoice
                            item.save()
                            continue

                        # If editing an existing item, restore its original stock first
                        if item.pk:
                            original_item = InvoiceItem.objects.get(pk=item.pk)
                            if original_item.purchase_item:
                                old_batch = get_locked_batch(original_item.purchase_item.id)
                                old_batch.remaining_quantity += original_item.quantity

                        # --- SCENARIO 1: User left Batch BLANK (Auto-Assign FIFO) ---
                        if not item.purchase_item:
                            requested_qty = item.quantity
                            
                            # Find all batches for this product with stock, ordered by ID (oldest first)
                            # We must exclude the cache updates? No, better to fetch all and then adjust from cache.
                            available_batches = PurchaseItem.objects.filter(
                                product=selected_product, 
                                remaining_quantity__gt=0
                            ).select_for_update().order_by('id')

                            # We need to handle splitting one line item into multiple batches if one isn't enough.
                            # BUT the model only allows 1 batch per InvoiceItem.
                            # So for now, we find the first batch that can satisfy the WHOLE amount.
                            # In a more advanced system, we would create multiple InvoiceItems.
                            
                            found_batch = None
                            for b in available_batches:
                                # Sync with cache if exists
                                if b.id in batch_cache:
                                    b.remaining_quantity = batch_cache[b.id].remaining_quantity
                                
                                if b.remaining_quantity >= requested_qty:
                                    found_batch = b
                                    batch_cache[b.id] = b
                                    break
                            
                            if not found_batch:
                                raise Exception(f"No single batch has enough stock for {selected_product.name} (Need {requested_qty})")
                            
                            item.purchase_item = found_batch
                            found_batch.remaining_quantity -= requested_qty

                        # --- SCENARIO 2: User SELECTED a specific Batch ---
                        else:
                            selected_batch = get_locked_batch(item.purchase_item.id)
                            
                            if selected_batch.product != selected_product:
                                raise Exception(f"Mismatch: Batch {selected_batch} does not belong to product {selected_product.name}")
                            
                            if item.quantity > selected_batch.remaining_quantity:
                                raise Exception(f"Not enough stock in selected batch {selected_batch.id}. Available: {selected_batch.remaining_quantity}, Requested: {item.quantity}")

                            selected_batch.remaining_quantity -= item.quantity
                            item.purchase_item = selected_batch

                        item.invoice = invoice
                        item.save()

                    # Save all modified batches
                    for batch in batch_cache.values():
                        batch.save()
                    
                    # --- D. Final Totals ---
                    invoice.calculate_totals()
                    
                    messages.success(request, "บันทึกใบกำกับภาษีเรียบร้อยแล้ว")
                    return redirect('invoice_list')

            except Exception as e:
                messages.error(request, f"เกิดข้อผิดพลาด: {str(e)}")
        else:
            messages.error(request, "กรุณาตรวจสอบข้อมูลในฟอร์ม")
    
    # 3. Handle GET Request
    else:
        form = InvoiceForm(instance=invoice_instance)
        formset = InvoiceItemFormSet(instance=invoice_instance)

    # 4. Fetch Recent Data
    invoices = Invoice.objects.select_related('vendor').order_by('-invoice_date', '-created_at')
    if request.GET.get('show_cancelled') != '1':
        invoices = invoices.exclude(status='CANCELLED')

    if request.GET.get('q'):
        q = request.GET.get('q')
        invoices = invoices.filter(Q(invoice_number__icontains=q) | Q(vendor__name__icontains=q))
    
    invoices = invoices[:1000]

    context = {
        'form': form,
        'formset': formset,
        'invoices': invoices,
        'is_editing': is_editing,
        'editing_invoice': invoice_instance,
    }
    return render(request, 'invoice_form.html', context)

@login_required
def platform_import_view(request):
    # Fetch History for the table
    import_history = ImportLog.objects.filter(user=request.user).order_by('-created_at')[:10]
    companies = Company.objects.filter(is_active=True)

    context = {
        'page_title': 'Platform Data Import',
        'companies': companies,
        'import_history': import_history # Pass history to template
    }

    if request.method == 'POST':
        uploaded_file = request.FILES.get('import_file')
        platform = request.POST.get('platform')
        company_id = request.POST.get('company_id')

        if not uploaded_file or not platform or not company_id:
            messages.error(request, "Missing data.")
            return redirect('platform_import')

        # 1. Save file temporarily
        fs = FileSystemStorage()
        clean_name = f"bg_{platform}_{uploaded_file.name.replace(' ', '_')}"
        filename = fs.save(clean_name, uploaded_file)
        file_path = fs.path(filename)

        # 2. Create Log Entry (PENDING)
        log = ImportLog.objects.create(
            user=request.user,
            platform=platform,
            filename=uploaded_file.name,
            status='PENDING'
        )

        # 3. Start Background Thread
        # We pass arguments so the thread can work independently
        thread = threading.Thread(
            target=run_import_background,
            args=(log.id, file_path, company_id, request.user.id, platform)
        )
        thread.daemon = True # Ensures thread dies if main process dies
        thread.start()

        # 4. Immediate Response
        messages.info(request, "Import started in background! Check the history table below for status.")
        return redirect('platform_import')

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


@login_required
def product_mapping_suggest_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    import json as _json
    from django.conf import settings as dj_settings

    try:
        body = _json.loads(request.body)
        items = body.get('items', [])
    except (_json.JSONDecodeError, Exception):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    if not items:
        return JsonResponse({'suggestions': {}, 'degraded': False})

    candidates = list(Product.objects.filter(is_active=True).values('id', 'sku', 'name'))

    try:
        result = suggest_product_matches(items, candidates)
        return JsonResponse(result)
    except LLMUnavailable as e:
        resp = {'degraded': True, 'suggestions': {}}
        if dj_settings.DEBUG:
            resp['debug_reason'] = str(e)
        return JsonResponse(resp)


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
    
    if not invoice.is_printed:
        invoice.is_printed = True
        invoice.status = 'BILLED'
    invoice.print_datetime = timezone.now()
    invoice.save(update_fields=['is_printed', 'print_datetime', 'status'])
    
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

from django.http import JsonResponse
from django.db.models import Q
from django.contrib.auth.decorators import login_required

@login_required
def check_duplicate_po_fields(request):
    """
    API endpoint to check if po_number or tax_sequence_number already exists,
    excluding the current purchase order (if editing).
    """
    po_number = request.GET.get('po_number')
    tax_sequence_number = request.GET.get('tax_sequence_number')
    current_po_id = request.GET.get('current_po_id')
    company_id = request.GET.get('company_id')

    queryset = PurchaseOrder.objects.all()
    if current_po_id:
        queryset = queryset.exclude(id=current_po_id)
    if company_id:
        queryset = queryset.filter(company_id=company_id)

    duplicate_po = False
    duplicate_tax = False

    if po_number:
        duplicate_po = queryset.filter(po_number=po_number).exists()
    if tax_sequence_number:
        duplicate_tax = queryset.filter(tax_sequence_number=tax_sequence_number).exists()

    return JsonResponse({
        'duplicate_po_number': duplicate_po,
        'duplicate_tax_sequence': duplicate_tax
    })

def wht_cert_list_view(request):
    # ... (Keep your Fetch Lists code same as before) ...
    companies = Company.objects.filter(is_active=True)
    vendors = Vendor.objects.filter(is_active=True)
    transactions = Transaction.objects.filter(type='EXPENSE', wht_cert__isnull=True).order_by('-transaction_date')
    purchase_orders = PurchaseOrder.objects.filter(status='PAID', wht_cert__isnull=True).order_by('-order_date')
    certs = WithholdingTaxCert.objects.all().order_by('-created_at')[:20]
    
    context = {
        'companies': companies,
        'vendors': vendors,
        'transactions': transactions, # Ensure this is passed
        'purchase_orders': purchase_orders,
        'certs': certs,
        'income_choices': WithholdingTaxCert.INCOME_TYPE_CHOICES,
    }

    if request.method == 'POST':
        # --- DEBUG: Remove try/except block to see the REAL error on screen ---
        # try:
        
        # 1. Get Basic Data

        company_id = request.POST.get('company_id')
        source_type = request.POST.get('source_type') # 'manual', 'po', 'trans'
        source_id = request.POST.get('source_id')
        user_cert_number = request.POST.get('cert_number', '').strip()
        
        # 2. Parse Date Correctly (Fixes Bug #3)
        date_str = request.POST.get('date_issued')
        date_obj = timezone.now().date()
        if date_str:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

        # 3. Initialize Object
        cert = WithholdingTaxCert()
        cert.company_id = company_id
        cert.date_issued = date_obj 
        
        # Fix Bug #3: Force None if empty string so Model logic triggers
        if user_cert_number:
            cert.cert_number = user_cert_number
        else:
            cert.cert_number = None 
            
        cert.income_type = request.POST.get('income_type')
        cert.income_description = request.POST.get('income_description', '')
        
        # 4. Handle Amounts
        cert.amount_before_tax = float(request.POST.get('amount_before_tax', 0).replace(',', ''))
        cert.tax_rate = float(request.POST.get('tax_rate', 3))
        cert.tax_amount = float(request.POST.get('tax_amount', 0).replace(',', ''))
        
        # 5. Fix Bug: Robust Linking Logic
        if source_type == 'po' and source_id:
            po = PurchaseOrder.objects.get(id=source_id)
            cert.purchase_order = po
            # PO always has a vendor, so this is safe
            cert.vendor = po.vendor 
            
        elif source_type == 'trans' and source_id:
            trans = Transaction.objects.get(id=source_id)
            cert.transaction = trans
            
            # --- FIX HERE: Handle Transactions without Vendor ---
            if trans.vendor:
                cert.vendor = trans.vendor
            else:
                # If Transaction has no vendor, grab from the form dropdown
                vendor_id = request.POST.get('vendor_id')
                if not vendor_id:
                    raise ValueError("รายการจ่ายนี้ไม่มี Vendor ในระบบ กรุณาเลือก Vendor ในแบบฟอร์ม")
                cert.vendor_id = vendor_id
                
        else:
            # Manual Mode
            vendor_id = request.POST.get('vendor_id')
            if not vendor_id:
                    raise ValueError("กรุณาเลือกผู้ถูกหักภาษี (Vendor)")
            cert.vendor_id = vendor_id

        # 6. Save & Generate
        is_issue = 'btn_issue' in request.POST
        cert.status = 'ISSUED' if is_issue else 'DRAFT'
        cert.save()

        if is_issue:
            pdf_url = generate_wht_pdf_4_copies(cert)
            messages.success(request, f"Issued Successfully: {cert.cert_number}")
            return HttpResponseRedirect(pdf_url)
        else:
            messages.info(request, "Draft Saved.")
            return redirect('wht_list')

        # except Exception as e:
        #     messages.error(request, f"Error: {str(e)}")
        #     return redirect('wht_list')

    return render(request, 'wht_form.html', context)

# API เพื่อดึงข้อมูลเมื่อผู้ใช้เลือก PO หรือ Transaction ใน Dropdown
def get_source_details(request):
    source_type = request.GET.get('type')
    source_id = request.GET.get('id')
    
    data = {'amount': 0, 'vendor_id': None, 'vendor_name': ''}
    
    if source_type == 'po':
        obj = PurchaseOrder.objects.get(id=source_id)
        data['amount'] = obj.subtotal # ยอดก่อนภาษี
        data['vendor_id'] = obj.vendor.id
        data['vendor_name'] = obj.vendor.name
    elif source_type == 'trans':
        obj = Transaction.objects.get(id=source_id)
        data['amount'] = obj.amount
        data['vendor_id'] = obj.vendor.id if obj.vendor else None
        data['vendor_name'] = obj.vendor.name if obj.vendor else ''
        
    return JsonResponse(data)


# ---------------------------------------------------------------------------
# VAT Orders Tracking APIs (Standalone)
# ---------------------------------------------------------------------------
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Q, Sum, Count
from .models import VatOrderBuy, VatOrderBuyItem, VatOrderSaleItem
from .serializers import VatOrderBuyItemSerializer, VatOrderSaleItemSerializer
from .utils_vat_import import process_vat_buy_import, process_vat_sale_import


class VatImportDataView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        file_obj = request.FILES.get('file')
        import_type = request.data.get('type')

        if not file_obj:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

        if import_type == 'buy':
            result = process_vat_buy_import(file_obj)
        elif import_type == 'sale':
            result = process_vat_sale_import(file_obj)
        else:
            return Response({'error': 'Invalid import type'}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result, status=status.HTTP_200_OK)


class VatReportView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        vat_company = request.query_params.get('vat_company')
        product_query = request.query_params.get('q')

        queryset = VatOrderBuyItem.objects.select_related('vat_order').all()

        if start_date:
            queryset = queryset.filter(vat_order__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(vat_order__date__lte=end_date)
        if vat_company and vat_company.lower() != 'all':
            queryset = queryset.filter(vat_order__supplier_name__icontains=vat_company)
        if product_query:
            queryset = queryset.filter(
                Q(product_name__icontains=product_query) |
                Q(serial_no__icontains=product_query)
            )

        queryset = queryset.order_by('vat_order__date', 'vat_order__document_no')
        serializer = VatOrderBuyItemSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, format=None):
        item_type = request.data.get('item_type')
        item_id = request.data.get('id')

        if item_type == 'buy':
            try:
                item = VatOrderBuyItem.objects.get(id=item_id)
            except VatOrderBuyItem.DoesNotExist:
                return Response({'error': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)

            if 'vat_company' in request.data:
                item.vat_company = request.data['vat_company']
            if 'payment_method_in' in request.data:
                item.payment_method_in = request.data['payment_method_in']
            if 'bank_in' in request.data:
                item.bank_in = request.data['bank_in']
            item.save()

        elif item_type == 'sale':
            try:
                item = VatOrderSaleItem.objects.get(id=item_id)
            except VatOrderSaleItem.DoesNotExist:
                return Response({'error': 'Item not found'}, status=status.HTTP_404_NOT_FOUND)

            if 'payment_method_out' in request.data:
                item.payment_method_out = request.data['payment_method_out']
            if 'company_out' in request.data:
                item.company_out = request.data['company_out']
            item.save()
        else:
            return Response({'error': 'Invalid item type'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class VatExportExcelView(APIView):
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        from django.http import HttpResponse
        from api.utils_vat_export import export_vat_report

        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        vat_company = request.query_params.get('vat_company')
        product_query = request.query_params.get('q')

        queryset = VatOrderBuyItem.objects.select_related('vat_order').all()

        if start_date:
            queryset = queryset.filter(vat_order__date__gte=start_date)
        if end_date:
            queryset = queryset.filter(vat_order__date__lte=end_date)
        if vat_company and vat_company.lower() != 'all':
            queryset = queryset.filter(vat_order__supplier_name__icontains=vat_company)
        if product_query:
            queryset = queryset.filter(
                Q(product_name__icontains=product_query) |
                Q(serial_no__icontains=product_query)
            )

        queryset = queryset.order_by('vat_order__date', 'vat_order__document_no')

        return export_vat_report(queryset)


@login_required
def vat_tracking_view(request):
    return render(request, 'vat_tracking.html')


@login_required
def vat_buy_summary_view(request):
    return render(request, 'vat_buy_summary.html')


class VatBuyOrderSummaryView(APIView):
    """Returns VatOrderBuy headers with aggregated totals for the document-level summary view."""
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        filter_date = request.query_params.get('date')
        vat_status = request.query_params.get('vat_status')
        product_query = request.query_params.get('q')

        queryset = VatOrderBuy.objects.annotate(
            total_buy_amount=Sum('items__purchase_price'),
            item_count=Count('items')
        )

        if vat_status == 'vat_only':
            queryset = queryset.filter(Q(supplier_name__iendswith='/kit') | Q(supplier_name__iendswith='/s16'))
        elif vat_status == 'non_vat':
            queryset = queryset.exclude(Q(supplier_name__iendswith='/kit') | Q(supplier_name__iendswith='/s16'))

        if filter_date:
            queryset = queryset.filter(date=filter_date)
        if product_query:
            queryset = queryset.filter(items__product_name__icontains=product_query).distinct()

        queryset = queryset.order_by('-date', '-document_no')

        data = []
        for order in queryset:
            supplier = order.supplier_name or ''
            supplier_lower = supplier.lower().rstrip()
            is_vat = supplier_lower.endswith('/kit') or supplier_lower.endswith('/s16')

            data.append({
                'id': order.id,
                'document_no': order.document_no,
                'date': order.date.isoformat() if order.date else None,
                'supplier_name': supplier,
                'is_vat_company': is_vat,
                'total_buy_amount': float(order.total_buy_amount or 0),
                'item_count': order.item_count or 0,
            })

        return Response(data, status=status.HTTP_200_OK)


class VatBuySummaryExportExcelView(APIView):
    """Exports Document-level VAT Buy Summaries to Excel."""
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        from api.utils_vat_export import export_vat_buy_summary_report
        from django.http import HttpResponse

        filter_date = request.query_params.get('date')
        vat_status = request.query_params.get('vat_status')
        product_query = request.query_params.get('q')

        queryset = VatOrderBuy.objects.annotate(
            total_buy_amount=Sum('items__purchase_price'),
            item_count=Count('items')
        )

        if vat_status == 'vat_only':
            queryset = queryset.filter(Q(supplier_name__iendswith='/kit') | Q(supplier_name__iendswith='/s16'))
        elif vat_status == 'non_vat':
            queryset = queryset.exclude(Q(supplier_name__iendswith='/kit') | Q(supplier_name__iendswith='/s16'))

        if filter_date:
            queryset = queryset.filter(date=filter_date)
        if product_query:
            queryset = queryset.filter(items__product_name__icontains=product_query).distinct()

        queryset = queryset.order_by('-date', '-document_no')

        filepath, filename = export_vat_buy_summary_report(queryset)

        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = f'attachment; filename={filename}'
                return response
        else:
            return Response({'error': 'Export failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VatBuyOrderDetailView(APIView):
    """Returns items for a specific VatOrderBuy by its pk."""
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, format=None):
        try:
            order = VatOrderBuy.objects.get(pk=pk)
        except VatOrderBuy.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        items = VatOrderBuyItem.objects.filter(vat_order=order)
        serializer = VatOrderBuyItemSerializer(items, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


import csv
import urllib.request

@login_required
def invoice_excel_view(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    
    # Create workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Invoice_{invoice.invoice_number}"
    
    # Header format
    ws.append(["Company", "Invoice Number", "Date", "Customer", "Subtotal", "Tax", "Grand Total", "Status"])
    ws.append([
        invoice.company.name if invoice.company else "",
        invoice.invoice_number,
        invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else "",
        invoice.vendor.name if invoice.vendor else invoice.recipient_name,
        float(invoice.subtotal),
        float(invoice.tax_amount),
        float(invoice.grand_total),
        invoice.status
    ])

    ws.append([]) # empty row
    ws.append(["SKU", "Item Name", "Quantity", "Unit Price", "Total Price"])
    for item in invoice.invoice_items.all():
        ws.append([
            item.product.sku if item.product else item.sku,
            item.product.name if item.product else item.item_name,
            item.quantity,
            float(item.unit_price),
            float(item.total_price)
        ])
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.invoice_number}.xlsx"'
    wb.save(response)
    return response

@login_required
def sync_google_sheet_requests(request):
    SHEET_URL = "https://docs.google.com/spreadsheets/d/10vSZIeyigc74uTkXmAO3AxaG6TNFA6uGSb39udH7JgI/export?format=csv&id=10vSZIeyigc74uTkXmAO3AxaG6TNFA6uGSb39udH7JgI&gid=0"
    try:
        req = urllib.request.Request(SHEET_URL, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        lines = [l.decode('utf-8') for l in response.readlines()]
        reader = csv.reader(lines)
        
        # skip headers / empty rows until data (start at row 3, index 2)
        for _ in range(2):
            next(reader, None)
            
        sync_count = 0
        for row in reader:
            if len(row) < 8:
                continue
            # "ลำดับ หมายเลขคำสั่งซื้อ วันที่ ชื่อ สกุล ที่อยุ่ปัจจุบัน หมายเลขประจำตัวผู้เสียภาษี เบอร์โทร Email ช่องทางการสั่งซื้อ สถานะ"
            # 0: ลำดับ, 1: order id, 2: date, 3: name, 4: address, 5: tax_id, 6: phone
            order_id = row[1].strip()
            if not order_id:
                continue
                
            invoices = Invoice.objects.filter(platform_order_id=order_id)
            for inv in invoices:
                if not inv.tax_invoice_requested:
                    inv.tax_invoice_requested = True
                    inv.recipient_name = row[3].strip() if len(row) > 3 else inv.recipient_name
                    inv.recipient_address = row[4].strip() if len(row) > 4 else inv.recipient_address
                    inv.recipient_phone = row[6].strip() if len(row) > 6 else inv.recipient_phone
                    
                    if inv.vendor and len(row) > 5:
                        inv.vendor.tax_id = row[5].strip()
                        inv.vendor.save()
                    inv.save()
                    sync_count += 1
                    
        return JsonResponse({'success': True, 'count': sync_count, 'message': f'พบคำขอและซิงค์ข้อมูลแล้ว {sync_count} รายการ'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})