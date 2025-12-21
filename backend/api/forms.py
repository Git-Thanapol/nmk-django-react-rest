from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from .models import Vendor, Product, Transaction,PurchaseOrder, PurchaseItem, Product, Invoice, InvoiceItem,Company
from django.core.validators import FileExtensionValidator
from django import forms
from django import forms
from .models import PurchaseOrder, Company # <--- Make sure Company is imported

class VendorForm(forms.ModelForm):
    company_selection = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'list': 'company_list',
            'placeholder': 'เลือกบริษัท (เว้นว่างได้)...',
            'autocomplete': 'off'
        })
    )

    class Meta:
        model = Vendor
        fields = ['name', 'contact_person', 'phone', 'email', 'address', 'tax_id', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อผู้ขาย / บริษัท'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ชื่อผู้ติดต่อ'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '081-234-5678'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'vendor@email.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'ที่อยู่ผู้ขาย'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เลขประจำตัวผู้เสียภาษีอากรไม่ต้องมีขีด', 'maxlength': '13'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    # ADD THIS METHOD
    def __init__(self, *args, **kwargs):
        super(VendorForm, self).__init__(*args, **kwargs)
        # If we are editing an existing vendor (instance exists and has a company)
        if self.instance and self.instance.pk and self.instance.company:
            # Pre-fill the custom company_selection field
            self.fields['company_selection'].initial = self.instance.company.name

class ProductForm(forms.ModelForm):
    # Override category to allow custom input (Select or Type)
    category = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'list': 'category_list', 
            'placeholder': 'เลือกประเภท หรือ เพิ่มประเภทใหม่...',
            'autocomplete': 'off'
        })
    )

    class Meta:
        model = Product
        fields = ['sku', 'name', 'description', 'category', 'cost_price', 'selling_price', 'is_active', 'company']
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'รหัสสินค้า (SKU) ต้องไม่ซ้ำ'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ระบุชื่อสินค้า...'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'ระบุรายละเอียดสินค้า...'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'company': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'company': 'Company (Optional)',
            'sku': 'SKU Code'
        }

    def clean_sku(self):
        """Ensure SKU is unique, but allow the same SKU if we are editing the same instance."""
        sku = self.cleaned_data.get('sku')
        instance = self.instance
        
        # Check if SKU exists in other products
        qs = Product.objects.filter(sku=sku)
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
            
        if qs.exists():
            raise forms.ValidationError(f"SKU '{sku}' นี้มีอยู่ในระบบแล้ว กรุณาใช้รหัสอื่น.")
        return sku
    
class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['transaction_number', 'transaction_date', 'type', 'category', 'amount', 'reference', 'description','company','vendor']
        widgets = {
            'transaction_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ตัวอย่างเช่น .. TX-2024-001'}),
            'transaction_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'หมายเลขอ้างอิง / หมายเลขใบเสร็จ (ถ้ามี)'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'อธิบายรายละเอียด...'}),
            'company': forms.Select(attrs={'class': 'form-select'}),
            'vendor': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date to today if not editing
        self.fields['company'].queryset = Company.objects.filter(is_active=True)
        self.fields['vendor'].queryset = Vendor.objects.filter(is_active=True)
        if not self.instance.pk:

            from django.utils import timezone
            self.fields['transaction_date'].initial = timezone.now().date()

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['po_number', 'vendor', 'order_date', 'purchase_type', 'company', 
                  'expected_delivery_date', 'tax_include', 'tax_percent', 'notes', 
                  'status', 'tax_sender_date', 'tax_sequence_number']
        widgets = {
            'po_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ระบุรหัสคำสั่งซื้อ เช่น PO-2024-XXXX'}),
            'vendor': forms.Select(attrs={'class': 'form-select'}),
            'purchase_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'tax_include': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_tax_include'}),
            'tax_percent': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_tax_percent', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'tax_sequence_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ระบุเลขที่ลำดับภาษี'}),
            'company': forms.Select(attrs={'class': 'form-select'}),
            
            # Date Pickers
            'order_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'expected_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'tax_sender_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Filter Company Dropdown (Only Active Companies)
        # This overrides the default "All Companies" list
        self.fields['vendor'].queryset = Vendor.objects.filter(is_active=True)
        self.fields['company'].queryset = Company.objects.filter(is_active=True)

        # 2. Set default date (Your existing logic)
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['order_date'].initial = timezone.now().date()

class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = ['product', 'quantity', 'unit_cost']
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select product-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control qty', 'min': '1'}),
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control price', 'step': '1'}),
        }

