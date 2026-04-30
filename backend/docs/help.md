# คู่มือการใช้งาน Namkang Phone System

ระบบ ERP สำหรับจัดการธุรกิจมือถือ รองรับหลายบริษัท เชื่อมต่อ Shopee/Lazada/TikTok

---

## ภาพรวมระบบ (anchor: sec-overview)

ระบบจัดการครบวงจร: ซื้อสินค้าเข้า → ขายออก → รายงานภาษี → ดูกำไร  
รองรับ Platform ออนไลน์ (Shopee, Lazada, TikTok) และมีระบบภาษีไทย (VAT, 50 ทวิ)

---

## Dashboard (anchor: sec-dashboard)

หน้าแรกหลัง login แสดงภาพรวมธุรกิจแบบ Real-time  
กรองดูข้อมูลตามบริษัทได้จาก dropdown

**สิ่งที่แสดง:**
- KPI Summary: ยอดซื้อรวม, ยอดขายรวม, กำไร, ภาษี ของช่วงเวลาที่เลือก
- Sales Trend: กราฟแนวโน้มยอดขายย้อนหลัง
- Top Products: สินค้าขายดีอันดับต้น
- Purchase vs Sales: เปรียบเทียบซื้อ vs ขาย รายเดือน
- Stock Alerts: สินค้าที่ stock ต่ำกว่า threshold

---

## ใบสั่งซื้อ - Purchase Order (anchor: sec-purchase)

URL: /purchases/  
ใช้บันทึกการซื้อสินค้าจากซัพพลายเออร์ stock เพิ่มเมื่อสถานะ Paid

**วิธีสร้าง:**
1. ไปที่เมนู "รายการซื้อเข้า"
2. กรอก PO Number (ต้องไม่ซ้ำกันในบริษัทเดียวกัน)
3. เลือก Vendor และ Company
4. ใส่วันที่และประเภทการซื้อ
5. เพิ่มรายการสินค้า (product, จำนวน, ราคา/หน่วย)
6. บันทึก

**สถานะ:**
- Draft: ร่าง ยังไม่จ่ายเงิน stock ยังไม่เข้า
- Paid: จ่ายเงินแล้ว stock เข้าระบบ แก้ไขรายการสินค้าไม่ได้
- Cancelled: ยกเลิก stock ไม่นับ

**ข้อควรระวัง:** stock เพิ่มก็ต่อเมื่อสถานะเป็น Paid เท่านั้น ถ้ายัง Draft อยู่ stock ยังไม่เข้า

### Field Definitions — PurchaseOrder

| Field | ความหมาย |
|-------|-----------|
| po_number | เลขที่เอกสารใบสั่งซื้อ ต้องไม่ซ้ำกันในบริษัทเดียวกัน |
| vendor | ผู้จำหน่าย/ซัพพลายเออร์ที่ซื้อสินค้ามาจาก |
| company | บริษัทที่ออกใบสั่งซื้อนี้ |
| purchase_type | ประเภทการซื้อ |
| order_date | วันที่บนใบสั่งซื้อ |
| status | DRAFT/PAID/CANCELLED |
| subtotal | ยอดรวมก่อนหักส่วนลดและก่อนภาษี |
| discount_amount | จำนวนส่วนลด |
| tax_include | True = ราคาในใบรวม VAT แล้ว, False = ราคาไม่รวม VAT |
| tax_percent | อัตราภาษี % (ปกติ 7) |
| tax_amount | จำนวนเงินภาษีที่คำนวณได้ |
| total_amount | ยอดรวมสุทธิหลังภาษีและส่วนลด |
| tax_sender_date | วันที่บนใบกำกับภาษีที่ vendor ออกให้ ใช้ในรายงานภาษีซื้อ |
| tax_sequence_number | เลขที่ลำดับบนใบภาษีของ vendor ใช้ในรายงานภาษีซื้อ |
| expected_delivery_date | วันที่คาดว่าของจะถึง |
| created_by | ผู้บันทึกรายการ |

### Field Definitions — PurchaseItem (รายการในใบสั่งซื้อ)

| Field | ความหมาย |
|-------|-----------|
| product | สินค้าที่ซื้อ |
| quantity | จำนวนที่ซื้อ |
| unit_cost | ราคาต้นทุน/หน่วย ณ เวลาที่ซื้อ |
| total_price | quantity × unit_cost |
| remaining_quantity | จำนวนที่เหลืออยู่ใน lot นี้ (ยังไม่ถูกขายออก) |

