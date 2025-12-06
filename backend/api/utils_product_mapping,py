from .models import ProductAlias

def resolve_product(platform_name, row_data):
    """
    Returns: (Product, Search_Key)
    """
    search_key = ""
    
    if platform_name == 'TikTok Shop':
        search_key = str(row_data.get('sku', '')).strip() # mapped from 'Seller SKU'
    elif platform_name == 'Shopee':
        # Shopee logic: Use Name if SKU is empty
        search_key = str(row_data.get('item_name', '')).strip()
        
    if not search_key: return None, "UNKNOWN"

    try:
        alias = ProductAlias.objects.get(external_key=search_key)
        return alias.product, search_key
    except ProductAlias.DoesNotExist:
        return None, search_key