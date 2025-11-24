# services.py
from .models import Product, ProductMapping

def import_product_mappings(mapping_data):
    """
    mapping_data structure:
    {
        "Master Product Name (In Database)": ["Messy Name 1", "Messy Name 2"]
    }
    """
    results = {"success": 0, "failed": []}

    for master_name, aliases in mapping_data.items():
        # 1. Find the internal product by name (or you could use SKU)
        try:
            # Note: This assumes 'name' is unique enough. 
            # In production, mapping by SKU is safer if available.
            internal_product = Product.objects.get(name=master_name)
        except Product.DoesNotExist:
            results["failed"].append(f"Master product not found: {master_name}")
            continue
        except Product.MultipleObjectsReturned:
            results["failed"].append(f"Multiple products found for: {master_name}")
            continue

        # 2. Create mappings for each alias
        for alias in aliases:
            # Clean the string (strip whitespace)
            clean_alias = alias.strip()
            
            ProductMapping.objects.get_or_create(
                product=internal_product,
                platform_name=clean_alias,
                # You might want to pass the specific platform here if known
                defaults={'platform': 'OTHER'} 
            )
            results["success"] += 1
            
    return results

def resolve_product(incoming_name, platform_source='OTHER'):
    """
    Takes a name from an order file and finds the real Product object.
    """
    clean_name = incoming_name.strip()
    
    # 1. Try Exact Match on Mapping Table
    mapping = ProductMapping.objects.filter(
        platform_name=clean_name
    ).first()
    
    if mapping:
        return mapping.product
        
    # 2. Fallback: Try matching the internal name directly
    # (Sometimes they use the correct name)
    try:
        return Product.objects.get(name=clean_name)
    except Product.DoesNotExist:
        return None