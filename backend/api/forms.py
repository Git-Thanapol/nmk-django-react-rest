from django import forms
from django.forms import inlineformset_factory
from .models import Customer, Vendor, Product, Transaction,PurchaseOrder, PurchaseItem, Product, Invoice, InvoiceItem

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        # Note: 'company' is excluded here as it's usually set automatically based on the logged-in user
        fields = ['name', 'tax_id', 'phone', 'email', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer or Company Name'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tax Identification ID'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '081-234-5678'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Billing/Shipping Address'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Customer / Company Name',
        } 

class VendorForm(forms.ModelForm):
    company_selection = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'list': 'company_list',
            'placeholder': 'Select existing or type new Company name...',
            'autocomplete': 'off'
        })
    )

    class Meta:
        model = Vendor
        fields = ['name', 'contact_person', 'phone', 'email', 'address', 'tax_id', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Vendor Name'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '081-234-5678'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'vendor@email.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Vendor Address'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tax ID'}),
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
            'placeholder': 'Select or type new category...',
            'autocomplete': 'off'
        })
    )

    class Meta:
        model = Product
        fields = ['sku', 'name', 'description', 'category', 'cost_price', 'selling_price', 'is_active', 'company']
        widgets = {
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique SKU'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Product details...'}),
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
            raise forms.ValidationError(f"SKU '{sku}' is already in use.")
        return sku
    
class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['transaction_number', 'transaction_date', 'type', 'category', 'amount', 'reference', 'description']
        widgets = {
            'transaction_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. TX-2024-001'}),
            'transaction_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ref / Receipt ID'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Details of expenditure or income...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date to today if not editing
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['transaction_date'].initial = timezone.now().date()


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = ['po_number', 'vendor', 'order_date', 'purchase_type', 
                  'expected_delivery_date', 'tax_include', 'tax_percent', 'notes', 'status']
        widgets = {
            'po_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PO-2024-XXXX'}),
            'vendor': forms.Select(attrs={'class': 'form-select'}),
            'order_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'purchase_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'tax_include': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_tax_include'}), # ID for JS
            'tax_percent': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_tax_percent', 'step': '0.01'}), # ID for JS
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date
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
            'unit_cost': forms.NumberInput(attrs={'class': 'form-control price', 'step': '0.01'}),
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
        fields = ['invoice_number', 'customer', 'invoice_date', 'selling_channel', 
                  'status', 'tax_include', 'tax_percent', 'shipping_cost', 'notes']
        widgets = {
            'invoice_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'INV-2024-XXXX'}),
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'invoice_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'selling_channel': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'tax_include': forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_tax_include'}),
            'tax_percent': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_tax_percent', 'step': '0.01'}),
            'shipping_cost': forms.NumberInput(attrs={'class': 'form-control', 'id': 'id_shipping_cost', 'step': '0.01', 'value': '0.00'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['invoice_date'].initial = timezone.now().date()

class InvoiceItemCustomChoiceField(forms.ModelChoiceField):
    """Custom field to display detailed stock info in the dropdown"""
    def label_from_instance(self, obj):
        # Display: Product Name | PO Number | Cost | Remaining Stock
        return f"{obj.product.name} | PO: {obj.purchase_order.po_number} | Stock: {obj.remaining_quantity} | Cost: {obj.unit_cost}"

class InvoiceItemForm(forms.ModelForm):
    # Replace standard select with our custom label field
    purchase_item = InvoiceItemCustomChoiceField(
        queryset=PurchaseItem.objects.none(), # Queryset set in __init__
        widget=forms.Select(attrs={'class': 'form-select stock-select'}),
        empty_label="Select Stock Batch..."
    )

    class Meta:
        model = InvoiceItem
        fields = ['purchase_item', 'quantity', 'unit_price']
        widgets = {
            'quantity': forms.NumberInput(attrs={'class': 'form-control qty', 'min': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': 'form-control price', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Logic to filter dropdown: Show items with stock > 0
        # If editing, we must ALSO include the currently selected item (even if stock is now 0)
        stock_qs = PurchaseItem.objects.filter(remaining_quantity__gt=0).select_related('product', 'purchase_order')
        
        if self.instance.pk and self.instance.purchase_item:
            # Add the current item back to the list so it doesn't disappear
            current_item_qs = PurchaseItem.objects.filter(pk=self.instance.purchase_item.pk)
            stock_qs = stock_qs | current_item_qs
            
        self.fields['purchase_item'].queryset = stock_qs.distinct().order_by('product__name')

InvoiceItemFormSet = inlineformset_factory(
    Invoice, 
    InvoiceItem, 
    form=InvoiceItemForm,
    extra=1, 
    can_delete=True
)