# Logic: Link Parent (PurchaseOrder) to Child (PurchaseItem)
PurchaseItemFormSet = inlineformset_factory(
    PurchaseOrder, 
    PurchaseItem, 
    form=PurchaseItemForm,
    extra=1,       # Show 1 empty row by default
    can_delete=True # Allow deleting rows
)

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = [
            'invoice_number', 'vendor', 'invoice_date', 'platform_name', 'company',
            'status', 'tax_include', 'tax_percent', 'shipping_cost', 'notes', 
            'tax_sender_date', 'tax_sequence_number', 'saleperson'
        ]
        widgets = {
            'invoice_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'INV-2024-XXXX'}),
            'vendor': forms.Select(attrs={'class': 'form-select'}),
            'company': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'platform_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ระบุช่องทางการขาย'}),
            
            'tax_include': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_tax_include'}),
            'tax_percent': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_tax_percent', 'step': '0.01'}),
            'shipping_cost': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_shipping_cost', 'step': '0.01', 'value': '0.00'}),
            
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'tax_sequence_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ระบุเลขที่ลำดับภาษี'}),
            'saleperson': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ระบุชื่อผู้ขาย'}),

            # Date Pickers with YYYY-MM-DD enforcement
            'invoice_date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}, 
                format='%Y-%m-%d'
            ),
            'tax_sender_date': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'}, 
                format='%Y-%m-%d'
            ),
        }
        labels = {
            'status': 'Status',
            'platform_name': 'Platform / Channel',
            'vendor': 'Customer / Vendor',
        }
            
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter active companies and vendors
        self.fields['vendor'].queryset = Vendor.objects.filter(is_active=True)
        self.fields['company'].queryset = Company.objects.filter(is_active=True)

        # Set Initial Defaults
        if not self.instance.pk:
            self.fields['invoice_date'].initial = timezone.now().date()
            self.fields['status'].initial = 'DRAFT'  # Use key 'DRAFT', not label 'แบบร่าง'

class InvoiceItemCustomChoiceField(forms.ModelChoiceField):
    """Custom field to display detailed stock info in the dropdown"""
    def label_from_instance(self, obj):
        # Display: Product Name | PO Number | Cost | Remaining Stock
        return f"{obj.product.name} | PO: {obj.purchase_order.po_number} | Stock: {obj.remaining_quantity} | Cost: {obj.unit_cost}"

class InvoiceItemForm(forms.ModelForm):
    # 1. Product Field (User selects this first)
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select product-select'}),
        required=True
    )

    # 2. Batch Field (Optional - filtered by JS on frontend)
    purchase_item = forms.ModelChoiceField(
        queryset=PurchaseItem.objects.filter(remaining_quantity__gt=0),
        widget=forms.Select(attrs={'class': 'form-select batch-select'}),
        required=False, # Allow blank (Backend will handle auto-assign)
        empty_label="Auto-Assign (FIFO) or Select Batch"
    )

    class Meta:
        model = InvoiceItem
        fields = ['product', 'purchase_item', 'quantity', 'unit_price']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control qty', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control price', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Additional logic can be added here if needed
        # Mapping for batch-product logic will be handled in the template via JS/Loop

# The Formset remains the same
InvoiceItemFormSet = inlineformset_factory(
    Invoice, 
    InvoiceItem, 
    form=InvoiceItemForm,
    extra=1, 
    can_delete=True
)

class ImportFileForm(forms.Form):
    import_file = forms.FileField(
        label="Select Data File",
        help_text="Supported formats: .csv, .xlsx, .xls",
        validators=[FileExtensionValidator(allowed_extensions=['csv', 'xlsx', 'xls'])],
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.csv, .xlsx, .xls'})
    )
    # Hidden field to track which platform is being imported
    platform = forms.CharField(widget=forms.HiddenInput(), initial='tiktok')

class ReportFilterForm(forms.Form):
    REPORT_BASIS_CHOICES = [
        ('create_date', 'ตามวันที่เอกสาร (Document Date)'),
        ('tax_date', 'ตามวันที่ยื่นภาษี (Tax Filing Date)'),
    ]

    # Changed from ModelChoiceField to ChoiceField to support "All" manually
    company = forms.ChoiceField(
        choices=[], # Populated in __init__
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Select Company",
        required=True
    )
    
    report_basis = forms.ChoiceField(
        choices=REPORT_BASIS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Report Basis",
        initial='create_date'
    )
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Start Date"
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="End Date"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 1. Fetch companies
        companies = Company.objects.filter(is_active=True).order_by('name')
        
        # 2. Create Custom Choices: [('all', '--- All Companies ---'), (1, 'Company A'), ...]
        company_choices = [('all', '--- ทุกบริษัท (All Companies) ---')]
        company_choices += [(c.id, c.name) for c in companies]
        
        self.fields['company'].choices = company_choices

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'nick_name', 'tax_id', 'address', 'phone', 'email', 'is_active']
        labels = {
            'name': 'ชื่อบริษัท (จดทะเบียน)',
            'nick_name': 'ชื่อย่อ / ชื่อเรียก',
            'tax_id': 'เลขประจำตัวผู้เสียภาษี',
            'address': 'ที่อยู่บริษัท (สำหรับออกใบกำกับภาษี)',
            'phone': 'เบอร์โทรศัพท์',
            'email': 'อีเมล',
            'is_active': 'เปิดใช้งาน (Active)'
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น บริษัท เคไอที23 จำกัด'}),
            'nick_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'เช่น KIT23'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }