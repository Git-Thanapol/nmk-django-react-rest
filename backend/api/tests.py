from django.test import TestCase
#from .models import Product, ProductMapping
from .utils_import_core import process_shopee_orders


# Create your tests here.
class ShopeeOrderProcessingTestCase(TestCase):
    def test_process_shopee_orders(self):
        file_path = r"C:/Users/Thana/OneDrive/เดสก์ท็อป/nmk/data_processing/samples/SP NK ORDER 31-10.xlsx"
        headers, items = process_shopee_orders(file_path)
        
        # Basic assertions to check if dataframes are not empty
        self.assertFalse(headers.empty, "Headers dataframe should not be empty")
        self.assertFalse(items.empty, "Items dataframe should not be empty")
        
        print("Headers DataFrame:")
        print(headers)
        print("\nItems DataFrame:")
        print(items)

        # Check if expected columns are present in headers
        expected_header_columns = ['Order ID', 'Order Status', 'Total Order Amount', 'Recipient', 'Phone', 'Address', 'Tracking ID', 'Shipped Date']
        for col in expected_header_columns:
            self.assertIn(col, headers.columns, f"Column '{col}' should be in headers dataframe")
        
        # Check if expected columns are present in items
        expected_item_columns = ['order_id', 'sku', 'quantity', 'unit_price', 'total_price']
        for col in expected_item_columns:
            self.assertIn(col, items.columns, f"Column '{col}' should be in items dataframe")

