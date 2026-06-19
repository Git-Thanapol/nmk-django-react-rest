from .models import ProductAlias

# def resolve_product(platform_name, row_data):
#     """
#     Returns: (Product, Search_Key)
#     """
#     search_key = ""
    
#     if platform_name == 'TikTok Shop':
#         search_key = str(row_data.get('sku', '')).strip() # mapped from 'Seller SKU'
#     elif platform_name == 'Shopee':
#         # Shopee logic: Use Name if SKU is empty
#         search_key = str(row_data.get('item_name', '')).strip()
        
#     if not search_key: return None, "UNKNOWN"

#     try:
#         alias = ProductAlias.objects.get(external_key=search_key)
#         return alias.product, search_key
#     except ProductAlias.DoesNotExist:
#         return None, search_key

def resolve_product(platform_name, row_data):
    """
    Analyzes row data to find a matching internal Product.
    Returns: (Product Object or None, Search_Key String)
    """
    search_key = ""
    
    # 1. Determine the Key based on Platform Logic
    if platform_name == 'TikTok Shop':
        # TikTok uses 'Seller SKU'
        search_key = str(row_data.get('sku', '')).strip() 
        
    elif platform_name == 'Shopee':
        # Shopee often uses Item Name if SKU is missing/messy
        search_key = str(row_data.get('item_name', '')).strip()
    
    elif platform_name == 'Lazada':
        search_key = str(row_data.get('sku', '')).strip()

    # Fallback: If no specific key found, try item name
    if not search_key: 
        search_key = str(row_data.get('item_name', '')).strip()

    if not search_key: 
        return None, "UNKNOWN"

    # 2. Look up the Alias in DB
    try:
        # We search by external_key (Exact Match)
        alias = ProductAlias.objects.get(external_key=search_key)
        return alias.product, search_key
    except ProductAlias.DoesNotExist:
        # Return None so the Import Logic knows to save it as 'Unmapped'
        return None, search_key