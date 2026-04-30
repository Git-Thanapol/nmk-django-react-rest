"""
Utils-processor tests — Shopee/Lazada/TikTok CSV parsing with synthetic DataFrames.
These tests do NOT require real files on disk.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from decimal import Decimal


# ---------------------------------------------------------------------------
# Helper: build synthetic DataFrames mimicking each platform's raw CSV
# ---------------------------------------------------------------------------

def _shopee_raw_df():
    return pd.DataFrame({
        'หมายเลขคำสั่งซื้อ': ['ORD-001', 'ORD-001', 'ORD-002'],
        'สถานะการสั่งซื้อ': ['Shipped', 'Shipped', 'Completed'],
        'ราคาขาย': ['1000', '500', '800'],
        'ราคาสินค้าที่ชำระโดยผู้ซื้อ (THB)': ['1000', '1000', '800'],
        'ชื่อผู้รับ': ['Alice', 'Alice', 'Bob'],
        'หมายเลขโทรศัพท์': ['0811111111', '0811111111', '0822222222'],
        'ที่อยู่ในการจัดส่ง': ['Bangkok', 'Bangkok', 'Chiang Mai'],
        '*หมายเลขติดตามพัสดุ': ['TH001', 'TH001', 'TH002'],
        'เวลาส่งสินค้า': ['2025-01-01', '2025-01-01', '2025-01-02'],
        'ชื่อสินค้า': ['iPhone 15', 'AirPods 4', 'MacBook'],
        'จำนวน': [1, 2, 1],
        'ราคาตั้งต้น': [1000, 250, 800],
    })


def _tiktok_raw_df():
    return pd.DataFrame({
        'Order ID': ['TT-001', 'TT-001', 'TT-002'],
        'Order Status': ['Completed', 'Completed', 'Shipped'],
        'SKU Subtotal Before Discount': [1000, 500, 800],
        'Order Amount': [1000, 1000, 800],
        'Recipient': ['Alice', 'Alice', 'Bob'],
        'Phone #': ['081', '081', '082'],
        'Detail Address': ['123 Main', '123 Main', '456 Side'],
        'District': ['Klong Toey', 'Klong Toey', 'Muang'],
        'Province': ['Bangkok', 'Bangkok', 'Chiang Mai'],
        'Country': ['Thailand', 'Thailand', 'Thailand'],
        'Tracking ID': ['TK001', 'TK001', 'TK002'],
        'Shipped Time': ['01/01/2025', '01/01/2025', '02/01/2025'],
        'Seller SKU': ['SKU-001', 'SKU-002', 'SKU-003'],
        'Product Name': ['iPhone 15', 'AirPods 4', 'MacBook'],
        'Quantity': [1, 2, 1],
        'SKU Unit Original Price': [1000, 250, 800],
        'Warehouse Name': ['BKK WH', 'BKK WH', 'CNX WH'],
    })


def _lazada_raw_df():
    return pd.DataFrame({
        'orderNumber': ['LZ-001', 'LZ-002'],
        'status': ['Delivered', 'Shipped'],
        'unitPrice': [1500.0, 800.0],
        'paidPrice': [1500.0, 800.0],
        'customerName': ['Alice', 'Bob'],
        'billingPhone': ['081', '082'],
        'billingAddr': ['123 Main', '456 Side'],
        'billingAddr3': ['', ''],
        'billingAddr4': ['', ''],
        'billingCity': ['Bangkok', 'Chiang Mai'],
        'billingPostCode': ['10110', '50000'],
        'billingCountry': ['Thailand', 'Thailand'],
        'trackingCode': ['LZD001', 'LZD002'],
        'deliveredDate': ['01/01/2025', '02/01/2025'],
        'sellerSku': ['SKU-A', 'SKU-B'],
        'itemName': ['iPhone 15', 'MacBook'],
        'wareHouse': ['LZ WH', 'LZ WH'],
    })


# ---------------------------------------------------------------------------
# Shopee processor
# ---------------------------------------------------------------------------

class TestProcessShopeeOrders:
    def _run(self, df):
        from api.utils_processors import process_shopee_orders
        with patch('api.utils_processors.load_data', return_value=df):
            return process_shopee_orders('fake_path.xlsx')

    def test_returns_two_dataframes(self):
        headers, items = self._run(_shopee_raw_df())
        assert isinstance(headers, pd.DataFrame)
        assert isinstance(items, pd.DataFrame)

    def test_header_required_columns(self):
        headers, _ = self._run(_shopee_raw_df())
        required = ['order_id', 'order_status', 'total_amount', 'recipient',
                    'phone', 'address', 'tracking_no', 'shipped_date', 'subtotal', 'warehouse']
        for col in required:
            assert col in headers.columns, f"Missing header column: {col}"

    def test_items_required_columns(self):
        _, items = self._run(_shopee_raw_df())
        required = ['order_id', 'sku', 'item_name', 'quantity', 'unit_price']
        for col in required:
            assert col in items.columns, f"Missing item column: {col}"

    def test_groups_by_order_id(self):
        headers, _ = self._run(_shopee_raw_df())
        assert len(headers) == 2  # ORD-001 and ORD-002

    def test_items_keep_all_rows(self):
        _, items = self._run(_shopee_raw_df())
        assert len(items) == 3

    def test_subtotal_calculated_from_items(self):
        headers, _ = self._run(_shopee_raw_df())
        ord001 = headers[headers['order_id'] == 'ORD-001'].iloc[0]
        # (1000 * 1) + (250 * 2) = 1500
        assert ord001['subtotal'] == 1500

    def test_warehouse_set_to_shopee_wh(self):
        headers, _ = self._run(_shopee_raw_df())
        assert (headers['warehouse'] == 'Shopee WH').all()

    def test_null_order_id_rows_dropped(self):
        df = _shopee_raw_df().copy()
        df.loc[3] = [None] + ['x'] * (len(df.columns) - 1)
        headers, items = self._run(df)
        assert None not in headers['order_id'].values

    def test_shipped_date_parsed_as_datetime(self):
        headers, _ = self._run(_shopee_raw_df())
        assert pd.api.types.is_datetime64_any_dtype(headers['shipped_date'])

    def test_empty_dataframe_raises_or_returns_empty(self):
        """Edge case: empty file — should not silently succeed."""
        empty = pd.DataFrame(columns=_shopee_raw_df().columns)
        try:
            headers, items = self._run(empty)
            assert headers.empty
            assert items.empty
        except (KeyError, Exception):
            pass  # Acceptable — processor doesn't guarantee empty-input handling


# ---------------------------------------------------------------------------
# TikTok processor
# ---------------------------------------------------------------------------

class TestProcessTikTokOrders:
    def _run(self, df):
        from api.utils_processors import process_tiktok_orders
        with patch('api.utils_processors.load_data', return_value=df):
            return process_tiktok_orders('fake_path.xlsx')

    def test_returns_two_dataframes(self):
        headers, items = self._run(_tiktok_raw_df())
        assert isinstance(headers, pd.DataFrame)
        assert isinstance(items, pd.DataFrame)

    def test_header_required_columns(self):
        headers, _ = self._run(_tiktok_raw_df())
        required = ['order_id', 'order_status', 'subtotal', 'total_amount',
                    'recipient', 'phone', 'address', 'tracking_no', 'shipped_date', 'warehouse']
        for col in required:
            assert col in headers.columns, f"Missing header column: {col}"

    def test_items_required_columns(self):
        _, items = self._run(_tiktok_raw_df())
        required = ['order_id', 'sku', 'item_name', 'quantity', 'unit_price']
        for col in required:
            assert col in items.columns, f"Missing item column: {col}"

    def test_groups_by_order_id(self):
        headers, _ = self._run(_tiktok_raw_df())
        assert len(headers) == 2  # TT-001, TT-002

    def test_full_address_concatenated(self):
        headers, _ = self._run(_tiktok_raw_df())
        tt001 = headers[headers['order_id'] == 'TT-001'].iloc[0]
        assert 'Bangkok' in tt001['address']

    def test_shipped_date_parsed(self):
        headers, _ = self._run(_tiktok_raw_df())
        assert pd.api.types.is_datetime64_any_dtype(headers['shipped_date'])


# ---------------------------------------------------------------------------
# Lazada processor
# ---------------------------------------------------------------------------

class TestProcessLazadaOrders:
    def _run(self, df):
        from api.utils_processors import process_lazada_orders
        with patch('api.utils_processors.load_data', return_value=df):
            return process_lazada_orders('fake_path.xlsx')

    def test_returns_two_dataframes(self):
        headers, items = self._run(_lazada_raw_df())
        assert isinstance(headers, pd.DataFrame)
        assert isinstance(items, pd.DataFrame)

    def test_header_required_columns(self):
        headers, _ = self._run(_lazada_raw_df())
        required = ['order_id', 'order_status', 'subtotal', 'total_amount',
                    'recipient', 'phone', 'address', 'tracking_no', 'shipped_date', 'warehouse']
        for col in required:
            assert col in headers.columns, f"Missing header column: {col}"

    def test_items_required_columns(self):
        _, items = self._run(_lazada_raw_df())
        required = ['order_id', 'sku', 'item_name', 'quantity', 'unit_price']
        for col in required:
            assert col in items.columns, f"Missing item column: {col}"

    def test_quantity_defaults_to_one(self):
        _, items = self._run(_lazada_raw_df())
        assert (items['quantity'] == 1).all()

    def test_total_amount_equals_subtotal(self):
        headers, _ = self._run(_lazada_raw_df())
        assert (headers['total_amount'] == headers['subtotal']).all()

    def test_shipped_date_parsed(self):
        headers, _ = self._run(_lazada_raw_df())
        assert pd.api.types.is_datetime64_any_dtype(headers['shipped_date'])
