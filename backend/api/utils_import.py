import pandas as pd
from django.db import transaction
from decimal import Decimal, InvalidOperation
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Invoice, Company, InvoiceItem
import os

def process_tiktok_orders(file_path):
    """
    Returns:
        bill_header (DataFrame): Unique orders (Invoices)
        bill_items (DataFrame): Individual line items (Invoice Items)
    """
    
    # 1. Load Data
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == '.csv':
        df = pd.read_csv(file_path, encoding='utf-8-sig', dtype={'Phone #': str, 'Zipcode': str})
    elif ext in ['.xls', '.xlsx']:
        df = pd.read_excel(file_path, dtype={'Phone #': str, 'Zipcode': str})
    else:
        raise ValueError("Unsupported file format.")

    # 2. Data Cleaning
    text_cols = ['Detail Address', 'Additional address information', 'District', 'Province', 'Country']
    df[text_cols] = df[text_cols].fillna('')

    # 3. Create Address
    df['Address'] = (
        df['Detail Address'] + " " + df['Additional address information'] + " " + 
        df['District'] + " " + df['Province'] + " " + df['Country'] + " " + df['Zipcode']
    ).str.strip()

    # 4. --- HEADER DATAFRAME ---
    bill_header = df.groupby('Order ID').agg({
        'Order Status': 'first',
        'SKU Subtotal Before Discount': 'sum',
        'Order Amount': 'first', 
        'Recipient': 'first',
        'Phone #': 'first',
        'Address': 'first',
        'Warehouse Name': 'first',
        'Tracking ID': 'first',
        'Shipped Time': 'first'
    }).reset_index()

    # Rename Header Columns
    bill_header = bill_header.rename(columns={
        'SKU Subtotal Before Discount': 'Subtotal Before Discount',
        'Order Amount': 'Total Order Amount',
        'Phone #': 'Phone',
        'Shipped Time': 'Shipped Date'
    })

    # Header Calculation: Total Discount
    bill_header['Total Discount'] = (
        bill_header['Subtotal Before Discount'] - bill_header['Total Order Amount']
    )

    # Header Type Conversion: Date
    bill_header['Shipped Date'] = pd.to_datetime(
        bill_header['Shipped Date'], dayfirst=True, errors='coerce'
    )

    # 5. --- ITEMS DATAFRAME ---
    # Select specific columns (Note the double brackets [[ ... ]])
    target_cols = [
        'Order ID', 
        'Seller SKU', 
        'Product Name', 
        'Quantity', 
        'SKU Unit Original Price', 
        'SKU Subtotal Before Discount'
    ]
    
    # Check if columns exist to avoid KeyErrors
    available_cols = [c for c in target_cols if c in df.columns]
    bill_items = df[available_cols].copy()

    # Rename Item Columns for Django friendly names
    bill_items = bill_items.rename(columns={
        'Order ID': 'order_id',
        'Seller SKU': 'sku',
        'Product Name': 'item_name',
        'Quantity': 'quantity',
        'SKU Unit Original Price': 'unit_price',
        'SKU Subtotal Before Discount': 'total_price'
    })

    return bill_header, bill_items


def clean_decimal(val):
    """Helper to safely convert currency strings to Decimal"""
    try:
        return Decimal(str(val).replace(',', ''))
    except (ValueError, InvalidOperation):
        return Decimal('0.00')

