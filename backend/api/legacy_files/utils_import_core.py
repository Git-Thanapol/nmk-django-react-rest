import pandas as pd
from django.db import transaction
from decimal import Decimal, InvalidOperation
from django.contrib.auth.models import User
from django.utils import timezone
from ..models import Invoice, Company, InvoiceItem, ProductAlias
import os

# --- 1. SHARED HELPERS ---
def load_data(file_path):
    """Universal file loader"""
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == '.csv':
        # utf-8-sig handles BOM characters often found in Excel exports
        return pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)
    elif ext in ['.xls', '.xlsx']:
        return pd.read_excel(file_path, dtype=str)
    else:
        raise ValueError("Unsupported file format. Use CSV or Excel.")
    
def clean_decimal(val):
    """Safely converts currency strings (e.g., '1,200.50') to Decimal"""
    if pd.isna(val) or val == '': return Decimal('0.00')
    try:
        return Decimal(str(val).replace(',', '').replace('฿', '').strip())
        # Clean string
        # cleaned = str(val).replace(',', '').replace('฿', '').strip()
        # d = Decimal(cleaned)

        # # FAIL-SAFE: If the number is too big (likely an ID), return 0 or error
        # if d > Decimal('9999999999'): 
        #     print(f"WARNING: Suspiciously large number found: {d}. Treating as 0.")
        #     return Decimal('0.00') # Or raise specific error

        # return d
    except (ValueError, InvalidOperation):
        return Decimal('0.00')
    
# --- 2. THE UNIVERSAL IMPORTER ---
def universal_invoice_import(header_df, items_df, company_id, user_id, platform_name):
    """
    One function to rule them all. 
    It expects standard column names (standardized by the Processor functions).
    """
    print(f"--- Starting Import for {platform_name} ---")
    
    # Validation
    required_cols = ['order_id', 'total_amount', 'subtotal']
    if not all(col in header_df.columns for col in required_cols):
        return {"status": "error", "message": f"Header DF missing columns. Need: {required_cols}"}

    try:
        company = Company.objects.get(id=company_id)
        user = User.objects.get(id=user_id)
    except Exception as e:
        return {"status": "error", "message": str(e)}

    # Optimize Item Lookup
    if 'order_id' not in items_df.columns:
        return {"status": "error", "message": "Items DF missing 'order_id'"}
    
    items_df['order_id'] = items_df['order_id'].astype(str)
    items_grouped = items_df.groupby('order_id')

    success_count = 0
    errors = []
    
    # Import Loop
    records = header_df.fillna('').to_dict('records')
    
    # CHANGED: Use enumerate to track Excel Row Number
    for index, row in enumerate(records):
        try:
            # A. Prepare Data
            order_id = str(row.get('order_id', '')).strip()
            if not order_id: continue

            # order_id = order_id.strip()
            grand_total = clean_decimal(row.get('total_amount'))
            subtotal = clean_decimal(row.get('subtotal'))
            
            # Logic: Discount vs Shipping
            diff = subtotal - grand_total
            if diff >= 0:
                discount, shipping = diff, Decimal(0)
            else:
                discount, shipping = Decimal(0), abs(diff)


            # Logic: Tax (Backwards 7%)
            tax_rate = Decimal('7.00')
            base_ex_tax = grand_total / (Decimal(1) + (tax_rate / Decimal(100)))
            tax_amt = grand_total - base_ex_tax


            # discount = clean_decimal(discount)
            # shipping = clean_decimal(shipping)
            # tax_amt = clean_decimal(tax_amt)
            # Date
            inv_date = row.get('shipped_date')
            if not isinstance(inv_date, (pd.Timestamp, str)) or pd.isna(inv_date):
                inv_date = timezone.now()

            # B. Database Transaction
            from ..utils_product_mapping import resolve_product # Lazy import to avoid circular dependency

            with transaction.atomic():
                # 1. Update/Create Invoice
                invoice, _ = Invoice.objects.update_or_create(
                    company=company,
                    invoice_number=order_id,
                    defaults={
                        'created_by': user,
                        'platform_name': platform_name,
                        'status': 'DRAFT', # Always Draft first so user can map products
                        'invoice_date': inv_date,
                        'tax_include': True,
                        'tax_percent': tax_rate,
                        'subtotal': subtotal,
                        'grand_total': grand_total,
                        'discount_amount': discount,
                        'shipping_cost': shipping,
                        'tax_amount': round(tax_amt, 2),
                        # Platform Meta
                        'platform_order_id': order_id,
                        'platform_order_status': str(row.get('order_status', ''))[:100],
                        'platform_tracking_number': str(row.get('tracking_no', ''))[:100],
                        'recipient_name': str(row.get('recipient', ''))[:200],
                        'recipient_phone': str(row.get('phone', ''))[:20],
                        'recipient_address': str(row.get('address', '')),
                        'warehouse_name': str(row.get('warehouse', ''))[:100],
                    }
                )

                # 2. Handle Items
                InvoiceItem.objects.filter(invoice=invoice).delete()
                new_items = []

                if order_id in items_grouped.groups:
                    related_items = items_grouped.get_group(order_id)
                    for _, item_row in related_items.iterrows():
                        qty = int(clean_decimal(item_row.get('quantity', 1)))
                        u_price = clean_decimal(item_row.get('unit_price', 0))
                        
                        # Product Mapping Logic
                        internal_product, external_key = resolve_product(platform_name, item_row)

                        new_items.append(InvoiceItem(
                            invoice=invoice,
                            product=internal_product,
                            purchase_item=None,
                            sku=external_key[:100], # Store the external key for mapping UI
                            item_name=str(item_row.get('item_name', ''))[:255],
                            quantity=qty,
                            unit_price=u_price,
                            total_price=qty * u_price
                        ))

                if new_items:
                    InvoiceItem.objects.bulk_create(new_items)
                
                success_count += 1

        except Exception as e:
            # CHANGED: Capture Structured Error Data
            error_info = {
                'row_index': index + 2, # +2 to match Excel Row (Header is 1)
                'order_id': str(row.get('order_id', 'Unknown')), 
                'reason': str(e)
            }
            errors.append(error_info)

    return {
        "status": "completed",
        "imported": success_count,
        "failed": len(errors),
        "error_log": errors
    }