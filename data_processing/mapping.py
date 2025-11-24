import backend.api.models as models
from backend.api.services import import_product_mappings, resolve_product

if __name__ == "__main__":
    # Example Data (Converted from your JS)
    data_map = {
        "Adapter 20W กล่อง ขากลม": ["Adapter 20W  (ขากลม) ", "Adapter 20W  (ขากลม) , "],
        "AirTag 2 Pack ไม่มีกล่อง 2 ชิ้น": ["แยกขาย AirTag 1 Pack จ.น. 1"],
        "AirTag 4 Pack กล่อง 4ชิ้น": ["Apple Airtag Airtag 4Pack"],
        "AirPods 4 Active Noise Cancellation": ["Airpods 4/07 (ANC) ACT , 09/08/68", "Airpods 4/1 Noise , Cancellation "]
    }

    # 1. Import the mappings
    # Ensure the Master Products (Keys) exist in your Product table first!
    import_product_mappings(data_map)

    # 2. Simulate an order coming from Shopee
    incoming_order_item = "Airpods 4/07 (ANC) ACT , 09/08/68"
    real_product = resolve_product(incoming_order_item)

    if real_product:
        print(f"Sold SKU: {real_product.sku}")
        # Now you can deduct stock safely
    else:
        print("Alert: Unknown product mapping. Please update database.")