import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from django.http import HttpResponse
from datetime import datetime
from django.db.models import Sum, Q, F
from django.db.models.functions import Coalesce
from .models import Product, PurchaseItem, InvoiceItem # Ensure Product is imported

def get_thai_datetime():
    """Returns current datetime in Thai format: 2 ตุลาคม 2568 18:46 น."""
    now = datetime.now()
    thai_months = [
        "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    year = now.year + 543
    return f"{now.day} {thai_months[now.month]} {year} {now.strftime('%H:%M')} น."

def get_thai_month_year(date_obj):
    """Returns Month Year in Thai: ตุลาคม ปี พ.ศ. 2568"""
    if not date_obj: return ""
    thai_months = [
        "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
        "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
    ]
    return f"{thai_months[date_obj.month]} ปี พ.ศ. {date_obj.year + 543}"

def generate_purchase_tax_report(queryset, company, start_date, end_date):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Purchase Tax Report"

    # --- Styles ---
    font_header = Font(name='Sarabun', size=14, bold=True)
    font_sub = Font(name='Sarabun', size=11)
    font_bold = Font(name='Sarabun', size=11, bold=True)
    border_thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    align_center = Alignment(horizontal='center', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')

    # --- 1. HEADER SECTION ---
    ws.merge_cells('A1:B1')
    ws['A1'] = get_thai_datetime()
    ws['A1'].alignment = align_left
    
    ws.merge_cells('D1:F1')
    ws['D1'] = str(company) # Use str() in case company is an object
    ws['D1'].font = font_header
    ws['D1'].alignment = align_center

    ws['H1'] = "หน้า 1" 
    ws['H1'].alignment = align_right

    ws.merge_cells('D2:F2')
    ws['D2'] = "รายงานภาษีซื้อ"
    ws['D2'].font = font_bold
    ws['D2'].alignment = align_center

    ws['H2'] = "สำนักงานใหญ่" 
    ws['H2'].alignment = align_right

    ws.merge_cells('D3:F3')
    ws['D3'] = f"เดือนภาษี {get_thai_month_year(start_date)}" 
    ws['D3'].alignment = align_center

    # Safe access to tax_id
    tax_id = getattr(company, 'tax_id', '-')
    ws['H3'] = f"เลขประจำตัวผู้เสียภาษี {tax_id}"
    ws['H3'].alignment = align_right

    # --- 2. TABLE HEADERS ---
    headers = [
        ('A5:A6', 'ลำดับ', 5),
        ('B5:C5', 'ใบกำกับภาษี', 0),
        ('B6:B6', 'วัน/เดือน/ปี', 12),
        ('C6:C6', 'เลขที่', 15),
        ('D5:D6', 'ชื่อผู้ขายสินค้า/ผู้รับบริการ', 30),
        ('E5:E6', 'เลขประจำตัวผู้เสียภาษี\nของผู้ขายสินค้า', 20),
        ('F5:G5', 'สถานประกอบการ', 0),
        ('F6:F6', 'สนญ.', 8),
        ('G6:G6', 'สาขาที่', 8),
        ('H5:H6', 'มูลค่าสินค้าหรือบริการ', 15),
        ('I5:I6', 'จำนวนเงินภาษีมูลค่าเพิ่ม', 15),
    ]

    for cell_range, text, width in headers:
        ws.merge_cells(cell_range)
        top_left_cell = ws[cell_range.split(':')[0]]
        top_left_cell.value = text
        top_left_cell.font = font_bold
        top_left_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        for row in ws[cell_range]:
            for cell in row:
                cell.border = border_thin
        
        col_letter = cell_range.split(':')[0][0]
        if width > 0:
            ws.column_dimensions[col_letter].width = width

    ws.print_title_rows = '1:6'

    # --- 3. DATA POPULATION ---
    current_row = 7
    seq = 1
    total_value = 0
    total_vat = 0

    for po in queryset:
        # FIX: Changed po.date to po.order_date
        po_date = po.order_date 
        thai_date = f"{po_date.day:02d}/{po_date.month:02d}/{po_date.year+543}"
        
        vendor_name = po.vendor.name if po.vendor else "Unknown"
        # Check if vendor has tax_id field, otherwise empty
        vendor_tax = getattr(po.vendor, 'tax_id', '') 
        
        # Use total_amount logic based on tax inclusion
        # Your model stores 'subtotal' and 'tax_amount' calculated in calculate_totals()
        
        # For Purchase Tax Report:
        # Column H = Base Value (Subtotal)
        # Column I = VAT Amount
        
        val = po.subtotal
        vat = po.tax_amount
        
        total_value += val
        total_vat += vat

        # Prepare Data Row
        data = [
            (seq, 'center'),
            (thai_date, 'center'),
            (po.po_number, 'left'), 
            (vendor_name, 'left'),
            (vendor_tax, 'center'),
            ('X', 'center'), 
            ('', 'center'),
            (val, 'number'),
            (vat, 'number'),
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
                cell.alignment = align_left

        current_row += 1
        seq += 1

    # --- 4. TOTALS ROW ---
    ws.merge_cells(f'A{current_row}:G{current_row}')
    cell = ws[f'A{current_row}']
    cell.value = "รวมทั้งสิ้น"
    cell.font = font_bold
    cell.alignment = align_right
    cell.border = border_thin
    
    for col in ['B','C','D','E','F','G']:
        ws[f'{col}{current_row}'].border = border_thin

    for col, val in [('H', total_value), ('I', total_vat)]:
        cell = ws[f'{col}{current_row}']
        cell.value = val
        cell.font = font_bold
        cell.number_format = '#,##0.00'
        cell.alignment = align_right
        cell.border = border_thin

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Purchase_Tax_Report_{start_date}.xlsx"'
    wb.save(response)
    return response

def generate_sales_tax_report(queryset, company, start_date, end_date):
    """
    Generates Output VAT Report (Sales Tax) based on Invoice model.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sales Tax Report"

    # --- Styles ---
    font_header = Font(name='Sarabun', size=14, bold=True)
    font_sub = Font(name='Sarabun', size=11)
    font_bold = Font(name='Sarabun', size=11, bold=True)
    border_thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    align_center = Alignment(horizontal='center', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')

    # --- 1. HEADER SECTION ---
    # Row 1: Print Date, Company, Page
    ws.merge_cells('A1:B1')
    ws['A1'] = get_thai_datetime()
    ws['A1'].alignment = align_left
    
    ws.merge_cells('D1:F1')
    ws['D1'] = str(company)
    ws['D1'].font = font_header
    ws['D1'].alignment = align_center

    ws['H1'] = "หน้า 1" 
    ws['H1'].alignment = align_right

    # Row 2: Report Name
    ws.merge_cells('D2:F2')
    ws['D2'] = "รายงานภาษีขาย" # <--- CHANGED TITLE
    ws['D2'].font = font_bold
    ws['D2'].alignment = align_center

    ws['H2'] = "สำนักงานใหญ่" 
    ws['H2'].alignment = align_right

    # Row 3: Month/Tax ID
    ws.merge_cells('D3:F3')
    ws['D3'] = f"เดือนภาษี {get_thai_month_year(start_date)}" 
    ws['D3'].alignment = align_center

    tax_id = getattr(company, 'tax_id', '-')
    ws['H3'] = f"เลขประจำตัวผู้เสียภาษี {tax_id}"
    ws['H3'].alignment = align_right

    # --- 2. TABLE HEADERS ---
    headers = [
        ('A5:A6', 'ลำดับ', 5),
        ('B5:C5', 'ใบกำกับภาษี', 0),
        ('B6:B6', 'วัน/เดือน/ปี', 12),
        ('C6:C6', 'เลขที่', 15),
        ('D5:D6', 'ชื่อผู้ซื้อสินค้า/ผู้รับบริการ', 30), # <--- CHANGED: Buyer Name
        ('E5:E6', 'เลขประจำตัวผู้เสียภาษี\nของผู้ซื้อสินค้า', 20), # <--- CHANGED: Buyer Tax ID
        ('F5:G5', 'สถานประกอบการ', 0),
        ('F6:F6', 'สนญ.', 8),
        ('G6:G6', 'สาขาที่', 8),
        ('H5:H6', 'มูลค่าสินค้าหรือบริการ', 15),
        ('I5:I6', 'จำนวนเงินภาษีมูลค่าเพิ่ม', 15),
    ]

    for cell_range, text, width in headers:
        ws.merge_cells(cell_range)
        top_left_cell = ws[cell_range.split(':')[0]]
        top_left_cell.value = text
        top_left_cell.font = font_bold
        top_left_cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        for row in ws[cell_range]:
            for cell in row:
                cell.border = border_thin
        
        col_letter = cell_range.split(':')[0][0]
        if width > 0:
            ws.column_dimensions[col_letter].width = width

    ws.print_title_rows = '1:6'

    # --- 3. DATA POPULATION ---
    current_row = 7
    seq = 1
    total_value = 0
    total_vat = 0

    for inv in queryset:
        # Date
        inv_date = inv.invoice_date
        thai_date = f"{inv_date.day:02d}/{inv_date.month:02d}/{inv_date.year+543}"
        
        # Customer Name Logic: Prioritize Recipient Name (Online), fallback to Customer FK
        cust_name = inv.recipient_name if inv.recipient_name else (inv.customer.name if inv.customer else "เงินสด/ไม่ระบุ")
        
        # Tax ID Logic: Try to get from Customer object
        cust_tax = ""
        if inv.customer and hasattr(inv.customer, 'tax_id'):
            cust_tax = inv.customer.tax_id
        
        # Financials: invoice.subtotal is the taxable base (calculated in your model)
        val = inv.subtotal
        vat = inv.tax_amount
        
        total_value += val
        total_vat += vat

        # Row Data
        data = [
            (seq, 'center'),
            (thai_date, 'center'),
            (inv.invoice_number, 'left'),
            (cust_name, 'left'),
            (cust_tax, 'center'),
            ('X', 'center'), # Assume HQ for now
            ('', 'center'),
            (val, 'number'),
            (vat, 'number'),
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
                cell.alignment = align_left

        current_row += 1
        seq += 1

    # --- 4. TOTALS ---
    ws.merge_cells(f'A{current_row}:G{current_row}')
    cell = ws[f'A{current_row}']
    cell.value = "รวมทั้งสิ้น"
    cell.font = font_bold
    cell.alignment = align_right
    cell.border = border_thin
    
    for col in ['B','C','D','E','F','G']:
        ws[f'{col}{current_row}'].border = border_thin

    for col, val in [('H', total_value), ('I', total_vat)]:
        cell = ws[f'{col}{current_row}']
        cell.value = val
        cell.font = font_bold
        cell.number_format = '#,##0.00'
        cell.alignment = align_right
        cell.border = border_thin

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Sales_Tax_Report_{start_date}.xlsx"'
    wb.save(response)
    return response


def generate_stock_report(company, start_date, end_date):
    """
    Generates Stock Report showing movement within range and absolute current balance.
    Formula: Actual Stock = All Time Buy - All Time Sell (Allows negative results)
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Stock Report"

    # --- Styles (Reusing your standard styles) ---
    font_header = Font(name='Sarabun', size=14, bold=True)
    font_sub = Font(name='Sarabun', size=11)
    font_bold = Font(name='Sarabun', size=11, bold=True)
    border_thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    align_center = Alignment(horizontal='center', vertical='center')
    align_right = Alignment(horizontal='right', vertical='center')
    align_left = Alignment(horizontal='left', vertical='center')

    # --- 1. HEADER SECTION ---
    # Row 1
    ws.merge_cells('A1:B1')
    ws['A1'] = get_thai_datetime()
    ws['A1'].alignment = align_left
    
    ws.merge_cells('C1:E1')
    ws['C1'] = str(company)
    ws['C1'].font = font_header
    ws['C1'].alignment = align_center

    ws['F1'] = "หน้า 1"
    ws['F1'].alignment = align_right

    # Row 2
    ws.merge_cells('C2:E2')
    ws['C2'] = "รายงานสินค้าคงเหลือ" # Stock Report
    ws['C2'].font = font_bold
    ws['C2'].alignment = align_center

    ws['F2'] = "สำนักงานใหญ่"
    ws['F2'].alignment = align_right

    # Row 3
    ws.merge_cells('C3:E3')
    # Custom Date Range Text
    start_thai = f"{start_date.day}/{start_date.month}/{start_date.year+543}"
    end_thai = f"{end_date.day}/{end_date.month}/{end_date.year+543}"
    ws['C3'] = f"ข้อมูลตั้งแต่วันที่ {start_thai} ถึง {end_thai}" 
    ws['C3'].alignment = align_center

    tax_id = getattr(company, 'tax_id', '-')
    ws['F3'] = f"เลขประจำตัวผู้เสียภาษี {tax_id}"
    ws['F3'].alignment = align_right

    # --- 2. TABLE HEADERS ---
    headers = [
        ('A5:A6', 'ลำดับ', 8),
        ('B5:B6', 'รหัสสินค้า (SKU)', 20),
        ('C5:C6', 'ชื่อสินค้า', 40),
        ('D5:D5', 'ความเคลื่อนไหว (ช่วงเวลา)', 0), # Parent Header
        ('D6:D6', 'รับเข้า', 15),
        ('E6:E6', 'ขายออก', 15),
        ('F5:F6', 'คงเหลือปัจจุบัน\n(ทั้งหมด)', 20),
    ]

    # Merge Parent Header "Movement"
    ws.merge_cells('D5:E5')
    ws['D5'].alignment = align_center
    ws['D5'].font = font_bold
    ws['D5'].border = border_thin

    for cell_range, text, width in headers:
        # Skip if merged manually above
        if cell_range != 'D5:D5':
            ws.merge_cells(cell_range)
        
        top_left = cell_range.split(':')[0]
        cell = ws[top_left]
        cell.value = text
        cell.font = font_bold
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        # Apply borders
        for row in ws[cell_range]:
            for c in row:
                c.border = border_thin
        
        # Set Width
        if width > 0:
            col_letter = top_left[0]
            ws.column_dimensions[col_letter].width = width

    ws.print_title_rows = '1:6'

    # --- 3. DATA CALCULATION & POPULATION ---
    current_row = 7
    seq = 1

    # Fetch all active products
    products = Product.objects.filter(is_active=True).order_by('name')

    for product in products:
        # A. Movement within Date Range
        # Note: Filter by company to ensure multi-company isolation
        range_receive = PurchaseItem.objects.filter(
            product=product,
            #purchase_order__company=company,
            purchase_order__order_date__range=[start_date, end_date]
        ).aggregate(sum_qty=Coalesce(Sum('quantity'), 0))['sum_qty']

        range_sales = InvoiceItem.objects.filter(
            product=product,
            #invoice__company=company,
            invoice__status='BILLED', # Only count Billed sales
            invoice__invoice_date__range=[start_date, end_date]
        ).aggregate(sum_qty=Coalesce(Sum('quantity'), 0))['sum_qty']

        # B. Actual Stock (All Time)
        # Formula: Total In - Total Out
        all_time_in = PurchaseItem.objects.filter(
            product=product,
            #purchase_order__company=company
        ).aggregate(sum_qty=Coalesce(Sum('quantity'), 0))['sum_qty']

        all_time_out = InvoiceItem.objects.filter(
            product=product,
            #invoice__company=company,
            #invoice__status='BILLED'
        ).aggregate(sum_qty=Coalesce(Sum('quantity'), 0))['sum_qty']

        actual_stock = all_time_in - all_time_out

        # Skip rows if no movement AND no stock (optional, keeps report clean)
        if range_receive == 0 and range_sales == 0 and actual_stock == 0:
            continue

        # Write Row
        row_data = [
            (seq, 'center'),
            (product.sku if hasattr(product, 'sku') else '-', 'left'), # Adjust field name if needed
            (product.name, 'left'),
            (range_receive, 'number'),
            (range_sales, 'number'),
            (actual_stock, 'number_bold'), # Bold for emphasis
        ]

        col_indices = ['A', 'B', 'C', 'D', 'E', 'F']

        for i, (val, style) in enumerate(row_data):
            cell = ws[f"{col_indices[i]}{current_row}"]
            cell.value = val
            cell.border = border_thin
            cell.font = font_sub

            if 'number' in style:
                cell.number_format = '#,##0'
                cell.alignment = align_right
                if style == 'number_bold':
                    cell.font = font_bold
                    # Highlight negative stock in Red
                    if val < 0:
                        cell.font = Font(name='Sarabun', size=11, bold=True, color="FF0000")
            elif style == 'center':
                cell.alignment = align_center
            else:
                cell.alignment = align_left

        current_row += 1
        seq += 1

    # --- Response ---
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="Stock_Report_{start_date}.xlsx"'
    wb.save(response)
    return response

