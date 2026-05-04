"""
Platform CSV/Excel processors for Shopee, TikTok, Lazada.

Resilient column resolution:
- Each internal column has an alias priority list (primary + known variants).
- Falls back to normalized matching (strip, lowercase, remove *, #, spaces, _)
  to handle minor platform changes like 'Phone #' → 'Phone Number' or
  '*หมายเลขติดตามพัสดุ' → 'หมายเลขติดตามพัสดุ'.
- Missing non-critical columns are logged as warnings, not crashes.
- 'order_id' is the only critical column; its absence raises ValueError immediately.
"""

import logging

import pandas as pd

from .utils_import_core import load_data

log = logging.getLogger(__name__)


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    """Normalize a column name for fuzzy matching."""
    return s.strip().lower().replace(' ', '').replace('_', '').replace('*', '').replace('#', '').replace('.', '')


def _resolve_columns(df: pd.DataFrame, aliases: dict) -> tuple:
    """
    Rename df columns using priority alias lists with normalized fallback.

    aliases = {'internal_name': ['Primary Name', 'Alias 1', ...], ...}

    Strategy:
      1. Exact match against df.columns
      2. Normalized match (handles whitespace, case, *, # prefix changes)

    Returns (renamed_df, list_of_missing_internal_names).
    """
    col_norm_map = {_norm(c): c for c in df.columns}
    rename_map = {}
    missing = []

    for internal, candidates in aliases.items():
        if internal.startswith('_'):
            # Address helper fields — not renamed, just resolved separately
            continue
        found = False
        for c in candidates:
            if c in df.columns:
                rename_map[c] = internal
                found = True
                break
        if not found:
            for c in candidates:
                n = _norm(c)
                if n in col_norm_map:
                    rename_map[col_norm_map[n]] = internal
                    found = True
                    break
        if not found:
            missing.append(internal)

    df = df.rename(columns=rename_map)
    return df, missing


def _resolve_address_cols(df: pd.DataFrame, aliases: dict, addr_keys: list) -> list:
    """
    Given addr_keys (list of '_addr_*' alias keys), return the actual df column
    names that exist (after normalised resolution). Used for address construction.
    """
    col_norm_map = {_norm(c): c for c in df.columns}
    resolved = []
    for key in addr_keys:
        candidates = aliases.get(key, [])
        for c in candidates:
            if c in df.columns:
                resolved.append(c)
                break
        else:
            for c in candidates:
                n = _norm(c)
                if n in col_norm_map:
                    resolved.append(col_norm_map[n])
                    break
    return resolved


def _build_address(df: pd.DataFrame, col_candidates: list) -> pd.Series:
    """Join address parts that actually exist in df; silently skip missing ones."""
    available = [c for c in col_candidates if c in df.columns]
    if not available:
        return pd.Series([''] * len(df), index=df.index)
    return df[available].fillna('').astype(str).agg(' '.join, axis=1).str.strip()


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors='coerce').fillna(0)


def _ensure_cols(df: pd.DataFrame, cols: list, default) -> pd.DataFrame:
    """Add any missing columns with a default value."""
    for c in cols:
        if c not in df.columns:
            df[c] = default
    return df


# ─── Column alias definitions ─────────────────────────────────────────────────

