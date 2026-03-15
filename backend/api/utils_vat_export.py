"""
VAT Export Module - Generates Excel reports from VAT data.
Uses pandas + openpyxl to query DB and write .xlsx files.
"""
import os
import tempfile
from datetime import date

import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment

from api.models import VatOrderBuyItem, VatOrderSaleItem


def export_vat_report(start_date=None, end_date=None, vat_company=None, query=None):
    """
    Query VAT buy items from DB, match with sale items by serial_no,
    and export to an Excel file. Returns the file path.
    """

    # --- 1. Query buy items ---
    qs = VatOrderBuyItem.objects.all().select_related('vat_order')

    if start_date:
        qs = qs.filter(vat_order__date__gte=start_date)
    if end_date:
        qs = qs.filter(vat_order__date__lte=end_date)
    if vat_company and vat_company.lower() != 'all':
        qs = qs.filter(vat_order__supplier_name__icontains=vat_company)
    if query:
        qs = qs.filter(product_name__icontains=query)

    # --- 2. Build rows ---
    rows = []
    for item in qs:
        row = {
            'Serial No': item.serial_no or '',
            'สินค้า': item.product_name or '',
            'วันที่ซื้อ': str(item.vat_order.date) if item.vat_order else '',
            'เลขที่เอกสารซื้อ': item.vat_order.document_no if item.vat_order else '',
            'ราคาซื้อ': float(item.purchase_price) if item.purchase_price else 0,
            'บริษัท VAT': item.vat_order.supplier_name if item.vat_order else '',
            'วิธีชำระ (เข้า)': item.payment_method_in or '',
            'ธนาคาร (เข้า)': item.bank_in or '',
            'วันที่ขาย': '',
            'เลขที่เอกสารขาย': '',
            'ชื่อลูกค้า': '',
            'ราคาขาย': '',
            'วิธีชำระ (ออก)': '',
        }

        # Match sale item by serial_no
        sale = VatOrderSaleItem.objects.filter(serial_no=item.serial_no).select_related('vat_order').first()
        if sale:
            row['วันที่ขาย'] = str(sale.vat_order.date) if sale.vat_order else ''
            row['เลขที่เอกสารขาย'] = sale.vat_order.document_no if sale.vat_order else ''
            row['ชื่อลูกค้า'] = sale.vat_order.customer_name if sale.vat_order else ''
            row['ราคาขาย'] = float(sale.sale_price) if sale.sale_price else 0
            row['วิธีชำระ (ออก)'] = sale.payment_method_out or ''

        rows.append(row)

    # --- 3. Create DataFrame ---
    df = pd.DataFrame(rows)

    if df.empty:
        # Add empty row with headers
        df = pd.DataFrame(columns=[
            'Serial No', 'สินค้า', 'วันที่ซื้อ', 'เลขที่เอกสารซื้อ',
            'ราคาซื้อ', 'บริษัท VAT', 'วิธีชำระ (เข้า)', 'ธนาคาร (เข้า)',
            'วันที่ขาย', 'เลขที่เอกสารขาย', 'ชื่อลูกค้า', 'ราคาขาย', 'วิธีชำระ (ออก)'
        ])

    # --- 4. Write to temp Excel file ---
    filename = f'VAT_Report_{date.today().isoformat()}.xlsx'
    filepath = os.path.join(tempfile.gettempdir(), filename)

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='VAT_Report')
        
        # Style the header row
        ws = writer.sheets['VAT_Report']
        header_font = Font(bold=True, color='FFFFFF', size=11)
        header_fill = PatternFill(start_color='3b5998', end_color='3b5998', fill_type='solid')
        header_align = Alignment(horizontal='center')

        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align

        # Auto-fit columns
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                except:
                    pass
            ws.column_dimensions[col_letter].width = min(max_len + 4, 40)

    return filepath, filename


def export_vat_buy_summary_report(qs):
    """
    Export document-level VAT buy summaries to an Excel file.
    Takes a queryset of VatOrderBuy that has been annotated with total_buy_amount and item_count.
    """
    rows = []
    for order in qs:
        supplier = order.supplier_name or ''
        
        rows.append({
            'วันที่': str(order.date) if order.date else '',
            'เลขที่เอกสาร': order.document_no or '',
            'ร้านค้า (Supplier)': supplier,
            'บริษัท VAT': 'Kit' if supplier.lower().rstrip().endswith('/kit') else ('S16' if supplier.lower().rstrip().endswith('/s16') else '-'),
            'จำนวนรายการ': int(order.item_count) if hasattr(order, 'item_count') and order.item_count else 0,
            'รวมยอด VAT': float(order.total_buy_amount) if hasattr(order, 'total_buy_amount') and order.total_buy_amount else 0,
        })
        
    df = pd.DataFrame(rows)
    
    if df.empty:
        df = pd.DataFrame(columns=['วันที่', 'เลขที่เอกสาร', 'ร้านค้า (Supplier)', 'บริษัท VAT', 'จำนวนรายการ', 'รวมยอด VAT'])

    # Write to temp Excel file
    filename = f'VAT_Buy_Summary_{date.today().isoformat()}.xlsx'
    filepath = os.path.join(tempfile.gettempdir(), filename)

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Summary')
        
        # Style the header row
        ws = writer.sheets['Summary']
        header_font = Font(bold=True, color='FFFFFF', size=11)
        header_fill = PatternFill(start_color='198754', end_color='198754', fill_type='solid') # Green header
        header_align = Alignment(horizontal='center')

        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align

        # Auto-fit columns
        for col in ws.columns:
            max_len = 0
            col_letter = col[0].column_letter
            for cell in col:
                try:
                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                except:
                    pass
            ws.column_dimensions[col_letter].width = min(max_len + 4, 40)

    return filepath, filename
