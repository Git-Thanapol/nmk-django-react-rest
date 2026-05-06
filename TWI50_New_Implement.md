# TWI50 NEW Implement

Instead of build from scratch, I wanted you to use @TWI50/TWI50_OFFICIAL_TEMPLATE.xlsx as a template. and then populate to field as shown  in table below.

| Name | Description | Cell Position |
| :--- | :--- | :--- |
| Book No. | เล่มที่ | Q2 |
| Document No. | เลขที่ | Q3 |
| Payer National ID | เลขประจำตัวประชาชน (ผู้มีหน้าที่หักภาษี) | P5 |
| Payer Tax ID | เลขประจำตัวผู้เสียภาษีอากร (ผู้มีหน้าที่หักภาษี) | P6 |
| Payer Name | ชื่อ (ผู้มีหน้าที่หักภาษี) | C6 |
| Payer Address | ที่อยู่ (ผู้มีหน้าที่หักภาษี) | C8 |
| Payee National ID | เลขประจำตัวประชาชน (ผู้ถูกหักภาษี) | P11 |
| Payee Tax ID | เลขประจำตัวผู้เสียภาษีอากร (ผู้ถูกหักภาษี) | P12 |
| Payee Name | ชื่อ (ผู้ถูกหักภาษี) | C12 |
| Payee Address | ที่อยู่ (ผู้ถูกหักภาษี) | C14 |
| Sequence No. | ลำดับที่ในแบบ | D16 |
| Form Type: PND 1 Kor | (1) ภ.ง.ด. 1 ก. (Checkbox) | H16 |
| Form Type: PND 1 Kor Special | (2) ภ.ง.ด. 1 ก. พิเศษ (Checkbox) | J16 |
| Form Type: PND 2 | (3) ภ.ง.ด. 2 (Checkbox) | M16 |
| Form Type: PND 2 Kor | (4) ภ.ง.ด. 2 ก. (Checkbox) | O16 |
| Form Type: PND 3 | (5) ภ.ง.ด. 3 (Checkbox) | H18 |
| Form Type: PND 3 Kor | (6) ภ.ง.ด. 3 ก. (Checkbox) | J18 |
| Form Type: PND 53 | (7) ภ.ง.ด. 53 (Checkbox) | M18 |
| Income Type 6 Description | 6. อื่นๆ (ระบุ) รายละเอียดเงินได้ | E46 |
| Income Type 6 Date | วัน เดือน หรือปีภาษี ที่จ่าย | M46 |
| Income Type 6 Amount | จำนวนเงินที่จ่าย (ประเภทที่ 6) | O46 |
| Income Type 6 Tax Withheld | ภาษีที่หักและนำส่งไว้ (ประเภทที่ 6) | Q46 |
| Total Amount | รวมเงินที่จ่าย | O48 |
| Total Tax Withheld | รวมภาษีที่หักและนำส่งไว้ | Q48 |
| Total Tax in Words | รวมเงินภาษีที่หักนำส่ง (ตัวอักษร) | I50 |
| Provident Fund Amount | เงินสะสมจ่ายเข้ากองทุนสำรองเลี้ยงชีพ (จำนวนเงิน) | Q52 |
| Social Security Amount | เงินสมทบจ่ายเข้ากองทุนประกันสังคม (จำนวนเงิน) | J53 |
| Social Security ID | เลขที่บัตรประกันสังคม | P54 |
| Payer Status 1 | (1) หักภาษี ณ ที่จ่าย (Checkbox) | A56 |
| Payer Status 2 | (2) ออกภาษีให้ตลอดไป (Checkbox) | A57 |
| Payer Status 3 | (3) ออกภาษีให้ครั้งเดียว (Checkbox) | A58 |
| Payer Status 4 | (4) อื่นๆ (Checkbox) | A59 |
| Signature | ลงชื่อ (ผู้มีหน้าที่หักภาษี ณ ที่จ่าย) | H58 |
| Date Signed | วัน เดือน ปี ที่ออกหนังสือรับรองฯ | G59 |

# Income table detail
| ประเภทเงินได้พึงประเมินที่จ่าย | วัน  เดือน หรือปีภาษี ที่จ่าย | จำนวนเงินที่จ่าย | ภาษีที่หักและนำส่งไว้ |
| :--- | :--- | :--- | :--- |
|1. เงินเดือน ค่าจ้าง เบี้ยเลี้ยง โบนัส ฯลฯ  ตามมาตรา 40 (1) | M23 | O23 | Q23 |
|2. ค่าธรรมเนียม  ค่านายหน้า  ฯลฯ  ตามมาตรา 40 (2) | M24 | O24 | Q24 |
|3. ค่าแห่งลิขสิทธิ์  ฯลฯ  ตามมาตรา 40 (3) | M25 | O25 | Q25 |
|4. (ก) ค่าดอกเบี้ย ฯลฯ  ตามมาตรา 40 (4) (ก) | M26 | O26 | Q26 |
|(ข) เงินปันผล ส่วนแบ่งของกำไร ฯลฯ ตามมาตรา 40 (4) (ข)| M27 | O27 | Q27 |
|6. อื่นๆ(ระบุ) | M46 | O46 | Q46 |