SHOPEE_COL_ALIASES = {
    'order_id':         ['หมายเลขคำสั่งซื้อ', 'รหัสคำสั่งซื้อ', 'Order ID', 'Order Number', 'order_id'],
    'order_status':     ['สถานะการสั่งซื้อ', 'สถานะ', 'Order Status', 'Status'],
    'subtotal_raw':     ['ราคาขาย', 'ราคาสินค้า', 'Item Price', 'Seller Price'],
    'total_amount_raw': ['ราคาสินค้าที่ชำระโดยผู้ซื้อ (THB)', 'ราคาสินค้าที่ชำระโดยผู้ซื้อ',
                         'ราคาที่ผู้ซื้อชำระ', 'Buyer Paid Price', 'Total Order Amount', 'ราคาที่ชำระ (THB)'],
    'recipient':        ['ชื่อผู้รับ', 'ชื่อผู้รับสินค้า', 'Recipient', 'Customer Name'],
    'phone':            ['หมายเลขโทรศัพท์', 'เบอร์โทรศัพท์', 'Phone', 'Phone Number', 'Contact'],
    'address':          ['ที่อยู่ในการจัดส่ง', 'ที่อยู่จัดส่ง', 'Shipping Address', 'Address'],
    'tracking_no':      ['*หมายเลขติดตามพัสดุ', 'หมายเลขติดตามพัสดุ', 'เลขติดตามพัสดุ',
                         'Tracking Number', 'Tracking No', 'Tracking ID', 'Tracking'],
    'shipped_date':     ['เวลาส่งสินค้า', 'วันที่จัดส่ง', 'Shipped Date', 'Ship Time', 'Ship Date',
                         'วันจัดส่ง', 'เวลาจัดส่ง'],
    'item_name':        ['ชื่อสินค้า', 'ชื่อรายการสินค้า', 'Product Name', 'Item Name'],
    'quantity':         ['จำนวน', 'จำนวนสินค้า', 'Quantity', 'Qty'],
    'unit_price':       ['ราคาตั้งต้น', 'ราคาต่อหน่วย', 'Unit Price', 'Original Price', 'ราคาสินค้าต่อชิ้น'],
}

TIKTOK_COL_ALIASES = {
    'order_id':      ['Order ID', 'Order Id', 'OrderID', 'Order Number', 'Order #', 'order_id'],
    'order_status':  ['Order Status', 'Status'],
    'subtotal':      ['SKU Subtotal Before Discount', 'SKU Subtotal', 'Subtotal Before Discount',
                      'Item Subtotal', 'SKU Subtotal After Discount'],
    'total_amount':  ['Order Amount', 'Total Amount', 'Grand Total', 'Order Total', 'Total Order Amount'],
    'recipient':     ['Recipient', 'Recipient Name', 'Customer Name', 'Buyer Name', 'Receiver Name'],
    'phone':         ['Phone #', 'Phone', 'Phone Number', 'Contact Number', 'Tel'],
    'tracking_no':   ['Tracking ID', 'Tracking Number', 'Tracking No', 'Track No', 'Tracking No.',
                      'Shipment Tracking Number'],
    'shipped_date':  ['Shipped Time', 'Ship Time', 'Shipment Time', 'Delivery Time', 'Ship Date', 'Shipped Date'],
    'sku':           ['Seller SKU', 'Seller Sku', 'SKU', 'seller_sku', 'Product SKU', 'Item SKU'],
    'item_name':     ['Product Name', 'Item Name', 'product_name', 'Product'],
    'quantity':      ['Quantity', 'Qty', 'quantity'],
    'unit_price':    ['SKU Unit Original Price', 'Unit Price', 'Original Price', 'SKU Original Price',
                      'Item Original Price'],
    'warehouse':     ['Warehouse Name', 'Warehouse', 'warehouse_name', 'Ship From Warehouse', 'Fulfillment Warehouse'],
    # Address parts (underscore prefix = not renamed, resolved separately)
    '_addr_detail':   ['Detail Address', 'Address Detail', 'Address Line 1', 'Street Address', 'Address'],
    '_addr_district': ['District', 'Sub-district', 'Subdistrict', 'Sub District'],
    '_addr_province': ['Province', 'State', 'Region', 'City/Province'],
    '_addr_country':  ['Country'],
}

