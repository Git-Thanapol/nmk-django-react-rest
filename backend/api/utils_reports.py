import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from django.http import HttpResponse
from datetime import datetime, date
from django.db.models import Sum, Q, F
from django.db.models.functions import Coalesce
from decimal import Decimal
from .models import Product, PurchaseItem, InvoiceItem, PurchaseOrder, Invoice 

def get_thai_datetime():
    """Returns current datetime in Thai format: 29/03/2569 18:46:00"""
    now = datetime.now()
    year = now.year + 543
    return f"{now.day:02d}/{now.month:02d}/{year} {now.strftime('%H:%M:%S')}"

def get_thai_month_year(date_obj):
    """Returns Month Year in Thai: ตุลาคม ปี พ.ศ. 2568"""
    if not date_obj: return ""
    thai_months = [
        "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    return f"{thai_months[date_obj.month]} ปี พ.ศ. {date_obj.year + 543}"

def generate_purchase_tax_report(queryset, company, start_date, end_date, report_basis='create_date'):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Purchase Tax Report"

    font_header = Font(name='Sarabun', size=14, bold=True)
    font_sub = Font(name='Sarabun', size=11)
    font_bold = Font(name='Sarabun', size=11, bold=True)
    border_thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    align_center = Alignment(horizontal='center', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')

    ws.merge_cells('A1:B1'); ws['A1'] = get_thai_datetime()
    ws.merge_cells('D1:F1'); ws['D1'] = str(company); ws['D1'].font = font_header; ws['D1'].alignment = align_center
    ws.merge_cells('D2:F2'); ws['D2'] = "รายงานภาษีซื้อ"; ws['D2'].font = font_bold; ws['D2'].alignment = align_center
    
    basis_text = "(ยื่นตามวันที่เอกสาร)" if report_basis == 'create_date' else "(ยื่นตามวันที่จ่ายภาษี)"
    ws['D2'].value = f"รายงานภาษีซื้อ {basis_text}"

    ws.merge_cells('D3:F3')
    ws['D3'] = f"เดือนภาษี {get_thai_month_year(start_date)}" 
    ws['D3'].alignment = align_center

    tax_id = getattr(company, 'tax_id', '-')
    ws['H3'] = f"เลขประจำตัวผู้เสียภาษี {tax_id}"
    ws['H3'].alignment = align_right

    headers = [
        ('A5:A6', 'ลำดับ', 5), ('B5:C5', 'ใบกำกับภาษี', 0), ('B6:B6', 'วัน/เดือน/ปี', 12), ('C6:C6', 'เลขที่', 15),
        ('D5:D6', 'ชื่อผู้ขายสินค้า/ผู้รับบริการ', 30), ('E5:E6', 'เลขประจำตัวผู้เสียภาษี\nของผู้ขายสินค้า', 20),
        ('F5:G5', 'สถานประกอบการ', 0), ('F6:F6', 'สนญ.', 8), ('G6:G6', 'สาขาที่', 8),
        ('H5:H6', 'มูลค่าสินค้าหรือบริการ', 15), ('I5:I6', 'จำนวนเงินภาษีมูลค่าเพิ่ม', 15),
    ]
    for cell_range, text, width in headers:
        ws.merge_cells(cell_range)
        cell = ws[cell_range.split(':')[0]]
        cell.value = text
        cell.font = font_bold
        cell.alignment = align_center
        cell.border = border_thin
        for row in ws[cell_range]:
            for c in row: c.border = border_thin
        if width > 0: ws.column_dimensions[cell_range[0]].width = width

    ws.print_title_rows = '1:6'

    current_row = 7
    seq = 1
    total_value = 0
    total_vat = 0

    for po in queryset:
        po_date = po.order_date 
        thai_date = f"{po_date.day:02d}/{po_date.month:02d}/{po_date.year+543}"
        vendor_name = po.vendor.name if po.vendor else "Unknown"
        vendor_tax = getattr(po.vendor, 'tax_id', '') 
        val = po.subtotal
        vat = po.tax_amount
        total_value += val
        total_vat += vat

        data = [
            (seq, 'center'), (thai_date, 'center'), (po.po_number, 'left'), 
            (vendor_name, 'left'), (vendor_tax, 'center'), ('X', 'center'), ('', 'center'),
            (val, 'number'), (vat, 'number'),
        ]
        
        col_indices = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
        for i, (value, style_type) in enumerate(data):
            cell = ws[f"{col_indices[i]}{current_row}"]
            cell.value = value
            cell.font = font_sub
            cell.border = border_thin
            if style_type == 'number':
                cell.number_format = '#,##0.00'
                cell.alignment = align_right
            elif style_type == 'center':
                cell.alignment = align_center
            else:
                cell.alignment = Alignment(horizontal='left', vertical='center')
        current_row += 1
        seq += 1

    ws.merge_cells(f'A{current_row}:G{current_row}')
    ws[f'A{current_row}'] = "รวมทั้งสิ้น"
    ws[f'A{current_row}'].alignment = align_right
    ws[f'A{current_row}'].font = font_bold
    ws[f'A{current_row}'].border = border_thin
    for col in ['B','C','D','E','F','G']: ws[f'{col}{current_row}'].border = border_thin

    for col, val in [('H', total_value), ('I', total_vat)]:
        c = ws[f'{col}{current_row}']
        c.value = val
        c.font = font_bold
        c.number_format = '#,##0.00'
        c.alignment = align_right
        c.border = border_thin

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Purchase_Tax_{report_basis}_{start_date}.xlsx"'
    wb.save(response)
    return response

def generate_sales_tax_report(queryset, company, start_date, end_date, report_basis='create_date'):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales Tax Report"

    font_header = Font(name='Sarabun', size=14, bold=True)
    font_sub = Font(name='Sarabun', size=11)
    font_bold = Font(name='Sarabun', size=11, bold=True)
    border_thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    align_center = Alignment(horizontal='center', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')

    ws.merge_cells('A1:B1'); ws['A1'] = get_thai_datetime()
    ws.merge_cells('D1:F1'); ws['D1'] = str(company); ws['D1'].font = font_header; ws['D1'].alignment = align_center
    ws.merge_cells('D2:F2')
    basis_text = "(ยื่นตามวันที่เอกสาร)" if report_basis == 'create_date' else "(ยื่นตามวันที่จ่ายภาษี)"
    ws['D2'].value = f"รายงานภาษีขาย {basis_text}"
    ws['D2'].font = font_bold; ws['D2'].alignment = align_center

    ws.merge_cells('D3:F3')
    ws['D3'] = f"เดือนภาษี {get_thai_month_year(start_date)}" 
    ws['D3'].alignment = align_center

    tax_id = getattr(company, 'tax_id', '-')
    ws['H3'] = f"เลขประจำตัวผู้เสียภาษี {tax_id}"
    ws['H3'].alignment = align_right

    headers = [
        ('A5:A6', 'ลำดับ', 5), ('B5:C5', 'ใบกำกับภาษี', 0), ('B6:B6', 'วัน/เดือน/ปี', 12), ('C6:C6', 'เลขที่', 15),
        ('D5:D6', 'ชื่อผู้ซื้อสินค้า/ผู้รับบริการ', 30), ('E5:E6', 'เลขประจำตัวผู้เสียภาษี\nของผู้ซื้อสินค้า', 20),
        ('F5:G5', 'สถานประกอบการ', 0), ('F6:F6', 'สนญ.', 8), ('G6:G6', 'สาขาที่', 8),
        ('H5:H6', 'มูลค่าสินค้าหรือบริการ', 15), ('I5:I6', 'จำนวนเงินภาษีมูลค่าเพิ่ม', 15),
    ]
    for cell_range, text, width in headers:
        ws.merge_cells(cell_range)
        cell = ws[cell_range.split(':')[0]]
        cell.value = text
        cell.font = font_bold
        cell.alignment = align_center
        cell.border = border_thin
        for row in ws[cell_range]:
            for c in row: c.border = border_thin
        if width > 0: ws.column_dimensions[cell_range[0]].width = width

    ws.print_title_rows = '1:6'

    current_row = 7
    seq = 1
    total_value = 0
    total_vat = 0

    for inv in queryset:
        inv_date = inv.invoice_date
        thai_date = f"{inv_date.day:02d}/{inv_date.month:02d}/{inv_date.year+543}"
        cust_name = inv.recipient_name if inv.recipient_name else (inv.vendor.name if inv.vendor else "เงินสด/ไม่ระบุ")
        cust_tax = inv.vendor.tax_id if (inv.vendor and hasattr(inv.vendor, 'tax_id')) else ""
        val = inv.subtotal
        vat = inv.tax_amount
        total_value += val
        total_vat += vat

        data = [
            (seq, 'center'), (thai_date, 'center'), (inv.invoice_number, 'left'),
            (cust_name, 'left'), (cust_tax, 'center'), ('X', 'center'), ('', 'center'),
            (val, 'number'), (vat, 'number'),
        ]

        col_indices = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
        for i, (value, style_type) in enumerate(data):
            cell = ws[f"{col_indices[i]}{current_row}"]
            cell.value = value
            cell.font = font_sub
            cell.border = border_thin
            if style_type == 'number':
                cell.number_format = '#,##0.00'
                cell.alignment = align_right
            elif style_type == 'center':
                cell.alignment = align_center
            else:
                cell.alignment = Alignment(horizontal='left', vertical='center')
        current_row += 1
        seq += 1

    ws.merge_cells(f'A{current_row}:G{current_row}')
    ws[f'A{current_row}'] = "รวมทั้งสิ้น"
    ws[f'A{current_row}'].alignment = align_right
    ws[f'A{current_row}'].font = font_bold
    ws[f'A{current_row}'].border = border_thin
    for col in ['B','C','D','E','F','G']: ws[f'{col}{current_row}'].border = border_thin

    for col, val in [('H', total_value), ('I', total_vat)]:
        c = ws[f'{col}{current_row}']
        c.value = val
        c.font = font_bold
        c.number_format = '#,##0.00'
        c.alignment = align_right
        c.border = border_thin

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Sales_Tax_{report_basis}_{start_date}.xlsx"'
    wb.save(response)
    return response

def generate_stock_report(company, start_date, end_date):
    """
    Generates Stock Report with specific formatting: thick vertical separators and header borders.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Stock Report"

    # --- Styles ---
    font_header = Font(name='Sarabun', size=14, bold=True)
    font_bold = Font(name='Sarabun', size=11, bold=True)
    font_sub = Font(name='Sarabun', size=10)
    
    # Border Definitions
    thin = Side(style='thin')
    medium = Side(style='medium')
    
    # Helper for row borders
    def apply_row_borders(ws, row_idx, is_summary=False):
        for col in range(1, 13):
            cell = ws.cell(row=row_idx, column=col)
            b_left = medium if col in [4, 7, 10] else thin
            b_right = medium if col in [3, 6, 9, 12] else thin
            b_top = thin
            b_bottom = medium if is_summary else thin
            cell.border = Border(left=b_left, right=b_right, top=b_top, bottom=b_bottom)

    align_center = Alignment(horizontal='center', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')
    
    col_widths = [12, 6, 20, 10, 15, 15, 10, 15, 15, 10, 15, 15]
    for i, width in enumerate(col_widths):
        col_letter = openpyxl.utils.get_column_letter(i+1)
        ws.column_dimensions[col_letter].width = width

    # Header
    now = datetime.now()
    ws.cell(row=1, column=1, value=f"{now.day:02d}/{now.month:02d}/{now.year+543}").alignment = align_left
    ws.merge_cells('E1:H1'); ws['E1'] = str(company) if company else "ทุกบริษัท"; ws['E1'].font = font_header; ws['E1'].alignment = align_center
    ws['L1'] = "Page 1"; ws['L1'].alignment = align_right
    ws.cell(row=2, column=1, value=f"{now.strftime('%H:%M:%S')}").alignment = align_left
    ws.merge_cells('E2:H2'); ws['E2'] = "รายงานบัญชี"; ws['E2'].font = font_bold; ws['E2'].alignment = align_center
    tax_id = getattr(company, 'tax_id', '-') if company else "-"
    ws.merge_cells('A3:C3'); ws['A3'] = f"เลขประจำตัวผู้เสียภาษี: {tax_id}"; ws['A3'].font = font_sub
    ws.merge_cells('E3:H3'); ws['E3'] = f"ตั้งแต่วันที่ {start_date.day}/{start_date.month}/{start_date.year+543} จนถึง {end_date.day}/{end_date.month}/{end_date.year+543}"; ws['E3'].alignment = align_center

    # --- Table Headers (Row 5 & 6) ---
    ws.merge_cells('A5:C5'); ws.merge_cells('D5:F5'); ws['D5'] = "รายการรับ"; ws.merge_cells('G5:I5'); ws['G5'] = "รายการจ่าย"; ws.merge_cells('J5:L5'); ws['J5'] = "คงเหลือ"
    
    for col in range(1, 13):
        cell = ws.cell(row=5, column=col)
        b_left = medium if col in [4, 7, 10] else thin
        b_right = medium if col in [3, 6, 9, 12] else thin
        cell.border = Border(left=b_left, right=b_right, top=medium, bottom=thin)
        if col in [4, 7, 10]: cell.font = font_bold; cell.alignment = align_center

    headers_row6 = ['วันที่', 'T/C', 'เลขที่ใบกำกับ', 'จำนวน', 'ต้นทุนเฉลี่ย', 'รวมเป็นเงิน', 'จำนวน', 'ต้นทุนเฉลี่ย', 'รวมเป็นเงิน', 'จำนวน', 'ต้นทุนเฉลี่ย', 'รวมเป็นเงิน']
    for i, text in enumerate(headers_row6):
        col = i + 1
        cell = ws.cell(row=6, column=col)
        cell.value = text
        cell.font = font_bold
        cell.alignment = align_center
        b_left = medium if col in [4, 7, 10] else thin
        b_right = medium if col in [3, 6, 9, 12] else thin
        cell.border = Border(left=b_left, right=b_right, top=thin, bottom=medium)

    ws.print_title_rows = '1:6'
    current_row = 7

    # 1. Collect all transactions for the company (Mapped and Unmapped)
    pur_filter = Q(purchase_order__status='PAID')
    sal_filter = Q(invoice__status='BILLED')
    if company:
        pur_filter &= Q(purchase_order__company=company)
        sal_filter &= Q(invoice__company=company)

    purchases = PurchaseItem.objects.filter(pur_filter).select_related('purchase_order', 'product').values(
        'product__id', 'product__sku', 'product__name',
        'purchase_order__order_date', 'purchase_order__po_number', 'quantity', 'unit_cost', 'total_price'
    )
    sales = InvoiceItem.objects.filter(sal_filter).select_related('invoice', 'product').values(
        'product__id', 'product__sku', 'product__name', 'sku', 'item_name',
        'invoice__invoice_date', 'invoice__invoice_number', 'quantity'
    )

    data_by_sku = {}
    for p in purchases:
        p_id, sku, name = p['product__id'] or "UNMAPPED", p['product__sku'] or "NO-SKU", p['product__name'] or "Unknown Product"
        key = (p_id, sku)
        if key not in data_by_sku: data_by_sku[key] = {'sku': sku, 'name': name, 'tx': []}
        data_by_sku[key]['tx'].append({'date': p['purchase_order__order_date'] or date.min, 'type': 'PUR', 'ref': p['purchase_order__po_number'], 'qty': Decimal(str(p['quantity'] or 0)), 'cost': Decimal(str(p['unit_cost'] or 0)), 'amount': Decimal(str(p['total_price'] or 0))})

    for s in sales:
        p_id, sku, name = s['product__id'] or "UNMAPPED", s['product__sku'] or s['sku'] or "UNMAPPED", s['product__name'] or s['item_name'] or "Unknown Item"
        key = (p_id, sku)
        if key not in data_by_sku: data_by_sku[key] = {'sku': sku, 'name': name, 'tx': []}
        data_by_sku[key]['tx'].append({'date': s['invoice__invoice_date'] or date.min, 'type': 'SAL', 'ref': s['invoice__invoice_number'], 'qty': Decimal(str(s['quantity'] or 0)), 'cost': Decimal('0'), 'amount': Decimal('0')})

    sorted_keys = sorted(data_by_sku.keys(), key=lambda x: str(x[1]))

    for key in sorted_keys:
        group = data_by_sku[key]
        all_tx = group['tx']
        all_tx.sort(key=lambda x: (x['date'], 0 if x['type'] == 'PUR' else 1))

        running_qty, running_amount, running_avg_cost = Decimal('0'), Decimal('0'), Decimal('0')
        bf_qty, bf_amount, bf_avg_cost = Decimal('0'), Decimal('0'), Decimal('0')
        tx_in_range = []
        
        for tx in all_tx:
            if tx['type'] == 'PUR':
                running_qty += tx['qty']; running_amount += tx['amount']
                if running_qty > 0: running_avg_cost = running_amount / running_qty
            else:
                tx['cost'] = running_avg_cost; tx['amount'] = tx['qty'] * running_avg_cost
                running_qty -= tx['qty']; running_amount -= tx['amount']
            
            tx['rq'], tx['rc'], tx['ra'] = running_qty, running_avg_cost, running_amount
            if tx['date'] < start_date: 
                bf_qty, bf_amount, bf_avg_cost = running_qty, running_amount, running_avg_cost
            elif tx['date'] <= end_date: 
                tx_in_range.append(tx)

        if bf_qty == 0 and not tx_in_range: continue

        # SKU & Name
        ws.merge_cells(f'A{current_row}:C{current_row}'); ws[f'A{current_row}'] = f"รหัสสินค้า : {group['sku']}"; ws[f'A{current_row}'].font = font_bold; current_row += 1
        ws.merge_cells(f'A{current_row}:C{current_row}'); ws[f'A{current_row}'] = f"ชื่อสินค้า : {group['name']}"; ws[f'A{current_row}'].font = font_bold; current_row += 1
        
        # B/F row
        ws.cell(row=current_row, column=1, value=f"{start_date.day}/{start_date.month}/{start_date.year+543}")
        ws.cell(row=current_row, column=2, value="B/F")
        ws.cell(row=current_row, column=10, value=bf_qty).number_format = '#,##0'
        ws.cell(row=current_row, column=11, value=bf_avg_cost).number_format = '#,##0.0000'
        ws.cell(row=current_row, column=12, value=bf_amount).number_format = '#,##0.00'
        for c in range(10, 13): ws.cell(row=current_row, column=c).alignment = align_right
        apply_row_borders(ws, current_row)
        current_row += 1
        
        r_pq, r_pa, r_sq, r_sa = Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0')
        for tx in tx_in_range:
            ws.cell(row=current_row, column=1, value=f"{tx['date'].day}/{tx['date'].month}/{tx['date'].year+543}").alignment = align_left
            ws.cell(row=current_row, column=2, value=tx['type']).alignment = align_center
            ws.cell(row=current_row, column=3, value=tx['ref']).alignment = align_left
            if tx['type'] == 'PUR':
                ws.cell(row=current_row, column=4, value=tx['qty']).number_format = '#,##0'
                ws.cell(row=current_row, column=5, value=tx['cost']).number_format = '#,##0.0000'
                ws.cell(row=current_row, column=6, value=tx['amount']).number_format = '#,##0.00'
                r_pq += tx['qty']; r_pa += tx['amount']
            else:
                ws.cell(row=current_row, column=7, value=tx['qty']).number_format = '#,##0'
                ws.cell(row=current_row, column=8, value=tx['cost']).number_format = '#,##0.0000'
                ws.cell(row=current_row, column=9, value=tx['amount']).number_format = '#,##0.00'
                r_sq += tx['qty']; r_sa += tx['amount']
            ws.cell(row=current_row, column=10, value=tx['rq']).number_format = '#,##0'
            ws.cell(row=current_row, column=11, value=tx['rc']).number_format = '#,##0.0000'
            ws.cell(row=current_row, column=12, value=tx['ra']).number_format = '#,##0.00'
            for c in range(4, 13): ws.cell(row=current_row, column=c).alignment = align_right
            apply_row_borders(ws, current_row)
            current_row += 1

        # Summary Row
        ws.cell(row=current_row, column=4, value=r_pq).number_format = '#,##0'
        if r_pq > 0: ws.cell(row=current_row, column=5, value=r_pa/r_pq).number_format = '#,##0.0000'
        ws.cell(row=current_row, column=6, value=r_pa).number_format = '#,##0.00'
        ws.cell(row=current_row, column=7, value=r_sq).number_format = '#,##0'
        if r_sq > 0: ws.cell(row=current_row, column=8, value=r_sa/r_sq).number_format = '#,##0.0000'
        ws.cell(row=current_row, column=9, value=r_sa).number_format = '#,##0.00'
        f_q, f_v, f_a = (tx_in_range[-1]['rq'], tx_in_range[-1]['rc'], tx_in_range[-1]['ra']) if tx_in_range else (bf_qty, bf_avg_cost, bf_amount)
        ws.cell(row=current_row, column=10, value=f_q).number_format = '#,##0'; ws.cell(row=current_row, column=11, value=f_v).number_format = '#,##0.0000'; ws.cell(row=current_row, column=12, value=f_a).number_format = '#,##0.00'
        for c in range(4, 13): ws.cell(row=current_row, column=c).alignment = align_right; ws.cell(row=current_row, column=c).font = font_bold
        apply_row_borders(ws, current_row, is_summary=True)
        current_row += 2

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Stock_Report_{start_date}.xlsx"'
    wb.save(response)
    return response

def generate_combined_tax_report(po_qs, inv_qs, company_name, start_date, end_date, report_basis='create_date'):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Combined VAT Report"
    font_header = Font(name='Sarabun', size=14, bold=True)
    font_sub = Font(name='Sarabun', size=11)
    font_bold = Font(name='Sarabun', size=11, bold=True)
    border_thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    align_center = Alignment(horizontal='center', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')

    ws.merge_cells('A1:B1'); ws['A1'] = get_thai_datetime()
    ws.merge_cells('E1:G1'); ws['E1'] = str(company_name); ws['E1'].font = font_header; ws['E1'].alignment = align_center
    ws.merge_cells('E2:G2')
    basis_text = "(ยื่นตามวันที่เอกสาร)" if report_basis == 'create_date' else "(ยื่นตามวันที่จ่ายภาษี)"
    ws['E2'] = f"รายงานสรุปภาษีซื้อ - ขาย {basis_text}"; ws['E2'].font = font_bold; ws['E2'].alignment = align_center
    ws.merge_cells('E3:G3'); ws['E3'] = f"เดือนภาษี {get_thai_month_year(start_date)}"; ws['E3'].alignment = align_center

    headers = [('A5:A6', 'ลำดับ', 5), ('B5:B6', 'วัน/เดือน/ปี', 12), ('C5:C6', 'เลขที่เอกสาร', 15), ('D5:D6', 'ประเภท', 10), ('E5:E6', 'ชื่อผู้ซื้อ / ผู้ขาย', 30), ('F5:F6', 'เลขผู้เสียภาษี', 18), ('G5:H5', 'ภาษีซื้อ (Purchase Tax)', 0), ('G6:G6', 'มูลค่า', 15), ('H6:H6', 'ภาษี', 12), ('I5:J5', 'ภาษีขาย (Sales Tax)', 0), ('I6:I6', 'มูลค่า', 15), ('J6:J6', 'ภาษี', 12)]
    for cell_range, text, width in headers:
        if ':' in cell_range and cell_range.split(':')[0] != cell_range.split(':')[1]: ws.merge_cells(cell_range)
        cell = ws[cell_range.split(':')[0]]; cell.value = text; cell.font = font_bold; cell.alignment = align_center; cell.border = border_thin
        for row in ws[cell_range]:
            for c in row: c.border = border_thin
        if width > 0: ws.column_dimensions[cell_range[0]].width = width

    combined_data = []
    for po in po_qs:
        combined_data.append({'sort_date': po.order_date if report_basis == 'create_date' else po.tax_sender_date, 'priority': 1, 'doc_no': po.po_number, 'type': 'ซื้อ (Buy)', 'name': po.vendor.name if po.vendor else '-', 'tax_id': getattr(po.vendor, 'tax_id', '-'), 'buy_base': po.subtotal, 'buy_vat': po.tax_amount, 'sell_base': 0, 'sell_vat': 0})
    for inv in inv_qs:
        combined_data.append({'sort_date': inv.invoice_date if report_basis == 'create_date' else inv.tax_sender_date, 'priority': 2, 'doc_no': inv.invoice_number, 'type': 'ขาย (Sell)', 'name': inv.recipient_name if inv.recipient_name else (inv.vendor.name if inv.vendor else "เงินสด"), 'tax_id': inv.vendor.tax_id if (inv.vendor and hasattr(inv.vendor, 'tax_id')) else "", 'buy_base': 0, 'buy_vat': 0, 'sell_base': inv.subtotal, 'sell_vat': inv.tax_amount})
    combined_data.sort(key=lambda x: (x['sort_date'], x['priority'], x['doc_no']))

    current_row, seq, tbb, tbv, tsb, tsv = 7, 1, 0, 0, 0, 0
    for item in combined_data:
        d = item['sort_date']; thai_date = f"{d.day:02d}/{d.month:02d}/{d.year+543}" if d else "-"
        tbb += item['buy_base']; tbv += item['buy_vat']; tsb += item['sell_base']; tsv += item['sell_vat']
        row_cells = [(seq, 'center'), (thai_date, 'center'), (item['doc_no'], 'left'), (item['type'], 'center'), (item['name'], 'left'), (item['tax_id'], 'center'), (item['buy_base'], 'number'), (item['buy_vat'], 'number'), (item['sell_base'], 'number'), (item['sell_vat'], 'number')]
        col_indices = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
        for i, (val, style) in enumerate(row_cells):
            cell = ws[f"{col_indices[i]}{current_row}"]; cell.value = val; cell.border = border_thin; cell.font = font_sub
            if style == 'number':
                cell.number_format = '#,##0.00'; cell.alignment = align_right
                if val == 0: cell.font = Font(color="D3D3D3")
            elif style == 'center': cell.alignment = align_center
            else: cell.alignment = Alignment(horizontal='left', vertical='center')
        current_row += 1; seq += 1

    ws.merge_cells(f'A{current_row}:F{current_row}'); ws[f'A{current_row}'] = "รวมทั้งสิ้น"; ws[f'A{current_row}'].alignment = align_right; ws[f'A{current_row}'].font = font_bold
    for c in ['A','B','C','D','E','F']: ws[f'{c}{current_row}'].border = border_thin
    for i, val in enumerate([tbb, tbv, tsb, tsv]):
        cell = ws[f"{['G','H','I','J'][i]}{current_row}"]; cell.value = val; cell.number_format = '#,##0.00'; cell.font = font_bold; cell.alignment = align_right; cell.border = border_thin
    
    current_row += 2; ws[f'H{current_row}'] = "ภาษีขายสุทธิ:"; ws[f'I{current_row}'] = tsv
    ws[f'H{current_row+1}'] = "หัก ภาษีซื้อ:"; ws[f'I{current_row+1}'] = tbv
    ws[f'H{current_row+2}'] = "ภาษีที่ต้องชำระ:"; net_vat = tsv - tbv
    cell = ws[f'I{current_row+2}']; cell.value = net_vat; cell.number_format = '#,##0.00'; cell.font = font_bold
    if net_vat < 0: cell.font = Font(bold=True, color="FF0000")

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Combined_VAT_{report_basis}_{start_date}.xlsx"'
    wb.save(response)
    return response