---

## ใบกำกับ / ใบขาย — Invoice (anchor: sec-invoice)

URL: /invoices/  
ใช้บันทึกการขายสินค้า ระบบตัด stock แบบ FIFO อัตโนมัติ คำนวณกำไรให้

**วิธีสร้าง:**
1. ไปที่เมนู "ใบกำกับ/ใบขาย"
2. กรอกเลขที่ใบกำกับ วันที่ เลือกบริษัท
3. ใส่ข้อมูลลูกค้า (ชื่อ เบอร์ ที่อยู่)
4. ถ้าขายผ่าน Platform ใส่ Platform Name, Order ID, Tracking Number
5. เพิ่มสินค้า — ระบบดึง Batch แบบ FIFO ให้อัตโนมัติ หรือเลือก Batch เองได้
6. บันทึก

**สถานะ:**
- Draft: ร่าง ยังไม่ตัด stock
- Billed: ขายแล้ว stock ออก ใช้ในรายงานภาษีขาย
- Cancelled: ยกเลิก stock คืนกลับ

**FIFO:** ระบบเลือก lot ที่ซื้อมาก่อนขายก่อน เพื่อให้ต้นทุนถูกต้อง

**Export:** ปุ่ม Print PDF (เปลี่ยนสถานะเป็น Billed อัตโนมัติ) และ Export Excel

**Sync Google Sheet:** ดึงข้อมูลขอใบกำกับจาก Google Form เข้าระบบ

### Field Definitions — Invoice

| Field | ความหมาย |
|-------|-----------|
| invoice_number | เลขที่ใบกำกับภาษี |
| vendor | ลูกค้า/คู่ค้าที่ออกใบให้ |
| company | บริษัทที่ออกใบกำกับ |
| invoice_date | วันที่บนใบกำกับ |
| status | DRAFT/BILLED/CANCELLED |
| platform_name | ชื่อ Platform ที่ขายผ่าน เช่น Shopee, Lazada, TikTok |
| platform_order_id | หมายเลข Order บน Platform |
| platform_tracking_number | เลข Tracking การขนส่ง |
| recipient_name | ชื่อผู้รับสินค้า |
| recipient_phone | เบอร์โทรผู้รับ |
| recipient_address | ที่อยู่จัดส่ง |
| tax_invoice_requested | True = ลูกค้าขอใบกำกับภาษีอย่างเป็นทางการ |
| is_printed | True = เคยพิมพ์ PDF แล้ว |
| print_datetime | วันเวลาที่พิมพ์ล่าสุด |
| subtotal | ยอดรวมก่อนส่วนลดและภาษี |
| discount_amount | ส่วนลด |
| shipping_cost | ค่าขนส่ง |
| tax_include | True = ราคาในใบรวม VAT แล้ว |
| tax_percent | อัตราภาษี % |
| tax_amount | จำนวนเงินภาษี |
| grand_total | ยอดรวมสุทธิทั้งหมด |

### Field Definitions — InvoiceItem (รายการในใบขาย)

| Field | ความหมาย |
|-------|-----------|
| product | สินค้าที่ขาย (อาจว่างถ้า import จาก platform แล้ว unmatched) |
| purchase_item | Batch/Lot ที่ดึงมาขาย ใช้ติดตาม FIFO และต้นทุน |
| sku | รหัสสินค้า ณ เวลาที่บันทึก |
| item_name | ชื่อสินค้า ณ เวลาที่บันทึก |
| quantity | จำนวนที่ขาย |
| unit_price | ราคาขาย/หน่วย |
| total_price | quantity × unit_price |
| unit_cost | ราคาทุน/หน่วย (ดึงจาก purchase_item ที่เลือก) |
| profit | กำไรรวม = total_price − (unit_cost × quantity) |

---

## สินค้า — Products (anchor: sec-product)

URL: /products/  
Master catalog สินค้าทั้งหมด แต่ละรายการมี SKU ที่ unique

**ข้อควรรู้:** stock คำนวณจาก (สินค้าที่ซื้อ Paid ทั้งหมด) − (สินค้าที่ขาย Billed ทั้งหมด)  
สินค้า Inactive จะไม่ขึ้นใน dropdown ตอนสร้าง Invoice/PO

### Field Definitions — Product