LAZADA_COL_ALIASES = {
    'order_id':     ['orderNumber', 'Order Number', 'order_id', 'OrderNo', 'Order ID', 'orderId'],
    'order_status': ['status', 'Status', 'Order Status', 'orderStatus'],
    'unit_price':   ['unitPrice', 'Unit Price', 'unit_price', 'Price', 'itemPrice'],
    'subtotal':     ['paidPrice', 'Paid Price', 'Item Price', 'Paid Amount', 'paidAmt', 'itemTotal'],
    'recipient':    ['customerName', 'Customer Name', 'Recipient', 'Buyer Name', 'buyerName', 'receiverName'],
    'phone':        ['billingPhone', 'Phone', 'Contact', 'Customer Phone', 'buyerPhone', 'receiverPhone'],
    'tracking_no':  ['trackingCode', 'Tracking Code', 'Tracking Number', 'Tracking ID', 'trackingNumber',
                     'awbNumber', 'AWB'],
    'shipped_date': ['deliveredDate', 'Delivered Date', 'Ship Date', 'Shipped Date', 'Delivery Date',
                     'shippedDate', 'shipDate'],
    'sku':          ['sellerSku', 'Seller SKU', 'SKU', 'seller_sku', 'SellerSKU', 'sellerSkuId'],
    'item_name':    ['itemName', 'Item Name', 'Product Name', 'productName', 'name'],
    'warehouse':    ['wareHouse', 'Warehouse', 'Warehouse Name', 'warehouseName', 'fulfillmentChannel'],
    # Address parts
    '_addr1':       ['billingAddr', 'Billing Address', 'Address', 'address1', 'shippingAddr'],
    '_addr3':       ['billingAddr3', 'Address Line 3', 'address3'],
    '_addr4':       ['billingAddr4', 'Address Line 4', 'address4'],
    '_addr_city':   ['billingCity', 'City', 'city', 'shippingCity'],
    '_addr_post':   ['billingPostCode', 'Post Code', 'Zip Code', 'Postcode', 'postCode', 'zipCode'],
    '_addr_country':['billingCountry', 'Country', 'country'],
}


# ─── Processors ───────────────────────────────────────────────────────────────

def process_shopee_orders(file_path):
    df = load_data(file_path)

    # 1. Resolve columns with alias + fuzzy fallback
    df, missing = _resolve_columns(df, SHOPEE_COL_ALIASES)
    if missing:
        log.warning("Shopee import — columns not found (will use defaults): %s", missing)

    if 'order_id' not in df.columns:
        raise ValueError("Shopee: ไม่พบคอลัมน์ order_id — ไฟล์อาจผิดรูปแบบหรือเป็นแพลตฟอร์มอื่น")

    # 2. Drop summary rows (Shopee sometimes appends totals at the bottom)
    df = df.dropna(subset=['order_id'])
    df['order_id'] = df['order_id'].astype(str).str.strip()

    # 3. SKU = item_name for Shopee (platform doesn't export a stable SKU field)
    df['sku'] = df['item_name'].copy() if 'item_name' in df.columns else ''

    # 4. Ensure required item columns exist
    df = _ensure_cols(df, ['item_name', 'quantity', 'unit_price'], 0)
    df = _ensure_cols(df, ['order_status', 'recipient', 'phone', 'address', 'tracking_no', 'shipped_date'], '')

    # 5. Header aggregation (one row per order)
    header_agg = {c: 'first' for c in
                  ['order_status', 'recipient', 'phone', 'address', 'tracking_no', 'shipped_date']
                  if c in df.columns}
    if 'total_amount_raw' in df.columns:
        header_agg['total_amount_raw'] = 'first'

    bill_header = df.groupby('order_id').agg(header_agg).reset_index()

    # 6. Subtotal = sum(unit_price * quantity) per order
    df['_sub_calc'] = _safe_numeric(df['unit_price']) * _safe_numeric(df['quantity'])
    sums = df.groupby('order_id')['_sub_calc'].sum().reset_index()
    bill_header = bill_header.merge(sums, on='order_id')
    bill_header = bill_header.rename(columns={'_sub_calc': 'subtotal'})

    if 'total_amount_raw' in bill_header.columns:
        bill_header = bill_header.rename(columns={'total_amount_raw': 'total_amount'})
        bill_header['total_amount'] = _safe_numeric(bill_header['total_amount'])
    else:
        bill_header['total_amount'] = bill_header['subtotal']

    bill_header['shipped_date'] = pd.to_datetime(bill_header.get('shipped_date'), errors='coerce')
    bill_header['warehouse'] = 'Shopee WH'

    # 7. Items
    item_cols = [c for c in ['order_id', 'sku', 'item_name', 'quantity', 'unit_price'] if c in df.columns]
    bill_items = df[item_cols].copy()
    bill_items = _ensure_cols(bill_items, ['sku', 'item_name'], '')
    bill_items = _ensure_cols(bill_items, ['quantity', 'unit_price'], 0)

    return bill_header, bill_items


