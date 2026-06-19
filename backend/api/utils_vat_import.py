import pandas as pd
import numpy as np
from datetime import datetime
from django.db import transaction
from .models import VatOrderBuy, VatOrderBuyItem, VatOrderSale, VatOrderSaleItem
import math

def parse_thai_date(date_str):
    """
    Parses DD/MM/YYYY where YYYY could be Buddhist era.
    e.g. 12/03/2569 -> 2026-03-12
    """
    if pd.isna(date_str) or not date_str:
        return None
    try:
        parts = str(date_str).strip().split('/')
        if len(parts) == 3:
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            # If Buddhist Era (typically > 2400)
            if year > 2400:
                year -= 543
            return datetime(year, month, day).date()
    except Exception as e:
        print(f"Error parsing date {date_str}: {e}")
    return None

def clean_dataframe(df):
    """Clean NaN values from DataFrame for safe database insert"""
    # Replace NaN, NaT, inf, -inf with None
    df = df.replace({np.nan: None, float('inf'): None, float('-inf'): None})
    return df

@transaction.atomic
def process_vat_buy_import(file_obj):
    """
    Process POS Buy-in Excel list using stateful parsing for multi-line headers.
    """
    try:
        # 1. Read Raw DataFrame without headers to expose all rows
        df_raw = pd.read_excel(file_obj, header=None)
        df_raw = clean_dataframe(df_raw)
        
        # 2. Extract Date (try row 4, column B)
        order_date = datetime.now().date()
        for r in range(0, min(10, len(df_raw))):
            val = df_raw.iloc[r, 1]
            if pd.notna(val) and isinstance(val, str) and '/' in val:
                parsed = parse_thai_date(val)
                if parsed:
                    order_date = parsed
                    break

        # 3. Find Header Row dynamically (starts with "Serial No")
        header_row_idx = -1
        for i in range(len(df_raw)):
            val = df_raw.iloc[i, 0]
            if pd.notna(val) and str(val).strip() == 'Serial No':
                header_row_idx = i
                break
                
        if header_row_idx == -1:
            return {'success': 0, 'errors': ["Could not find 'Serial No' header row."], 'total': 0}

        results = {'success': 0, 'errors': [], 'total': 0}
        
        # Columns based on image: A(0)=Serial No, C(2)=Product, E(4)=Unit, F(5)=Doc, I(8)=Supplier, K(10)=Price
        COL_SERIAL = 0
        COL_DESC = 2
        COL_UNIT = 4
        COL_DOC = 5
        COL_SUPPLIER = 8
        COL_PRICE = 10

        parsed_items = []
        current_item = None

        # 4. Stateful parsing
        for index in range(header_row_idx + 1, len(df_raw)):
            row = df_raw.iloc[index]
            serial = row[COL_SERIAL]
            
            is_serial_valid = pd.notna(serial) and str(serial).strip() and str(serial).strip() != 'nan'
            
            # Stop parsing on summary rows
            if is_serial_valid and 'รวม' in str(serial):
                break
                
            # Ignore print footers
            if is_serial_valid and str(serial).strip().startswith('Print On'):
                continue
            if is_serial_valid and str(serial).strip().startswith('วันที่'):
                continue
            if is_serial_valid and str(serial).strip().startswith('Serial No'):
                continue

            if is_serial_valid:
                # Flush the previous item
                if current_item:
                    parsed_items.append(current_item)
                
                # Start new item
                try:
                    price = float(row.get(COL_PRICE, 0))
                    if math.isnan(price): price = 0
                except:
                    price = 0
                    
                current_item = {
                    'serial_no': str(serial).strip(),
                    'product_name': str(row[COL_DESC]).strip() if pd.notna(row[COL_DESC]) else '',
                    'unit': str(row[COL_UNIT]).strip() if pd.notna(row[COL_UNIT]) else '',
                    'document_no': str(row[COL_DOC]).strip() if pd.notna(row[COL_DOC]) else '',
                    'supplier_name': str(row[COL_SUPPLIER]).strip() if pd.notna(row[COL_SUPPLIER]) else '',
                    'purchase_price': price
                }
            else:
                # Continuation row for the current item
                if current_item:
                    desc_part = str(row[COL_DESC]).strip() if pd.notna(row[COL_DESC]) else ''
                    supp_part = str(row[COL_SUPPLIER]).strip() if pd.notna(row[COL_SUPPLIER]) else ''
                    
                    if desc_part and desc_part != 'nan':
                        current_item['product_name'] += ' ' + desc_part
                    if supp_part and supp_part != 'nan':
                        current_item['supplier_name'] += ' ' + supp_part

        # Flush the final item
        if current_item:
            parsed_items.append(current_item)

        # 5. Database Insertion
        for item in parsed_items:
            results['total'] += 1
            if not item['document_no']:
                results['errors'].append(f"Missing 'เลขที่เอกสาร' for Serial {item['serial_no']}")
                continue
                
            try:
                # Header
                order, created = VatOrderBuy.objects.get_or_create(
                    document_no=item['document_no'],
                    defaults={
                        'date': order_date,
                        'supplier_name': item['supplier_name'].strip()
                    }
                )
                if not created:
                    order.date = order_date
                    order.supplier_name = item['supplier_name'].strip()
                    order.save()

                # Item
                VatOrderBuyItem.objects.update_or_create(
                    serial_no=item['serial_no'],
                    defaults={
                        'vat_order': order,
                        'product_name': item['product_name'].strip(),
                        'unit': item['unit'],
                        'purchase_price': item['purchase_price']
                    }
                )
                results['success'] += 1
            except Exception as e:
                results['errors'].append(f"Serial {item['serial_no']}: {str(e)}")

        return results
    except Exception as e:
        return {'success': 0, 'errors': [f"Failed to process file: {str(e)}"], 'total': 0}