| Field | ความหมาย |
|-------|-----------|
| sku | รหัสสินค้า (unique ทั้งระบบ) |
| name | ชื่อสินค้า |
| description | คำอธิบายเพิ่มเติม |
| category | หมวดหมู่สินค้า |
| cost_price | ราคาทุนอ้างอิง (ราคาจริงติดตามใน PurchaseItem) |
| selling_price | ราคาขายตั้งต้น |
| is_active | True = ใช้งานอยู่ False = ปิดใช้งาน |
| current_stock | stock คงเหลือ (computed: ซื้อ Paid − ขาย Billed) |
| company | บริษัทที่สินค้านี้สังกัด (optional) |

---

## ผู้จำหน่าย — Vendors (anchor: sec-vendor)

URL: /vendors/  
ฐานข้อมูลซัพพลายเออร์ที่ซื้อสินค้ามาจาก

### Field Definitions — Vendor

| Field | ความหมาย |
|-------|-----------|
| name | ชื่อบริษัท/ร้านค้าของ vendor |
| contact_person | ชื่อผู้ติดต่อ |
| phone | เบอร์โทร |
| email | อีเมล |
| address | ที่อยู่ |
| tax_id | เลขประจำตัวผู้เสียภาษี 13 หลัก ใช้ในเอกสาร 50 ทวิ |
| company | บริษัทที่ vendor นี้ supply ให้ |
| is_active | True = ใช้งานอยู่ |

---

## รายรับ / รายจ่าย — Transactions (anchor: sec-transaction)

URL: /transactions/  
บันทึกรายรับ-รายจ่ายที่ไม่ใช่การซื้อ-ขายสินค้า เช่น ค่าเช่า ค่าขนส่ง เงินเดือน

**ประเภท:** INCOME (รายรับ) / EXPENSE (รายจ่าย)

**หมวดหมู่:** REPAIR_SERVICE, DELIVERY, SALARY, RENT, UTILITY, MARKETING, OTHER

### Field Definitions — Transaction

| Field | ความหมาย |
|-------|-----------|
| transaction_number | เลขที่เอกสารรายรับ/รายจ่าย |
| transaction_date | วันที่บันทึก |
| type | INCOME = รายรับ, EXPENSE = รายจ่าย |
| category | หมวดหมู่ค่าใช้จ่าย |
| amount | จำนวนเงิน (บวกเสมอ ไม่ว่าจะ income หรือ expense) |
| description | รายละเอียด |
| reference | เลขอ้างอิงเอกสาร |
| vendor | vendor ที่เกี่ยวข้อง (ใช้เชื่อมกับใบ 50 ทวิ) |
| company | บริษัทที่บันทึกรายการนี้ |

---

## นำเข้าข้อมูล Platform (anchor: sec-import)

URL: /import/platforms/  
Import ไฟล์ Excel/CSV จาก Shopee/Lazada/TikTok เป็น Invoice อัตโนมัติ

**วิธีใช้:**
1. เลือก Platform: Shopee / Lazada / TikTok
2. อัปโหลดไฟล์ .csv หรือ .xlsx จาก Seller Center
3. ระบบประมวลผลใน Background ไม่ต้องรอ
4. ดูสถานะที่ Import Log ด้านล่างหน้า

**สถานะ Import:** PENDING → PROCESSING → COMPLETED / COMPLETED_WITH_ERRORS / FAILED

**ถ้า Error:** ดาวน์โหลด Error File จาก Import Log ส่วนใหญ่เกิดจากสินค้าที่ยังไม่ Map SKU

### Field Definitions — ImportLog

| Field | ความหมาย |
|-------|-----------|
| platform | SHOPEE / LAZADA / TIKTOK |
| filename | ชื่อไฟล์ที่อัปโหลด |
| status | PENDING/PROCESSING/COMPLETED/COMPLETED_WITH_ERRORS/FAILED |
| total_records | จำนวน Order ทั้งหมดในไฟล์ |
| success_count | จำนวน Order ที่ import สำเร็จ |
| failed_count | จำนวน Order ที่ล้มเหลว |
| error_file | ไฟล์ Excel รายการ Order ที่มีปัญหา (ดาวน์โหลดได้) |

---

## จับคู่สินค้า — Product Mapping (anchor: sec-mapping)

URL: /product_mapping/  
ใช้บอกระบบว่าชื่อสินค้าจาก Platform ตรงกับ SKU ไหนในระบบ  
ทำครั้งเดียว ครั้งต่อไประบบจำให้ และย้อนหลังแก้ไข Invoice เก่าให้ด้วย

