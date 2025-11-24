import import_spreadsheet as spreadsheet_importer

# Example usage:
if __name__ == "__main__":
    # Import all columns, but validate that 'Order ID' exists
    importer = spreadsheet_importer.DataImporter(
        file_path="./samples/ทั้งหมด_คำสั่งซื้อ_2025_11_18_22_23_1.csv",
        validate_columns=['Order ID']
    )
    
    # Import specific columns
    # importer2 = spreadsheet_importer.DataImporter(
    #     file_path="./samples/SP NK ORDER 31-10.xlsx",
    #     columns=['หมายเลขคำสั่งซื้อ','สถานะการสั่งซื้อ','Hot Listing'],
    #     validate_columns=['ค่าจัดส่งที่ Shopee ออกให้โดยประมาณ']
    # )

    
    data = importer.get_data()
    success_order= data[ data['Order Status'] == 'เสร็จสมบูรณ์']
    summary = importer.get_summary()
    print(success_order)
    print(f"Imported {summary['rows']} rows with {summary['columns']} columns")