@transaction.atomic
def process_vat_sale_import(file_obj):
    """
    Process POS Sale Excel list using stateful parsing for multi-line headers.
    """
    try:
        df_raw = pd.read_excel(file_obj, header=None)
        df_raw = clean_dataframe(df_raw)
        
        # 1. Extract Date
        order_date = datetime.now().date()
        for r in range(0, min(10, len(df_raw))):
            val = df_raw.iloc[r, 1]
            if pd.notna(val) and isinstance(val, str) and '/' in val:
                parsed = parse_thai_date(val)
                if parsed:
                    order_date = parsed
                    break
        
        # 2. Find Header Row dynamically
        header_row_idx = -1
        for i in range(len(df_raw)):
            val = df_raw.iloc[i, 0]
            if pd.notna(val) and str(val).strip() == 'Serial No':
                header_row_idx = i
                break
                
        if header_row_idx == -1:
            return {'success': 0, 'errors': ["Could not find 'Serial No' header row."], 'total': 0}

        results = {'success': 0, 'errors': [], 'total': 0}

        COL_SERIAL = 0      # A
        COL_DESC = 2        # C
        COL_UNIT = 6        # G
        COL_DOC = 7         # H
        COL_CUSTOMER = 11   # L
        COL_PRICE = 13      # N

        parsed_items = []
        current_item = None
        
        for index in range(header_row_idx + 1, len(df_raw)):
            row = df_raw.iloc[index]
            serial = row[COL_SERIAL]
            
            is_serial_valid = pd.notna(serial) and str(serial).strip() and str(serial).strip() != 'nan'
            
            if is_serial_valid and 'รวม' in str(serial):
                break
                
            # Ignore print footers
            if is_serial_valid and str(serial).strip().startswith('Print On'):
                continue
            if is_serial_valid and str(serial).strip().startswith('วันที่'):
                continue
            if is_serial_valid and str(serial).strip().startswith('Serial No'):
                continue

            if is_serial_valid:
                if current_item:
                    parsed_items.append(current_item)
                
                try:
                    price = float(row.get(COL_PRICE, 0))
                    if math.isnan(price): price = 0
                except:
                    price = 0
                    
                current_item = {
                    'serial_no': str(serial).strip(),
                    'product_name': str(row[COL_DESC]).strip() if pd.notna(row[COL_DESC]) else '',
                    'unit': str(row[COL_UNIT]).strip() if pd.notna(row[COL_UNIT]) else '',
                    'document_no': str(row[COL_DOC]).strip() if pd.notna(row[COL_DOC]) else '',
                    'customer_name': str(row[COL_CUSTOMER]).strip() if pd.notna(row[COL_CUSTOMER]) else '',
                    'sale_price': price
                }
            else:
                if current_item:
                    desc_part = str(row[COL_DESC]).strip() if pd.notna(row[COL_DESC]) else ''
                    cust_part = str(row[COL_CUSTOMER]).strip() if pd.notna(row[COL_CUSTOMER]) else ''
                    
                    if desc_part and desc_part != 'nan':
                        current_item['product_name'] += ' ' + desc_part
                    if cust_part and cust_part != 'nan':
                        current_item['customer_name'] += ' ' + cust_part

        if current_item:
            parsed_items.append(current_item)

        for item in parsed_items:
            results['total'] += 1
            if not item['document_no']:
                results['errors'].append(f"Missing 'เลขที่เอกสาร' for Serial {item['serial_no']}")
                continue

            try:
                # Header
                order, created = VatOrderSale.objects.get_or_create(
                    document_no=item['document_no'],
                    defaults={
                        'date': order_date,
                        'customer_name': item['customer_name'].strip()
                    }
                )

                if not created:
                    order.date = order_date
                    order.customer_name = item['customer_name'].strip()
                    order.save()

                # Item
                VatOrderSaleItem.objects.update_or_create(
                    vat_order=order,
                    serial_no=item['serial_no'],
                    defaults={
                        'product_name': item['product_name'].strip(),
                        'unit': item['unit'],
                        'sale_price': item['sale_price']
                    }
                )
                results['success'] += 1
            except Exception as e:
                results['errors'].append(f"Serial {item['serial_no']}: {str(e)}")

        return results

    except Exception as e:
        return {'success': 0, 'errors': [f"Failed to process file: {str(e)}"], 'total': 0}
