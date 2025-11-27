import pandas as pd
import os

def process_tiktok_orders(file_path):
    """
    Reads a TikTok Shop export (CSV/Excel), groups by Order ID, 
    and returns a Bill Header dataset similar to Power Query.
    """
    
    # 1. Load the Data (Handling CSV or Excel automatically)
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == '.csv':
        # Encoding 'utf-8-sig' handles BOM (common in exports) better than 'utf-8'
        df = pd.read_csv(file_path, encoding='utf-8-sig', dtype={'Phone #': str, 'Zipcode': str})
    elif ext in ['.xls', '.xlsx']:
        df = pd.read_excel(file_path, dtype={'Phone #': str, 'Zipcode': str})
    else:
        raise ValueError("Unsupported file format. Please use CSV or Excel.")

    # 2. Data Cleaning (Handling Missing Values for Text fields)
    # Essential for address concatenation, otherwise 'NaN' will break the string
    text_cols = ['Detail Address', 'Additional address information', 'District', 'Province', 'Country']
    df[text_cols] = df[text_cols].fillna('')

    # 3. Custom Column: Address
    # Logic: Concatenate address parts
    df['Address'] = (
        df['Detail Address'] + " " + 
        df['Additional address information'] + " " + 
        df['District'] + " " + 
        df['Province'] + " " + 
        df['Country'] + " " + 
        df['Zipcode']
    ).str.strip() # Remove double spaces if "Additional info" was empty

    # 4. Grouping & Aggregation (The "Bill Header" Logic)
    # In M, you used Table.Group. In Pandas, we use groupby().agg()
    # This pattern is often called "Split-Apply-Combine"
    bill_header = df.groupby('Order ID').agg({
        'Order Status': 'first',
        'SKU Subtotal Before Discount': 'sum',  # We sum the SKU prices to get Order Subtotal
        'Order Amount': 'first',                # Taking the first because it's usually total per order
        'Recipient': 'first',
        'Phone #': 'first',
        'Address': 'first',
        'Warehouse Name': 'first',
        'Tracking ID': 'first',
        'Shipped Time': 'first'
    }).reset_index()

    # 5. Rename Columns to match your System Requirements
    bill_header = bill_header.rename(columns={
        'SKU Subtotal Before Discount': 'Subtotal Before Discount',
        'Order Amount': 'Total Order Amount',
        'Phone #': 'Phone',
        'Shipped Time': 'Shipped Date'
    })

    # 6. Custom Column: Total Discount
    # Logic: Subtotal - Total Order Amount
    bill_header['Total Discount'] = (
        bill_header['Subtotal Before Discount'] - bill_header['Total Order Amount']
    )

    # 7. Type Conversion: Date (Locale en-GB)
    # dayfirst=True mimics the "en-GB" behavior (DD/MM/YYYY)
    bill_header['Shipped Date'] = pd.to_datetime(
        bill_header['Shipped Date'], 
        dayfirst=True, 
        errors='coerce' # If date is invalid, it becomes NaT (Not a Time)
    )

    return bill_header

# --- Usage Example ---
if __name__ == "__main__":
    # Simulate a file path
    sample_file = "samples\ทั้งหมด_คำสั่งซื้อ_2025_11_18_22_23_1.csv" 
    
    try:
        # Run the processor
        result_df = process_tiktok_orders(sample_file)
        
        # Preview the data
        print(result_df.head())
        
        # If you need to send this to your Django DB or API, convert to dict:
        data_for_system = result_df.to_dict(orient='records')
        print(f"\nReady to import {len(data_for_system)} orders.")
        
    except Exception as e:
        print(f"Error processing file: {e}")