import pandas as pd
from .utils_import_core import load_data

def process_shopee_orders(file_path):
    df = load_data(file_path)

    # 1. Clean Data
    # Shopee sometimes puts 'Total' lines at the bottom
    df = df.dropna(subset=['หมายเลขคำสั่งซื้อ']) 

    # 2. Standardize Columns (Thai -> Internal Standard)
    # Map: Source Column -> Internal Standard Column
    col_map = {
        'หมายเลขคำสั่งซื้อ': 'order_id',
        'สถานะการสั่งซื้อ': 'order_status',
        'ราคาขาย': 'subtotal_raw', # Usually needs summing
        'ราคาสินค้าที่ชำระโดยผู้ซื้อ (THB)': 'total_amount_raw',
        'ชื่อผู้รับ': 'recipient',
        'หมายเลขโทรศัพท์': 'phone',
        'ที่อยู่ในการจัดส่ง': 'address',
        '*หมายเลขติดตามพัสดุ': 'tracking_no',
        'เวลาส่งสินค้า': 'shipped_date',
        'ชื่อสินค้า': 'item_name',
        #'เลขรหัสสินค้า': 'sku', # Shopee 'Parent SKU' or Reference
        'จำนวน': 'quantity',
        'ราคาตั้งต้น': 'unit_price'
    }
    
    # Rename available columns
    df = df.rename(columns=col_map)
    df['sku'] = df['item_name'].copy()

    # 3. Create Header DataFrame (Group by Order)
    # We need to aggregate because Shopee CSV has one row per Item
    bill_header = df.groupby('order_id').agg({
        'order_status': 'first',
        'total_amount_raw': 'first', # Usually the same for all rows
        'recipient': 'first',
        'phone': 'first',
        'address': 'first',
        'tracking_no': 'first',
        'shipped_date': 'first'
    }).reset_index()

    # Calculate Header Totals from Items
    # Shopee 'Total Amount' in CSV includes shipping, but let's sum items for subtotal
    # (Converting string to float for summation)
    df['sub_calc'] = pd.to_numeric(df['unit_price'], errors='coerce') * pd.to_numeric(df['quantity'], errors='coerce')
    
    sums = df.groupby('order_id')['sub_calc'].sum().reset_index()
    bill_header = bill_header.merge(sums, on='order_id')
    
    # Rename for Universal Engine
    bill_header = bill_header.rename(columns={
        'total_amount_raw': 'total_amount',
        'sub_calc': 'subtotal'
    })
    
    # Date Conversion
    bill_header['shipped_date'] = pd.to_datetime(bill_header['shipped_date'], errors='coerce')
    bill_header['warehouse'] = "Shopee WH"

    # 4. Create Items DataFrame
    bill_items = df[[
        'order_id', 'sku', 'item_name', 'quantity', 'unit_price'
    ]].copy()

    return bill_header, bill_items


def process_tiktok_orders(file_path):

    df = load_data(file_path)

    # 1. Address Logic (Specific to TikTok)
    cols = ['Detail Address', 'District', 'Province', 'Country', 'Zipcode']
    df['FullAddress'] = df[cols].fillna('').astype(str).agg(' '.join, axis=1)

    # 2. Rename to Standard
    col_map = {
        'Order ID': 'order_id',
        'Order Status': 'order_status',
        'SKU Subtotal Before Discount': 'subtotal',
        'Total Order Amount': 'total_amount',
        'Recipient': 'recipient',
        'Phone #': 'phone',
        'Tracking ID': 'tracking_no',
        'Shipped Time': 'shipped_date',
        'Seller SKU': 'sku',
        'Product Name': 'item_name',
        'Quantity': 'quantity',
        'SKU Unit Original Price': 'unit_price',
        'Warehouse Name': 'warehouse'
    }
    df = df.rename(columns=col_map)
    df['address'] = df['FullAddress']

    # 3. Headers
    bill_header = df.groupby('order_id').agg({
        'order_status': 'first',
        'subtotal': 'sum',
        'total_amount': 'first',
        'recipient': 'first',
        'phone': 'first',
        'address': 'first',
        'tracking_no': 'first',
        'shipped_date': 'first',
        'warehouse': 'first'
    }).reset_index()
    
    bill_header['shipped_date'] = pd.to_datetime(bill_header['shipped_date'], dayfirst=True, errors='coerce')

    # 4. Items
    bill_items = df[[
        'order_id', 'sku', 'item_name', 'quantity', 'unit_price'
    ]].copy()

    return bill_header, bill_items


def process_lazada_orders(file_path):
    df = load_data(file_path)

    # 1. Address Logic (Specific to TikTok)
    cols = ['billingAddr', 'billingAddr3', 'billingAddr4', 'billingCity', 'billingPostCode', 'billingCountry']
    df['FullAddress'] = df[cols].fillna('').astype(str).agg(' '.join, axis=1)

    # 2. Rename to Standard
    col_map = {
        'orderNumber': 'order_id',
        'status': 'order_status',
        'unitPrice': 'unit_price',
        'paidPrice': 'subtotal',        
        'customerName': 'recipient',
        'billingPhone': 'phone',
        'trackingCode': 'tracking_no',
        'deliveredDate': 'shipped_date',
        'sellerSku': 'sku',
        'itemName': 'item_name',
        'wareHouse': 'warehouse'
        #'Total Order Amount': 'total_amount',
        #'Quantity': 'quantity',
        
    }
    df = df.rename(columns=col_map)
    df['address'] = df['FullAddress']
    df['quantity'] = 1
    df['total_amount'] = df['subtotal']

    # 3. Headers
    bill_header = df.groupby('order_id').agg({
        'order_status': 'first',
        'subtotal': 'sum',
        'total_amount': 'sum',
        'recipient': 'first',
        'phone': 'first',
        'address': 'first',
        'tracking_no': 'first',
        'shipped_date': 'first',
        'warehouse': 'first'
    }).reset_index()
    
    bill_header['shipped_date'] = pd.to_datetime(bill_header['shipped_date'], dayfirst=True, errors='coerce')

    # 4. Items
    bill_items = df[[
        'order_id', 'sku', 'item_name', 'quantity', 'unit_price'
    ]].copy()

    return bill_header, bill_items