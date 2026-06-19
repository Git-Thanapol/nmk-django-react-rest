# file: backend/management/commands/import_mapping.py

import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
# อย่าลืมเปลี่ยน your_app_name เป็นชื่อ App จริงๆ ของคุณ
from api.models import Product, ProductAlias 

class Command(BaseCommand):
    help = 'Import product mapping from product_mapping.csv'

    def handle(self, *args, **options):
        # 1. ระบุตำแหน่งไฟล์
        file_path = os.path.join(settings.BASE_DIR, 'static', 'product_mapping.csv')

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"ไม่พบไฟล์: {file_path}"))
            return

        self.stdout.write(f"กำลังเริ่มนำเข้า Mapping จาก: {file_path} ...")

        try:
            # 2. อ่านไฟล์ CSV
            df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)
            
            req_cols = ['external_key', 'platform', 'product_sku']
            if not all(col in df.columns for col in req_cols):
                self.stdout.write(self.style.ERROR(f"CSV ต้องมีคอลัมน์ {req_cols}"))
                return

            success, skipped = 0, 0
            
            for index, row in df.iterrows():
                ext_key = str(row['external_key']).strip()
                p_sku = str(row['product_sku']).strip()
                platform = str(row['platform']).strip().upper()

                if not ext_key or not p_sku: 
                    continue

                try:
                    # ค้นหา Product หลักจาก SKU
                    product_obj = Product.objects.get(sku=p_sku)
                    
                    # สร้างหรืออัปเดต Alias
                    ProductAlias.objects.update_or_create(
                        external_key=ext_key,
                        defaults={
                            'product': product_obj, 
                            'platform': platform
                        }
                    )
                    success += 1
                except Product.DoesNotExist:
                    skipped += 1
                    # แสดง Warning ใน Log เฉพาะ SKU ที่ไม่เจอ (จะได้รู้ว่าตัวไหนหายไป)
                    self.stdout.write(self.style.WARNING(f"Row {index+2}: Product SKU '{p_sku}' not found. Skipped."))

                # แสดงสถานะทุกๆ 100 รายการ
                if (index + 1) % 100 == 0:
                    self.stdout.write(f"Processed {index + 1} rows...")

            self.stdout.write(self.style.SUCCESS(f"เสร็จสิ้น! นำเข้าสำเร็จ {success} รายการ (ข้าม {skipped} รายการ)"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"เกิดข้อผิดพลาด: {str(e)}"))