def import_tiktok_invoices(header_df, items_df, company_id, user_id):
    """
    Args:
        header_df: DataFrame from process_tiktok_orders (Bill Header)
        items_df: DataFrame from process_tiktok_orders (Bill Items)
    """
    print("--- Starting Full Import (Headers & Items) ---")

    try:
        company = Company.objects.get(id=company_id)
        user = User.objects.get(id=user_id)
    except Exception as e:
        return {"status": "error", "message": str(e)}

    success_count = 0
    errors = []

    # Optimize Items DF: Indexing by order_id makes filtering inside the loop 100x faster
    if 'order_id' in items_df.columns:
        items_df['order_id'] = items_df['order_id'].astype(str) # Ensure string for matching
        items_grouped = items_df.groupby('order_id')
    else:
        # Fallback if column renaming failed in previous step
        return {"status": "error", "message": "Items DataFrame missing 'order_id' column"}

    # Handle NaN in headers
    header_df = header_df.fillna('')
    records = header_df.to_dict('records')

    for row in records:
        try:
            # 1. Setup Data
            order_id = str(row.get('Order ID', '')).strip()
            if not order_id or order_id.lower() == 'nan': continue

            # Financials
            subtotal_items = clean_decimal(row.get('Subtotal Before Discount', 0))
            grand_total_final = clean_decimal(row.get('Total Order Amount', 0))
            
            # 2. Logic: Discount vs Shipping
            difference = subtotal_items - grand_total_final
            if difference >= 0:
                calc_discount = difference
                calc_shipping = Decimal('0.00')
            else:
                calc_discount = Decimal('0.00')
                calc_shipping = abs(difference)

            # 3. Logic: Tax (Backwards)
            tax_rate = Decimal('7.00')
            divisor = Decimal('1') + (tax_rate / Decimal('100'))
            base_amount_ex_tax = grand_total_final / divisor
            calc_tax = grand_total_final - base_amount_ex_tax

            # 4. Date
            invoice_dt = row.get('Shipped Date')
            if pd.isna(invoice_dt) or invoice_dt == '':
                invoice_dt = timezone.now()

            # --- ATOMIC TRANSACTION START ---
            with transaction.atomic():
                # A. Upsert Invoice (Header)
                invoice, created = Invoice.objects.update_or_create(
                    company=company,
                    invoice_number=order_id,
                    defaults={
                        'created_by': user,
                        'customer': None,
                        'platform_name': 'TikTok Shop',
                        'status': 'DRAFT',
                        'invoice_date': invoice_dt,
                        'tax_include': True,
                        'tax_percent': tax_rate,
                        'subtotal': subtotal_items,
                        'grand_total': grand_total_final,
                        'discount_amount': calc_discount,
                        'shipping_cost': calc_shipping,
                        'tax_amount': round(calc_tax, 2),
                        # Platform fields
                        'platform_order_id': order_id,
                        'platform_order_status': str(row.get('Order Status', ''))[:100],
                        'platform_tracking_number': str(row.get('Tracking ID', ''))[:100],
                        'warehouse_name': str(row.get('Warehouse Name', ''))[:100],
                        'recipient_name': str(row.get('Recipient', ''))[:200],
                        'recipient_phone': str(row.get('Phone', ''))[:20],
                        'recipient_address': str(row.get('Address', '')),
                    }
                )

                # B. Handle Items (Child Records)
                # 1. Clear existing items for this invoice
                # Assuming your InvoiceItem model has a ForeignKey to Invoice named 'invoice'
                InvoiceItem.objects.filter(invoice=invoice).delete()

                # 2. Prepare new items
                new_items = []
                
                # Fetch related items from the grouped DataFrame
                if order_id in items_grouped.groups:
                    related_items = items_grouped.get_group(order_id)
                    
                    for _, item_row in related_items.iterrows():
                        # Extract raw values
                        qty = int(clean_decimal(item_row.get('quantity', 1)))
                        u_price = clean_decimal(item_row.get('unit_price', 0))
                        
                        # CRITICAL FIX: Calculate total_price here because bulk_create won't call save()
                        calc_total_price = qty * u_price
                        
                        new_items.append(InvoiceItem(
                            invoice=invoice,
                            # We don't link purchase_item during import (it's unknown/null)
                            purchase_item=None, 
                            sku=str(item_row.get('sku', ''))[:100],
                            item_name=str(item_row.get('item_name', 'Unknown Item')), # Mapped to description
                            quantity=qty,
                            unit_price=u_price,
                            total_price=calc_total_price # <--- Manually set this
                        ))
                    
                    if new_items:
                        InvoiceItem.objects.bulk_create(new_items)
                        # Note: We do NOT need to call invoice.calculate_totals() here 
                        # because we already set the Invoice totals (Subtotal/Grand Total) 
                        # from the Header CSV in the previous step (Part A).
                success_count += 1
            # --- ATOMIC TRANSACTION END ---

        except Exception as e:
            errors.append(f"Order {row.get('Order ID')}: {str(e)}")

    return {
        "status": "completed",
        "imported": success_count,
        "failed": len(errors),
        "error_log": errors
    }