**เมื่อไหรต้องมา Map:** Import แล้วสถานะ COMPLETED_WITH_ERRORS หรือมีสินค้า Unmapped

### Field Definitions — ProductAlias

| Field | ความหมาย |
|-------|-----------|
| external_key | ชื่อหรือ SKU ของสินค้าจาก Platform (Shopee/Lazada/TikTok) |
| product | สินค้าในระบบที่ตรงกัน |
| platform | SHOPEE / LAZADA / TIKTOK / OTHER |

---

## รายงาน — Reports (anchor: sec-reports)

URL: /reports/  
ออกรายงานภาษีและ Stock เป็น Excel

**ประเภทรายงาน:**
- รายงานภาษีซื้อ: PO สถานะ Paid ในช่วงวันที่ที่เลือก
- รายงานภาษีขาย: Invoice สถานะ Billed ในช่วงวันที่ที่เลือก
- Stock Report: สินค้าคงเหลือทั้งหมด ณ ปัจจุบัน
- Combined: ภาษีซื้อ + ภาษีขาย ในไฟล์เดียว

**Filter:**
- Company: เลือกบริษัทหรือทุกบริษัท
- Date Range: ช่วงวันที่
- Basis: "วันที่เอกสาร" = วันที่บนใบ / "วันที่ออกภาษี" = tax_sender_date บนใบ PO

---

## VAT Tracking (anchor: sec-vat)

URL: /vat-tracking/ และ /vat-buy-summary/  
ระบบติดตาม VAT ซื้อ/ขาย แยกจาก Invoice/PO หลัก  
ระบบแยก VAT/Non-VAT จากชื่อ vendor อัตโนมัติ (suffix /kit หรือ /s16 = Non-VAT)

### Field Definitions — VatOrderBuyItem

| Field | ความหมาย |
|-------|-----------|
| serial_no | เลขลำดับรายการจาก POS |
| product_name | ชื่อสินค้า |
| unit | หน่วยนับ |
| purchase_price | ราคาซื้อ |
| vat_company | บริษัทที่เกี่ยวข้อง (user กรอก) |
| payment_method_in | วิธีชำระเงิน (user กรอก) |
| bank_in | ธนาคาร (user กรอก) |

---

## ใบรับรองหักภาษี ณ ที่จ่าย — 50 ทวิ (anchor: sec-wht)

URL: /tax/50tawi/  
ออกใบรับรองหักภาษี ณ ที่จ่าย format ไทย พิมพ์ได้ 4 สำเนา  
เลขที่ใบรับรองออกอัตโนมัติ รูปแบบ YYYY/0001

**แหล่งที่มาของข้อมูล:** ใบสั่งซื้อ (PO) / รายจ่าย (Transaction) / พิมพ์เอง

**สถานะ:** Draft → Issued (เมื่อกด Issue Certificate เลขที่จะถูกออกและล็อค)

### Field Definitions — WithholdingTaxCert

| Field | ความหมาย |
|-------|-----------|
| book_number | เลขที่สมุด (ถ้ามี) |
| cert_number | เลขที่ใบรับรอง รูปแบบ YYYY/0001 ออกอัตโนมัติ |
| date_issued | วันที่ออกใบรับรอง |
| vendor | ผู้รับเงิน/ผู้ถูกหักภาษี |
| company | บริษัทผู้จ่ายเงิน (ผู้หักภาษี) |
| purchase_order | ใบสั่งซื้อที่เป็นแหล่งที่มา (ถ้ามี) |
| transaction | รายจ่ายที่เป็นแหล่งที่มา (ถ้ามี) |
| income_type | ประเภทเงินได้: salary/fee/royalty/interest/dividend/rent/profession/contract/other |
| income_description | คำอธิบายประเภทเงินได้ |
| tax_rate | อัตราภาษีหัก ณ ที่จ่าย % |
| amount_before_tax | จำนวนเงินก่อนหักภาษี |
| tax_amount | จำนวนเงินภาษีที่หัก |
| status | DRAFT / ISSUED |

---

## จัดการบริษัท — Companies (anchor: sec-company)

URL: /companies/  
ระบบรองรับหลายบริษัท แต่ละบริษัทมีข้อมูล/เอกสารแยกกัน

### Field Definitions — Company

