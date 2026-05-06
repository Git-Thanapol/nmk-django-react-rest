"""
VAT Export Module - Generates Excel reports from VAT data.
Uses pandas + openpyxl to query DB and write .xlsx files.
"""
import os
import tempfile
from datetime import date, datetime
from decimal import Decimal

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from api.models import VatOrderBuyItem, VatOrderSaleItem

VAT_RATE = Decimal('0.07')  # Thai VAT 7%


def export_vat_report(qs):
    """
    Export matched Buy↔Sale VAT items to Excel. Returns (filepath, filename).
    Filtering is handled by the caller before passing qs.
    """

    # --- 1. Build rows ---
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


def _strip_vat_suffix(supplier: str):
    """Strip /kit, /s16 suffix from supplier name. Returns (clean_name, branch_label)."""
    s = (supplier or '').strip()
    low = s.lower().rstrip()
    for suf, label in (('/kit', 'Kit'), ('/s16', 'S16')):
        if low.endswith(suf):
            return s[:-len(suf)].rstrip(), label
    return s, ''


def export_vat_buy_summary_report(qs, filter_date=None, vat_status=None, query=None):
    """
    Generates Thai-format รายงานภาษีซื้อ (Purchase VAT Report) Excel file matching
    the gov ภ.พ.30 layout. Includes:
        - Title, period, print timestamp, page number header/footer
        - Columns: ลำดับ, วัน/เดือน/ปี, เลขที่ใบกำกับภาษี, ชื่อผู้ขาย,
          เลขประจำตัวผู้เสียภาษี, สำนักงานใหญ่/สาขาที่,
          ค่าสินค้าและบริการ, ภาษีมูลค่าเพิ่ม, ยอดเงินสุทธิ
        - Totals row with item count
        - "* จบรายงาน *" end marker on last page

    Note: VatOrderBuy.items.purchase_price is the net ex-VAT goods base.
    VAT = goods × 7%, ยอดสุทธิ = goods + VAT.
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "รายงานภาษีซื้อ"

    # ---- Page setup (A4 landscape, fit width to 1, allow many pages tall) ----
    ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.orientation = ws.ORIENTATION_LANDSCAPE
    ws.page_margins.left = 0.4
    ws.page_margins.right = 0.4
    ws.page_margins.top = 0.6
    ws.page_margins.bottom = 0.6
    ws.print_options.horizontalCentered = True
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0  # 0 = unlimited pages tall

    # Excel header/footer codes: &P=page, &N=total pages, &L/C/R=left/center/right
    print_dt = datetime.now().strftime('%d/%m/%Y %H:%M')
    ws.oddHeader.right.text = f"พิมพ์เมื่อ {print_dt}\nหน้า &P / &N"
    ws.oddHeader.right.size = 9
    ws.oddFooter.center.text = "&P / &N"
    ws.oddFooter.center.size = 9

    thin = Side(border_style='thin', color='000000')
    border_all = Border(left=thin, right=thin, top=thin, bottom=thin)
    bold = Font(bold=True)
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    right = Alignment(horizontal='right', vertical='center')
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)

    NUM_COLS = 9
    last_col_letter = get_column_letter(NUM_COLS)

    # ---- Title block ----
    r = 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=NUM_COLS)
    c = ws.cell(row=r, column=1, value="รายงานภาษีซื้อ")
    c.font = Font(bold=True, size=16)
    c.alignment = center
    ws.row_dimensions[r].height = 24
    r += 1

    # Subtitle: VAT company / scope
    scope_label = "ทั้งหมด"
    if vat_status == 'vat_only':
        scope_label = "เฉพาะกิจการ VAT (Kit / S16)"
    elif vat_status == 'non_vat':
        scope_label = "เฉพาะกิจการ Non-VAT"
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=NUM_COLS)
    c = ws.cell(row=r, column=1, value=scope_label)
    c.alignment = center
    r += 1

    # Period
    if filter_date:
        period_label = f"ประจำวันที่ {filter_date}"
    else:
        period_label = "ทุกช่วงเวลา"
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=NUM_COLS)
    c = ws.cell(row=r, column=1, value=period_label)
    c.alignment = center
    r += 1

    # Spacer
    r += 1

    # ---- Table header ----
    headers = [
        'ลำดับ', 'วัน/เดือน/ปี', 'เลขที่ใบกำกับภาษี', 'ชื่อผู้ขาย',
        'เลขประจำตัวผู้เสียภาษีอากร', 'สำนักงานใหญ่/สาขาที่',
        'ค่าสินค้าและบริการ', 'ภาษีมูลค่าเพิ่ม', 'ยอดเงินสุทธิ',
    ]
    header_fill = PatternFill('solid', fgColor='D9E1F2')
    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=r, column=col_idx, value=h)
        c.font = bold
        c.fill = header_fill
        c.alignment = center
        c.border = border_all
    ws.row_dimensions[r].height = 38
    header_row = r
    r += 1

    # Column widths tuned for landscape A4
    widths = [6, 12, 18, 32, 18, 14, 15, 14, 15]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # ---- Data rows ----
    total_goods = Decimal('0')
    total_vat = Decimal('0')
    total_net = Decimal('0')
    item_count = 0

    for idx, order in enumerate(qs, start=1):
        item_count += 1
        # purchase_price is net ex-VAT (goods base); VAT = goods * 7%; net = goods + VAT
        goods = Decimal(str(order.total_buy_amount or 0)).quantize(Decimal('0.01'))
        vat_amt = (goods * VAT_RATE).quantize(Decimal('0.01'))
        net = (goods + vat_amt).quantize(Decimal('0.01'))

        total_goods += goods
        total_vat += vat_amt
        total_net += net

        date_str = order.date.strftime('%d/%m/%Y') if order.date else ''
        supplier_clean, branch = _strip_vat_suffix(order.supplier_name)

        values = [
            idx, date_str, order.document_no or '', supplier_clean,
            '',  # tax_id — not in model
            'สำนักงานใหญ่' if branch else '',
            float(goods), float(vat_amt), float(net),
        ]
        for col_idx, v in enumerate(values, start=1):
            cell = ws.cell(row=r, column=col_idx, value=v)
            cell.border = border_all
            if col_idx in (1, 2, 6):
                cell.alignment = center
            elif col_idx >= 7:
                cell.number_format = '#,##0.00'
                cell.alignment = right
            else:
                cell.alignment = left
        r += 1

    # ---- Totals row ----
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=6)
    label_cell = ws.cell(row=r, column=1, value=f"ยอดรวม  (รวมจำนวน {item_count} รายการ)")
    label_cell.font = bold
    label_cell.alignment = right
    for col_idx in range(1, 7):
        ws.cell(row=r, column=col_idx).border = border_all
    for col_idx, val in zip([7, 8, 9], [total_goods, total_vat, total_net]):
        c = ws.cell(row=r, column=col_idx, value=float(val))
        c.font = bold
        c.fill = header_fill
        c.border = border_all
        c.number_format = '#,##0.00'
        c.alignment = right
    r += 2

    # ---- End marker ----
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=NUM_COLS)
    end_cell = ws.cell(row=r, column=1, value="** จบรายงาน **")
    end_cell.font = bold
    end_cell.alignment = center

    # Repeat title + table header on each page
    ws.print_title_rows = f'1:{header_row}'
    ws.print_area = f'A1:{last_col_letter}{r}'

    # Save
    filename = f'VAT_Buy_Report_{date.today().isoformat()}.xlsx'
    filepath = os.path.join(tempfile.gettempdir(), filename)
    wb.save(filepath)
    return filepath, filename
