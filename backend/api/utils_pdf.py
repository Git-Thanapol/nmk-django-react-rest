import os
from django.conf import settings
from django.contrib.staticfiles import finders

from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from weasyprint import HTML, CSS
from django.conf import settings
import os
from pybaht import bahttext

def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those resources
    """
    result = finders.find(uri)
    if result:
        if not isinstance(result, (list, tuple)):
            result = [result]
        result = list(os.path.realpath(path) for path in result)
        path = result[0]
    else:
        sUrl = settings.STATIC_URL        # Typically /static/
        sRoot = settings.STATIC_ROOT      # Typically /home/userX/project_static/
        mUrl = settings.MEDIA_URL         # Typically /media/
        mRoot = settings.MEDIA_ROOT       # Typically /home/userX/project_media/

        if uri.startswith(mUrl):
            path = os.path.join(mRoot, uri.replace(mUrl, ""))
        elif uri.startswith(sUrl):
            path = os.path.join(sRoot, uri.replace(sUrl, ""))
        else:
            return uri

    # Make sure that file exists
    if not os.path.isfile(path):
        raise Exception(f'media URI must start with {sUrl} or {mUrl}')
    return path


def generate_wht_pdf(cert_object):
    """
    Generates 50 Tawi PDF for a given Certificate Object
    """
    context = {
        'cert': cert_object,
        'company': cert_object.company,
        'vendor': cert_object.vendor,
        # Helper to render the small checkbox 'X' in the form
        'is_3_percent': cert_object.tax_rate == 3, 
    }
    
    # 1. Render HTML
    html_string = render_to_string('pdf/50tawi_template.html', context)
    
    # 2. Define Font Configuration (Crucial for Thai)
    font_config = CSS(string='''
        @font-face {
            font-family: 'Sarabun';
            src: url('file://''' + os.path.join(settings.STATIC_ROOT, 'fonts/Sarabun-Regular.ttf') + ''');
        }
        body { font-family: 'Sarabun', sans-serif; }
    ''')

    # 3. Generate PDF
    html = HTML(string=html_string, base_url=settings.BASE_DIR)
    pdf_file = html.write_pdf(stylesheets=[font_config])
    
    # 4. Save to Model
    filename = f"50Tawi_{cert_object.cert_number.replace('/', '-')}.pdf"
    cert_object.pdf_file.save(filename, ContentFile(pdf_file), save=True)
    
    return cert_object.pdf_file.url


def generate_wht_pdf_4_copies(cert_object):
    """สร้าง PDF 50 ทวิ จำนวน 4 ฉบับในไฟล์เดียว"""
    
    # ข้อความระบุท้ายแต่ละฉบับ
    copy_labels = [
        "(ฉบับที่ 1) สำหรับผู้ถูกหักภาษี ณ ที่จ่าย ใช้แนบพร้อมกับแบบแสดงรายการภาษี",
        "(ฉบับที่ 2) สำหรับผู้ถูกหักภาษี ณ ที่จ่าย เก็บไว้เป็นหลักฐาน",
        "(ฉบับที่ 3) สำหรับผู้หักภาษี ณ ที่จ่าย ใช้แนบพร้อมกับแบบแสดงรายการภาษี",
        "(ฉบับที่ 4) สำหรับผู้หักภาษี ณ ที่จ่าย เก็บไว้เป็นหลักฐาน"
    ]

    context = {
        'cert': cert_object,
        'company': cert_object.company,
        'vendor': cert_object.vendor,
        'copy_labels': copy_labels, # ส่ง list ไปให้ Loop ใน Template
        'baht_text': cert_object.total_text_thai, # ยอดเงินเป็นตัวหนังสือ
    }
    
    html_string = render_to_string('pdf/50tawi_4copies_template.html', context)
    
    font_regular = os.path.join(settings.STATIC_ROOT, 'fonts/Sarabun-Regular.ttf')
    font_bold = os.path.join(settings.STATIC_ROOT, 'fonts/SarabunNew-Bold.ttf')
                             
    # Font Config (Sarabun)
    font_config = CSS(string=f'''
        @font-face {{
            font-family: 'TH Sarabun New';
            font-style: normal;
            font-weight: normal;
            src: url('file://{font_regular}');
        }}
        @font-face {{
            font-family: 'TH Sarabun New';
            font-style: normal;
            font-weight: bold;
            src: url('file://{font_bold}');
        }}
        /* Apply to body */
        body {{
            font-family: 'TH Sarabun New', sans-serif;
        }}
    ''')

    html = HTML(string=html_string, base_url=settings.BASE_DIR)
    pdf_file = html.write_pdf(stylesheets=[font_config])
    
    filename = f"50Tawi_{cert_object.cert_number.replace('/', '-')}.pdf"
    cert_object.pdf_file.save(filename, ContentFile(pdf_file), save=True)
    
    return cert_object.pdf_file.url