def process_tiktok_orders(file_path):
    df = load_data(file_path)

    # 1. Resolve address columns BEFORE general rename (they keep original names)
    addr_cols = _resolve_address_cols(df, TIKTOK_COL_ALIASES,
                                      ['_addr_detail', '_addr_district', '_addr_province', '_addr_country'])
    df['FullAddress'] = _build_address(df, addr_cols)

    # 2. Resolve standard columns with alias + fuzzy fallback
    df, missing = _resolve_columns(df, TIKTOK_COL_ALIASES)
    if missing:
        log.warning("TikTok import — columns not found (will use defaults): %s", missing)

    if 'order_id' not in df.columns:
        raise ValueError("TikTok: ไม่พบคอลัมน์ order_id — ไฟล์อาจผิดรูปแบบหรือเป็นแพลตฟอร์มอื่น")

    df['order_id'] = df['order_id'].astype(str).str.strip()
    df['address'] = df['FullAddress']

    # 3. Ensure all required columns exist
    df = _ensure_cols(df, ['order_status', 'recipient', 'phone', 'tracking_no', 'shipped_date', 'warehouse'], '')
    df = _ensure_cols(df, ['subtotal', 'total_amount', 'quantity', 'unit_price'], 0)
    df = _ensure_cols(df, ['sku', 'item_name'], '')

    df['subtotal'] = _safe_numeric(df['subtotal'])
    df['total_amount'] = _safe_numeric(df['total_amount'])

    # 4. Header aggregation
    bill_header = df.groupby('order_id').agg({
        'order_status': 'first',
        'subtotal':     'sum',
        'total_amount': 'first',
        'recipient':    'first',
        'phone':        'first',
        'address':      'first',
        'tracking_no':  'first',
        'shipped_date': 'first',
        'warehouse':    'first',
    }).reset_index()

    bill_header['shipped_date'] = pd.to_datetime(bill_header['shipped_date'], dayfirst=True, errors='coerce')

    # 5. Items
    bill_items = df[['order_id', 'sku', 'item_name', 'quantity', 'unit_price']].copy()

    return bill_header, bill_items


def process_lazada_orders(file_path):
    df = load_data(file_path)

    # 1. Resolve address columns BEFORE general rename
    addr_cols = _resolve_address_cols(df, LAZADA_COL_ALIASES,
                                      ['_addr1', '_addr3', '_addr4', '_addr_city', '_addr_post', '_addr_country'])
    df['FullAddress'] = _build_address(df, addr_cols)

    # 2. Resolve standard columns with alias + fuzzy fallback
    df, missing = _resolve_columns(df, LAZADA_COL_ALIASES)
    if missing:
        log.warning("Lazada import — columns not found (will use defaults): %s", missing)

    if 'order_id' not in df.columns:
        raise ValueError("Lazada: ไม่พบคอลัมน์ order_id — ไฟล์อาจผิดรูปแบบหรือเป็นแพลตฟอร์มอื่น")

    df['order_id'] = df['order_id'].astype(str).str.strip()
    df['address'] = df['FullAddress']

    # 3. Ensure all required columns exist
    df = _ensure_cols(df, ['order_status', 'recipient', 'phone', 'tracking_no', 'shipped_date', 'warehouse'], '')
    df = _ensure_cols(df, ['subtotal', 'unit_price'], 0)
    df = _ensure_cols(df, ['sku', 'item_name'], '')

    df['subtotal'] = _safe_numeric(df['subtotal'])
    df['unit_price'] = _safe_numeric(df['unit_price'])

    # Lazada exports one item per row with no quantity field → default 1
    df['quantity'] = 1
    df['total_amount'] = df['subtotal']

    # 4. Header aggregation
    bill_header = df.groupby('order_id').agg({
        'order_status': 'first',
        'subtotal':     'sum',
        'total_amount': 'sum',
        'recipient':    'first',
        'phone':        'first',
        'address':      'first',
        'tracking_no':  'first',
        'shipped_date': 'first',
        'warehouse':    'first',
    }).reset_index()

    bill_header['shipped_date'] = pd.to_datetime(bill_header['shipped_date'], dayfirst=True, errors='coerce')

    # 5. Items
    bill_items = df[['order_id', 'sku', 'item_name', 'quantity', 'unit_price']].copy()

    return bill_header, bill_items
