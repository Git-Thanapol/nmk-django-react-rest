import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from import_tiktok import process_tiktok_orders

# ==========================================
# CONFIGURATION: MANUAL MAPPING
# ==========================================
# Key   = ORIGINAL DataFrame Column Name (From process_tiktok_orders)
# Value = NEW Database Column Name (Your SQL Table)
COLUMN_MAPPING = {
    'Order ID': 'platform_order_id',         # Fix: Match exact string from previous step
    'Order Status': 'status',
    'Subtotal Before Discount': 'subtotal',
    'Total Order Amount': 'total_amount',
    'Tracking ID': 'platform_tracking_number',
    'Total Discount': 'discount_amount'
}

def apply_manual_mapping(df):
    # 1. Rename columns
    df = df.rename(columns=COLUMN_MAPPING)
    
    # 2. Filter: Keep only the columns we actually mapped
    mapped_cols = list(COLUMN_MAPPING.values())
    final_cols = [c for c in mapped_cols if c in df.columns]
    
    return df[final_cols]

def upsert_method(table, conn, keys, data_iter):
    insert_stmt = insert(table.table).values(list(data_iter))
    
    # FIX: index_elements must match your DATABASE Primary Key
    on_conflict_stmt = insert_stmt.on_conflict_do_update(
        index_elements=['platform_order_id'], # <--- CHANGED FROM 'order_id'
        set_={c.name: insert_stmt.excluded[c.name] for c in insert_stmt.excluded if c.name != 'platform_order_id'}
    )
    conn.execute(on_conflict_stmt)

def import_orders_to_db(df, db_connection_str):
    print("--- Starting Import ---")
    
    df_clean = apply_manual_mapping(df)
    
    if df_clean.empty:
        print("Error: DataFrame empty. Check if COLUMN_MAPPING keys match your CSV headers exactly.")
        print(f"Available CSV headers: {list(df.columns)}")
        return

    engine = create_engine(db_connection_str)
    
    try:
        df_clean.to_sql(
            name='test_import',
            con=engine,
            if_exists='append',
            index=False,
            method=upsert_method,
            chunksize=1000
        )
        print(f"Success! Processed {len(df_clean)} records.")
        
    except Exception as e:
        print(f"Database Error: {e}")

if __name__ == "__main__":
    DB_USER = "nmktester"
    DB_PASSWORD = "nmktester"
    
    # FIX: Added 'f' at the start for f-string formatting
    DB_CONN = f"postgresql://{DB_USER}:{DB_PASSWORD}@localhost:5432/NMK_DB"

    # Load Data
    print("Processing File...")
    # Make sure you handle the path correctly (use raw string r"..." for Windows paths)
    data = process_tiktok_orders("samples\ทั้งหมด_คำสั่งซื้อ_2025_11_18_22_23_1.csv")
    
    # Ensure data is a DataFrame
    df_test = pd.DataFrame(data)

    import_orders_to_db(df_test, DB_CONN)