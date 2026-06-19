# file: your_app/management/commands/import_products.py

import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import Product  # <-- แก้ชื่อ App ให้ถูกต้อง

class Command(BaseCommand):
    help = 'Import products from master_products.csv in static folder'

    def handle(self, *args, **options):
        # 1. ระบุตำแหน่งไฟล์
        file_path = os.path.join(settings.BASE_DIR, 'static', 'master_products.csv')

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"ไม่พบไฟล์: {file_path}"))
            return

        self.stdout.write(f"กำลังเริ่มนำเข้าข้อมูลจาก: {file_path} ...")

        try:
            # 2. อ่านไฟล์ CSV
            df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)

            # ตรวจสอบคอลัมน์
            if 'รหัสรุ่น' not in df.columns or 'รหัสชื่อสินค้า' not in df.columns:
                self.stdout.write(self.style.ERROR("CSV ขาดคอลัมน์ 'รหัสรุ่น' หรือ 'รหัสชื่อสินค้า'"))
                return

            count = 0
            for _, row in df.iterrows():
                sku = str(row['รหัสรุ่น']).strip()
                name = str(row['รหัสชื่อสินค้า']).strip()

                if not sku: 
                    continue
                
                # Logic จัดหมวดหมู่
                cat = 'OTHER'
                if 'IPHONE' in name.upper() or 'SAMSUNG' in name.upper(): 
                    cat = 'SMARTPHONE'
                elif 'IPAD' in name.upper(): 
                    cat = 'TABLET'

                # บันทึกลงฐานข้อมูล
                Product.objects.update_or_create(
                    sku=sku,
                    defaults={
                        'name': name,
                        'category': cat,
                        'is_active': True,
                        # 'company': None # ใส่ Company ถ้าจำเป็น
                    }
                )
                count += 1
                
                # แสดงผลทุกๆ 100 รายการ เพื่อให้รู้ว่าทำงานอยู่ (ดูใน Log)
                if count % 100 == 0:
                    self.stdout.write(f"Processed {count} items...")

            self.stdout.write(self.style.SUCCESS(f"เสร็จสิ้น! นำเข้าข้อมูลทั้งหมด {count} รายการ"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"เกิดข้อผิดพลาด: {str(e)}"))