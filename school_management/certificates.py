# your_app/certificates.py
import io
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from django.utils import timezone

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    ARABIC_SUPPORT = False

def format_arabic_text(text):
    """Format Arabic text with proper shaping and direction"""
    if not ARABIC_SUPPORT:
        return text

    try:
        reshaped_text = arabic_reshaper.reshape(text)
        return get_display(reshaped_text)
    except Exception as e:
        print(f"Arabic text formatting error: {e}")
        return text

def generate_algerian_certificate_pdf(certificates):
    """Generate PDF certificates in Algerian official format"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)

    for certificate in certificates:
        _generate_single_certificate(p, certificate)
        p.showPage()

    p.save()
    buffer.seek(0)
    return buffer

def _generate_single_certificate(p, certificate):
    """Generate a single Algerian-style certificate"""
    width, height = A4

    # Header - Algerian Republic
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width/2, height-50, format_arabic_text("الجمهورية الجزائرية الديمقراطية الشعبية"))

    # Academic Year
    p.setFont("Helvetica", 12)
    p.drawCentredString(width/2, height-80, format_arabic_text(f"السنة الدراسية {certificate.academic_year}"))

    # Directorate
    p.drawCentredString(width/2, height-100, format_arabic_text("مديرية النشاط الاجتماعي والتضامن"))

    # Separator line
    p.line(50, height-120, width-50, height-120)

    # Institution Info
    p.drawCentredString(width/2, height-150, format_arabic_text(f"مؤسسة {certificate.institution_name} المعتمدة من طرف الدولة تحت رقم ترخيص {certificate.license_number}"))

    # Certification Statement
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(width/2, height-190, format_arabic_text(f"تشهد {certificate.director_name} أن التلميذ"))

    # Student Information
    p.setFont("Helvetica", 12)
    p.drawString(100, height-230, format_arabic_text(f"اللقب: {certificate.student.last_name}"))
    p.drawString(100, height-250, format_arabic_text(f"الاسم: {certificate.student.first_name}"))

    # Use student's birth data
    birth_date = getattr(certificate.student, 'date_of_birth', 'جانفي 1921')
    birth_place = getattr(certificate.student, 'place_of_birth', 'بومرداس')
    p.drawString(100, height-270, format_arabic_text(f"المولود في: {birth_date} ب: {birth_place}"))

    # Study Information
    p.drawCentredString(width/2, height-310, format_arabic_text("تابع دراسته خلال:"))
    p.drawString(100, height-340, format_arabic_text(f"السنة الدراسية: {certificate.academic_year}"))
    p.drawString(100, height-360, format_arabic_text(f"المستوى: {certificate.level}"))
    p.drawString(100, height-380, format_arabic_text(f"رقم التسجيل: {certificate.registration_number}"))

    # Issue Details
    p.drawCentredString(width/2, height-430, format_arabic_text(f"حرر ب{certificate.issue_city} في {certificate.issue_date.strftime('%d %B %Y')}"))

    # Director Signature
    p.drawCentredString(width/2, height-480, format_arabic_text(certificate.director_name))

    # Transliteration
    p.drawCentredString(width/2, height-530, format_arabic_text("الكتابة السابقة لاسم واللقب بالحروف اللاتينية"))
    latin_name = getattr(certificate.student, 'latin_name', f"{certificate.student.last_name.upper()} {certificate.student.first_name.upper()}")
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(width/2, height-550, latin_name)

def generate_certificate_for_admin(queryset):
    """Generate certificates for admin action"""
    buffer = generate_algerian_certificate_pdf(queryset)

    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="student_certificates.pdf"'
    return response