| Field | ความหมาย |
|-------|-----------|
| name | ชื่อบริษัทเต็ม ใช้ในเอกสารอย่างเป็นทางการ |
| nick_name | ชื่อย่อ ใช้แสดงใน dropdown |
| tax_id | เลขประจำตัวผู้เสียภาษี 13 หลัก |
| address | ที่อยู่บริษัท |
| phone | เบอร์โทร |
| email | อีเมล |
| is_active | True = ใช้งานอยู่ False = ซ่อนจาก dropdown |

---

## ค้นหาทั่วไป — Global Search (anchor: sec-search)

Search box ด้านบน (header) ค้นหาข้ามทุก module  
ค้นหาได้จาก: สินค้า (SKU, ชื่อ), ผู้จำหน่าย, ใบกำกับ, ใบสั่งซื้อ, บริษัท

---

## แจ้งปัญหา — Bug Reports (anchor: sec-bugreport)

URL: /bug-reports/  
แจ้งบัค หรือขอฟีเจอร์ใหม่ มี AI Chat ช่วย diagnose

**ประเภท:** BUG (พบปัญหา) / FEATURE (ขอฟีเจอร์)

**สถานะ:** NEW → IN_PROGRESS → RESOLVED / REJECTED

---

## FAQ — คำถามที่พบบ่อย (anchor: sec-faq)

**Q: ทำไม Stock ไม่เพิ่มหลังสร้าง PO?**  
A: Stock เพิ่มก็ต่อเมื่อ PO สถานะ Paid เท่านั้น Draft ยังไม่เข้า

**Q: Import Shopee แล้วมี Error?**  
A: ดาวน์โหลด Error File จาก Import Log แล้วไป Map สินค้าที่ /product_mapping/ ก่อน แล้วค่อย Import ใหม่ หรือรายการเก่าจะถูกแก้ไขย้อนหลังให้อัตโนมัติ

**Q: ออกรายงานภาษีซื้อยังไง?**  
A: ไป /reports/ → เลือก "รายงานภาษีซื้อ" → เลือกบริษัท ช่วงวันที่ → Generate → ดาวน์โหลด Excel

**Q: ลบสินค้าออกจากใบ Billed ได้ไหม?**  
A: ต้องเปลี่ยน Invoice กลับเป็น Cancelled ก่อน (stock คืน) แล้วแก้ไข แล้วเปลี่ยนกลับเป็น Billed

**Q: FIFO คืออะไร?**  
A: First-In-First-Out = lot ที่ซื้อมาก่อนถูกขายออกก่อน เพื่อคำนวณต้นทุนให้ถูกต้อง

**Q: เลขที่ 50 ทวิ ออกยังไง?**  
A: ออกอัตโนมัติ รูปแบบ YYYY/0001 แยกตามปี พอกด Issue Certificate

**Q: สินค้าไม่ขึ้น dropdown ตอนสร้าง Invoice?**  
A: สินค้านั้นอาจเป็น Inactive อยู่ ไปที่ /products/ กรอง Inactive แล้วเปิด Active กลับมา

**Q: Basis ในรายงานคืออะไร?**  
A: "วันที่เอกสาร" = วันที่บนใบ PO/Invoice, "วันที่ออกภาษี" = tax_sender_date บน PO ใช้เมื่อวันบนใบกับวันบนภาษีต่างกัน

**Q: tax_sender_date และ tax_sequence_number ใน PO ใช้ทำอะไร?**  
A: ใช้ในรายงานภาษีซื้อ เพราะวันที่บนใบสั่งซื้อกับวันที่บนใบกำกับภาษีที่ vendor ออกอาจต่างกัน ใส่ข้อมูลเหล่านี้เพื่อให้รายงานถูกต้องตามหลักภาษี

**Q: remaining_quantity ใน PurchaseItem คืออะไร?**  
A: จำนวนสินค้าที่เหลือใน Lot นั้นที่ยังไม่ได้ขายออก เมื่อขายสินค้าออกจาก Lot นี้ ค่านี้จะลดลง

---

## สถานะสรุป (anchor: sec-status)

**PurchaseOrder:** DRAFT → PAID → (CANCELLED)  
**Invoice:** DRAFT → BILLED → (CANCELLED)  
**WithholdingTaxCert:** DRAFT → ISSUED  
**ImportLog:** PENDING → PROCESSING → COMPLETED / COMPLETED_WITH_ERRORS / FAILED  
**BugReport:** NEW → IN_PROGRESS → RESOLVED / REJECTED
