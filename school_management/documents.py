import io
import pandas as pd
from django.http import HttpResponse
from django.shortcuts import render
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from django.utils import timezone
from .models import Student, Staff, ClassRoom, Grade, Attendance, Payment
import logging

# Set up logger
logger = logging.getLogger(__name__)

# Arabic text support
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    ARABIC_SUPPORT = False
    logger.warning("arabic-reshaper or python-bidi not installed. Arabic text may not display correctly.")

def format_arabic_text(text):
    """Format Arabic text with proper shaping and direction"""
    if not text or not ARABIC_SUPPORT:
        return str(text) if text else ""

    try:
        reshaped_text = arabic_reshaper.reshape(str(text))
        return get_display(reshaped_text)
    except Exception as e:
        logger.error(f"Arabic text formatting error: {e}")
        return str(text)

def draw_arabic_text(p, x, y, text, font_size=12, font_name="Helvetica"):
    """Draw Arabic text with proper formatting"""
    if not text:
        return

    formatted_text = format_arabic_text(text)
    p.setFont(font_name, font_size)

    # For Arabic text, we need to adjust the position since it's right-to-left
    if any('\u0600' <= char <= '\u06FF' for char in str(text)):
        text_width = p.stringWidth(formatted_text, font_name, font_size)
        p.drawString(x - text_width, y, formatted_text)
    else:
        p.drawString(x, y, formatted_text)

def draw_centered_arabic_text(p, x, y, text, font_size=12, font_name="Helvetica"):
    """Draw centered Arabic text"""
    if not text:
        return

    formatted_text = format_arabic_text(text)
    p.setFont(font_name, font_size)
    text_width = p.stringWidth(formatted_text, font_name, font_size)
    p.drawString(x - text_width/2, y, formatted_text)

def is_arabic_text(text):
    """Check if text contains Arabic characters"""
    if not text:
        return False
    return any('\u0600' <= char <= '\u06FF' for char in str(text))

def admin_document_generator(request):
    """Document generator for admin panel"""
    try:
        classes = ClassRoom.objects.all()
        students = Student.objects.filter(is_active=True)

        context = {
            'classes': classes,
            'students': students,
            'title': 'Document Generator',
        }

        return render(request, 'admin/document_generator.html', context)
    except Exception as e:
        logger.error(f"Error in admin_document_generator: {e}")
        return HttpResponse("Error loading document generator", status=500)

def admin_generate_student_list(request, class_id=None, format_type='pdf', language='en'):
    """Generate student list from admin"""
    try:
        if class_id and class_id != 'all':
            try:
                class_room = ClassRoom.objects.get(pk=class_id)
                students = Student.objects.filter(class_room=class_room, is_active=True)
                title = f"Student List - {class_room}"
            except ClassRoom.DoesNotExist:
                students = Student.objects.filter(is_active=True)
                title = "All Students"
        else:
            students = Student.objects.filter(is_active=True)
            title = "All Students"

        # Language support
        translations = {
            'en': {
                'title': 'Student List - Trust Academy',
                'name': 'Name',
                'student_id': 'Student ID',
                'grade': 'Grade',
                'parent': 'Parent',
                'phone': 'Phone',
                'date': 'Date',
                'class': 'Class',
                'status': 'Status'
            },
            'fr': {
                'title': 'Liste des Étudiants - Trust Academy',
                'name': 'Nom',
                'student_id': 'ID Étudiant',
                'grade': 'Niveau',
                'parent': 'Parent',
                'phone': 'Téléphone',
                'date': 'Date',
                'class': 'Classe',
                'status': 'Statut'
            },
            'ar': {
                'title': 'قائمة الطلاب - أكاديمية ترست',
                'name': 'الاسم',
                'student_id': 'رقم الطالب',
                'grade': 'الصف',
                'parent': 'ولي الأمر',
                'phone': 'الهاتف',
                'date': 'التاريخ',
                'class': 'الفصل',
                'status': 'الحالة'
            }
        }

        lang = translations.get(language, translations['en'])

        if format_type == 'excel':
            return admin_generate_student_excel(students, title, lang)
        else:
            return admin_generate_student_pdf(students, title, lang)
    except Exception as e:
        logger.error(f"Error generating student list: {e}")
        return HttpResponse(f"Error generating student list: {str(e)}", status=500)

def admin_generate_student_pdf(students, title, lang):
    """Generate PDF student list"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        # Header
        p.setFont("Helvetica-Bold", 16)
        draw_centered_arabic_text(p, 4.25*inch, 10.5*inch, lang['title'])
        p.setFont("Helvetica", 12)
        p.drawString(1*inch, 10*inch, f"{lang['date']}: {timezone.now().strftime('%Y-%m-%d')}")

        # Table headers
        y_position = 9.5*inch
        p.setFont("Helvetica-Bold", 10)
        p.drawString(0.5*inch, y_position, lang['student_id'])
        p.drawString(1.5*inch, y_position, lang['name'])
        p.drawString(3.5*inch, y_position, lang['grade'])
        p.drawString(4.5*inch, y_position, lang['class'])
        p.drawString(5.5*inch, y_position, lang['parent'])
        p.drawString(7*inch, y_position, lang['phone'])

        # Student data
        p.setFont("Helvetica", 9)
        y_position -= 0.3*inch

        for i, student in enumerate(students):
            if y_position < 1*inch:  # New page if needed
                p.showPage()
                y_position = 9.5*inch
                # Redraw headers on new page
                p.setFont("Helvetica-Bold", 10)
                p.drawString(0.5*inch, y_position, lang['student_id'])
                p.drawString(1.5*inch, y_position, lang['name'])
                p.drawString(3.5*inch, y_position, lang['grade'])
                p.drawString(4.5*inch, y_position, lang['class'])
                p.drawString(5.5*inch, y_position, lang['parent'])
                p.drawString(7*inch, y_position, lang['phone'])
                y_position -= 0.3*inch
                p.setFont("Helvetica", 9)

            p.drawString(0.5*inch, y_position, student.student_id)
            draw_arabic_text(p, 1.5*inch, y_position, student.get_full_name())
            draw_arabic_text(p, 3.5*inch, y_position, student.get_grade_level_display())
            draw_arabic_text(p, 4.5*inch, y_position, str(student.class_room) if student.class_room else "N/A")
            draw_arabic_text(p, 5.5*inch, y_position, student.parent_name)
            p.drawString(7*inch, y_position, student.parent_phone)
            y_position -= 0.25*inch

        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="student_list_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error generating student PDF: {e}")
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

def admin_generate_student_excel(students, title, lang):
    """Generate Excel student list"""
    try:
        data = []
        for student in students:
            data.append({
                lang['student_id']: student.student_id,
                lang['name']: student.get_full_name(),
                lang['grade']: student.get_grade_level_display(),
                lang['class']: str(student.class_room) if student.class_room else "N/A",
                lang['parent']: student.parent_name,
                lang['phone']: student.parent_phone,
                lang['status']: "Active" if student.is_active else "Inactive"
            })

        df = pd.DataFrame(data)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="student_list_{timezone.now().strftime("%Y%m%d")}.xlsx"'

        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Students')
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Students']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        return response
    except Exception as e:
        logger.error(f"Error generating student Excel: {e}")
        return HttpResponse(f"Error generating Excel: {str(e)}", status=500)

def admin_generate_staff_list(request, format_type='pdf', language='en'):
    """Generate staff list from admin"""
    try:
        staff_members = Staff.objects.filter(is_active=True)

        translations = {
            'en': {
                'title': 'Staff Directory - Trust Academy',
                'staff_id': 'Staff ID',
                'name': 'Name',
                'position': 'Position',
                'phone': 'Phone',
                'email': 'Email',
                'hire_date': 'Hire Date'
            },
            'fr': {
                'title': 'Répertoire du Personnel - Trust Academy',
                'staff_id': 'ID Personnel',
                'name': 'Nom',
                'position': 'Poste',
                'phone': 'Téléphone',
                'email': 'Email',
                'hire_date': "Date d'embauche"
            },
            'ar': {
                'title': 'دليل الموظفين - أكاديمية ترست',
                'staff_id': 'رقم الموظف',
                'name': 'الاسم',
                'position': 'المنصب',
                'phone': 'الهاتف',
                'email': 'البريد الإلكتروني',
                'hire_date': 'تاريخ التعيين'
            }
        }

        lang = translations.get(language, translations['en'])

        if format_type == 'excel':
            return admin_generate_staff_excel(staff_members, lang)
        else:
            return admin_generate_staff_pdf(staff_members, lang)
    except Exception as e:
        logger.error(f"Error generating staff list: {e}")
        return HttpResponse(f"Error generating staff list: {str(e)}", status=500)

def admin_generate_staff_pdf(staff_members, lang):
    """Generate PDF staff directory"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        p.setFont("Helvetica-Bold", 16)
        draw_centered_arabic_text(p, 4.25*inch, 10.5*inch, lang['title'])
        p.setFont("Helvetica", 12)
        p.drawString(1*inch, 10*inch, f"Generated: {timezone.now().strftime('%Y-%m-%d')}")

        # Table headers
        y_position = 9.5*inch
        p.setFont("Helvetica-Bold", 10)
        p.drawString(0.5*inch, y_position, lang['staff_id'])
        p.drawString(1.5*inch, y_position, lang['name'])
        p.drawString(3.5*inch, y_position, lang['position'])
        p.drawString(5.5*inch, y_position, lang['phone'])
        p.drawString(7*inch, y_position, lang['email'])

        # Staff data
        p.setFont("Helvetica", 9)
        y_position -= 0.3*inch

        for staff in staff_members:
            if y_position < 1*inch:
                p.showPage()
                y_position = 9.5*inch
                p.setFont("Helvetica-Bold", 10)
                p.drawString(0.5*inch, y_position, lang['staff_id'])
                p.drawString(1.5*inch, y_position, lang['name'])
                p.drawString(3.5*inch, y_position, lang['position'])
                p.drawString(5.5*inch, y_position, lang['phone'])
                p.drawString(7*inch, y_position, lang['email'])
                y_position -= 0.3*inch
                p.setFont("Helvetica", 9)

            p.drawString(0.5*inch, y_position, staff.staff_id)
            draw_arabic_text(p, 1.5*inch, y_position, staff.get_full_name())
            draw_arabic_text(p, 3.5*inch, y_position, staff.get_position_display())
            p.drawString(5.5*inch, y_position, staff.phone)
            p.drawString(7*inch, y_position, staff.user.email if staff.user else "N/A")
            y_position -= 0.25*inch

        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="staff_directory_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error generating staff PDF: {e}")
        return HttpResponse(f"Error generating staff PDF: {str(e)}", status=500)

def admin_generate_staff_excel(staff_members, lang):
    """Generate Excel staff directory"""
    try:
        data = []
        for staff in staff_members:
            data.append({
                lang['staff_id']: staff.staff_id,
                lang['name']: staff.get_full_name(),
                lang['position']: staff.get_position_display(),
                lang['phone']: staff.phone,
                lang['email']: staff.user.email if staff.user else "N/A",
                lang['hire_date']: staff.hire_date.strftime('%Y-%m-%d')
            })

        df = pd.DataFrame(data)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="staff_directory_{timezone.now().strftime("%Y%m%d")}.xlsx"'

        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Staff')
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Staff']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column_letter].width = adjusted_width

        return response
    except Exception as e:
        logger.error(f"Error generating staff Excel: {e}")
        return HttpResponse(f"Error generating staff Excel: {str(e)}", status=500)

def admin_generate_parent_invitation(request, format_type='pdf', language='en'):
    """Generate parent or staff meeting invitations"""
    try:
        invitation_type = request.GET.get('type', 'parent')  # 'parent' or 'staff'

        translations = {
            'en': {
                'parent_title': 'Parent Meeting Invitation - Trust Academy',
                'staff_title': 'Staff Meeting Invitation - Trust Academy',
                'school_name': 'Trust Academy',
                'date': 'Date',
                'time': 'Time',
                'location': 'Location',
                'agenda': 'Agenda',
                'principal': 'School Principal',
                'parent_greeting': 'Dear Parents,',
                'staff_greeting': 'Dear Staff Members,',
                'parent_message': 'We cordially invite you to attend our parent-teacher meeting.',
                'staff_message': 'We cordially invite you to attend our staff meeting.',
            },
            'fr': {
                'parent_title': 'Invitation Réunion Parents - Trust Academy',
                'staff_title': 'Invitation Réunion Staff - Trust Academy',
                'school_name': 'Trust Academy',
                'date': 'Date',
                'time': 'Heure',
                'location': 'Lieu',
                'agenda': 'Ordre du Jour',
                'principal': 'Directeur de l\'École',
                'parent_greeting': 'Chers Parents,',
                'staff_greeting': 'Chers Membres du Personnel,',
                'parent_message': 'Nous avons le plaisir de vous inviter à notre réunion parents-professeurs.',
                'staff_message': 'Nous avons le plaisir de vous inviter à notre réunion du personnel.',
            },
            'ar': {
                'parent_title': 'دعوة اجتماع أولياء الأمور - أكاديمية ترست',
                'staff_title': 'دعوة اجتماع الموظفين - أكاديمية ترست',
                'school_name': 'أكاديمية ترست',
                'date': 'التاريخ',
                'time': 'الوقت',
                'location': 'المكان',
                'agenda': 'جدول الأعمال',
                'principal': 'مدير المدرسة',
                'parent_greeting': 'أعزائي أولياء الأمور،',
                'staff_greeting': 'أعزائي الموظفين،',
                'parent_message': 'يسرنا دعوتكم لحضور اجتماع أولياء الأمور والمعلمين.',
                'staff_message': 'يسرنا دعوتكم لحضور اجتماع الموظفين.',
            }
        }

        lang = translations.get(language, translations['en'])

        if format_type == 'excel':
            return admin_generate_parent_invitation_excel(lang, invitation_type)
        else:
            return admin_generate_parent_invitation_pdf(lang, invitation_type)
    except Exception as e:
        logger.error(f"Error generating invitation: {e}")
        return HttpResponse(f"Error generating invitation: {str(e)}", status=500)

def admin_generate_parent_invitation_pdf(lang, invitation_type='parent'):
    """Generate PDF invitation (parent or staff)"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        # Determine title and greeting based on type
        if invitation_type == 'staff':
            title = lang['staff_title']
            greeting = lang['staff_greeting']
            message = lang['staff_message']
        else:
            title = lang['parent_title']
            greeting = lang['parent_greeting']
            message = lang['parent_message']

        # Header
        p.setFont("Helvetica-Bold", 16)
        draw_centered_arabic_text(p, 4.25*inch, 10.5*inch, title)
        p.setFont("Helvetica", 12)
        p.drawString(1*inch, 10*inch, f"{timezone.now().strftime('%Y-%m-%d')}")

        # Content
        y_position = 9*inch
        p.setFont("Helvetica-Bold", 12)
        draw_arabic_text(p, 1*inch, y_position, greeting)

        y_position -= 0.5*inch
        p.setFont("Helvetica", 11)
        draw_arabic_text(p, 1*inch, y_position, message)

        if invitation_type == 'parent':
            y_position -= 0.3*inch
            draw_arabic_text(p, 1*inch, y_position, "Your presence is important for discussing your child's progress.")

        # Meeting details
        y_position -= 0.6*inch
        p.setFont("Helvetica-Bold", 12)
        draw_arabic_text(p, 1*inch, y_position, "Meeting Details:")

        y_position -= 0.3*inch
        p.setFont("Helvetica", 11)
        draw_arabic_text(p, 1.5*inch, y_position, f"{lang['date']}: {timezone.now().strftime('%Y-%m-%d')}")

        y_position -= 0.25*inch
        draw_arabic_text(p, 1.5*inch, y_position, f"{lang['time']}: 10:00 AM")

        y_position -= 0.25*inch
        draw_arabic_text(p, 1.5*inch, y_position, f"{lang['location']}: School Conference Hall")

        # Footer
        y_position -= 0.8*inch
        draw_arabic_text(p, 1*inch, y_position, "We look forward to your presence.")

        y_position -= 0.5*inch
        draw_arabic_text(p, 1*inch, y_position, "Sincerely,")

        y_position -= 0.3*inch
        p.setFont("Helvetica-Bold", 11)
        draw_arabic_text(p, 1*inch, y_position, lang['principal'])

        p.save()
        buffer.seek(0)

        filename = f"{invitation_type}_invitation_{timezone.now().strftime('%Y%m%d')}.pdf"
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        logger.error(f"Error generating invitation PDF: {e}")
        return HttpResponse(f"Error generating invitation PDF: {str(e)}", status=500)

def admin_generate_parent_invitation_excel(lang, invitation_type='parent'):
    """Generate Excel invitation (parent or staff)"""
    try:
        if invitation_type == 'staff':
            title = lang['staff_title']
            message = lang['staff_message']
        else:
            title = lang['parent_title']
            message = lang['parent_message']

        data = [{
            'Title': title,
            'Date': timezone.now().strftime('%Y-%m-%d'),
            'Time': '10:00 AM',
            'Location': 'School Conference Hall',
            'Message': message
        }]

        df = pd.DataFrame(data)
        filename = f"{invitation_type}_invitation_{timezone.now().strftime('%Y%m%d')}.xlsx"
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Invitation')
            
        return response
    except Exception as e:
        logger.error(f"Error generating invitation Excel: {e}")
        return HttpResponse(f"Error generating invitation Excel: {str(e)}", status=500)

def admin_generate_report_cards(request, format_type='pdf', language='en'):
    """Generate student report cards"""
    try:
        students = Student.objects.filter(is_active=True)

        if format_type == 'pdf':
            return admin_generate_report_cards_pdf(students, language)
        else:
            return admin_generate_report_cards_excel(students, language)
    except Exception as e:
        logger.error(f"Error generating report cards: {e}")
        return HttpResponse(f"Error generating report cards: {str(e)}", status=500)

def admin_generate_report_cards_pdf(students, language):
    """Generate PDF report cards"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        for student in students[:5]:  # Limit for demo
            p.setFont("Helvetica-Bold", 16)
            p.drawString(1*inch, 10.5*inch, "Student Report Card - Trust Academy")
            p.setFont("Helvetica", 12)
            p.drawString(1*inch, 10*inch, f"Generated on: {timezone.now().strftime('%Y-%m-%d')}")

            y_position = 9*inch
            p.setFont("Helvetica-Bold", 14)
            p.drawString(1*inch, y_position, f"Student: {student.get_full_name()}")
            y_position -= 0.4*inch

            p.setFont("Helvetica", 12)
            p.drawString(1*inch, y_position, f"Student ID: {student.student_id}")
            y_position -= 0.3*inch
            p.drawString(1*inch, y_position, f"Grade: {student.get_grade_level_display()}")
            y_position -= 0.3*inch
            p.drawString(1*inch, y_position, f"Class: {student.class_room if student.class_room else 'N/A'}")
            y_position -= 0.5*inch

            # Grades section
            p.setFont("Helvetica-Bold", 12)
            p.drawString(1*inch, y_position, "Academic Performance:")
            y_position -= 0.3*inch

            p.setFont("Helvetica", 11)
            subjects = ["Mathematics", "Science", "English", "History", "Art"]
            grades = ["A", "B+", "A-", "B", "A"]
            
            for subject, grade in zip(subjects, grades):
                p.drawString(1.5*inch, y_position, f"{subject}: {grade}")
                y_position -= 0.25*inch

            y_position -= 0.3*inch
            p.setFont("Helvetica-Bold", 11)
            p.drawString(1*inch, y_position, "Overall Grade: B+")
            y_position -= 0.3*inch
            p.drawString(1*inch, y_position, "Comments: Good performance, shows improvement in Science.")
            
            p.showPage()

        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_cards_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error generating report cards PDF: {e}")
        return HttpResponse(f"Error generating report cards PDF: {str(e)}", status=500)

def admin_generate_report_cards_excel(students, language):
    """Generate Excel report cards"""
    try:
        data = []
        for student in students:
            data.append({
                'Student Name': student.get_full_name(),
                'Student ID': student.student_id,
                'Grade Level': student.get_grade_level_display(),
                'Class': str(student.class_room) if student.class_room else 'N/A',
                'Mathematics': 'A',
                'Science': 'B+',
                'English': 'A-',
                'History': 'B',
                'Art': 'A',
                'Overall Grade': 'B+',
                'Comments': 'Good performance, shows improvement in Science.'
            })

        df = pd.DataFrame(data)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="report_cards_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Report Cards')
            
        return response
    except Exception as e:
        logger.error(f"Error generating report cards Excel: {e}")
        return HttpResponse(f"Error generating report cards Excel: {str(e)}", status=500)

def admin_generate_payslips(request, format_type='pdf', language='en'):
    """Generate staff payslips"""
    try:
        staff_members = Staff.objects.filter(is_active=True)

        if format_type == 'pdf':
            return admin_generate_payslips_pdf(staff_members, language)
        else:
            return admin_generate_payslips_excel(staff_members, language)
    except Exception as e:
        logger.error(f"Error generating payslips: {e}")
        return HttpResponse(f"Error generating payslips: {str(e)}", status=500)

def admin_generate_payslips_pdf(staff_members, language):
    """Generate PDF payslips"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        for staff in staff_members[:5]:  # Limit for demo
            p.setFont("Helvetica-Bold", 16)
            p.drawString(1*inch, 10.5*inch, "Staff Payslip - Trust Academy")
            p.setFont("Helvetica", 12)
            p.drawString(1*inch, 10*inch, f"Month: {timezone.now().strftime('%B %Y')}")

            y_position = 9*inch
            p.setFont("Helvetica-Bold", 14)
            p.drawString(1*inch, y_position, f"Staff: {staff.get_full_name()}")
            y_position -= 0.4*inch

            p.setFont("Helvetica", 12)
            p.drawString(1*inch, y_position, f"Staff ID: {staff.staff_id}")
            y_position -= 0.3*inch
            p.drawString(1*inch, y_position, f"Position: {staff.get_position_display()}")
            y_position -= 0.3*inch
            p.drawString(1*inch, y_position, f"Department: Academic")
            y_position -= 0.5*inch

            # Salary details
            p.setFont("Helvetica-Bold", 12)
            p.drawString(1*inch, y_position, "Salary Details:")
            y_position -= 0.3*inch

            p.setFont("Helvetica", 11)
            salary_items = [
                ("Basic Salary", "50,000 DZD"),
                ("Housing Allowance", "10,000 DZD"),
                ("Transport Allowance", "5,000 DZD"),
                ("Other Allowances", "2,000 DZD"),
                ("Deductions", "-3,000 DZD")
            ]
            
            for item, amount in salary_items:
                p.drawString(1.5*inch, y_position, f"{item}: {amount}")
                y_position -= 0.25*inch

            y_position -= 0.3*inch
            p.setFont("Helvetica-Bold", 12)
            p.drawString(1*inch, y_position, "Net Salary: 64,000 DZD")
            
            p.showPage()

        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="payslips_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error generating payslips PDF: {e}")
        return HttpResponse(f"Error generating payslips PDF: {str(e)}", status=500)

def admin_generate_payslips_excel(staff_members, language):
    """Generate Excel payslips"""
    try:
        data = []
        for staff in staff_members:
            data.append({
                'Staff Name': staff.get_full_name(),
                'Staff ID': staff.staff_id,
                'Position': staff.get_position_display(),
                'Basic Salary': '50,000 DZD',
                'Housing Allowance': '10,000 DZD',
                'Transport Allowance': '5,000 DZD',
                'Other Allowances': '2,000 DZD',
                'Deductions': '3,000 DZD',
                'Net Salary': '64,000 DZD'
            })

        df = pd.DataFrame(data)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="payslips_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Payslips')
            
        return response
    except Exception as e:
        logger.error(f"Error generating payslips Excel: {e}")
        return HttpResponse(f"Error generating payslips Excel: {str(e)}", status=500)

def admin_generate_certificates(request, format_type='pdf', language='en'):
    """Generate school certificates"""
    try:
        students = Student.objects.filter(is_active=True)

        if format_type == 'pdf':
            return admin_generate_certificates_pdf(students, language)
        else:
            return HttpResponse("Excel format not available for certificates")
    except Exception as e:
        logger.error(f"Error generating certificates: {e}")
        return HttpResponse(f"Error generating certificates: {str(e)}", status=500)

def admin_generate_certificates_pdf(students, language):
    """Generate PDF certificates"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        for student in students[:3]:  # Limit for demo
            # Certificate border
            p.setStrokeColorRGB(0.8, 0.8, 0.8)
            p.rect(0.5*inch, 0.5*inch, 7.5*inch, 10*inch)

            # Title
            p.setFont("Helvetica-Bold", 24)
            p.drawCentredString(4.25*inch, 9*inch, "CERTIFICATE OF ACHIEVEMENT")

            # Student name
            p.setFont("Helvetica-Bold", 18)
            p.drawCentredString(4.25*inch, 7.5*inch, student.get_full_name())

            # Message
            p.setFont("Helvetica", 14)
            p.drawCentredString(4.25*inch, 6.5*inch, "has successfully completed the academic year")
            p.drawCentredString(4.25*inch, 6*inch, f"in Grade {student.get_grade_level_display()}")

            # Date
            p.drawCentredString(4.25*inch, 4*inch, timezone.now().strftime('%B %d, %Y'))

            # Signature
            p.drawCentredString(4.25*inch, 2*inch, "School Principal")

            p.showPage()

        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="certificates_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error generating certificates PDF: {e}")
        return HttpResponse(f"Error generating certificates PDF: {str(e)}", status=500)

def admin_generate_fee_statements(request, format_type='pdf', language='en'):
    """Generate fee statements"""
    try:
        students = Student.objects.filter(is_active=True)

        if format_type == 'pdf':
            return admin_generate_fee_statements_pdf(students, language)
        else:
            return admin_generate_fee_statements_excel(students, language)
    except Exception as e:
        logger.error(f"Error generating fee statements: {e}")
        return HttpResponse(f"Error generating fee statements: {str(e)}", status=500)

def admin_generate_fee_statements_pdf(students, language):
    """Generate PDF fee statements"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        p.setFont("Helvetica-Bold", 16)
        p.drawString(1*inch, 10.5*inch, "Fee Statements - Trust Academy")
        p.setFont("Helvetica", 12)
        p.drawString(1*inch, 10*inch, f"Generated on: {timezone.now().strftime('%Y-%m-%d')}")

        y_position = 9.5*inch
        for student in students[:8]:  # Limit for demo
            if y_position < 2*inch:
                p.showPage()
                y_position = 10*inch

            p.setFont("Helvetica-Bold", 12)
            p.drawString(1*inch, y_position, f"Student: {student.get_full_name()}")
            y_position -= 0.3*inch

            p.setFont("Helvetica", 10)
            p.drawString(1*inch, y_position, "Tuition Fee: 25,000 DZD")
            y_position -= 0.2*inch
            p.drawString(1*inch, y_position, "Transportation: 5,000 DZD")
            y_position -= 0.2*inch
            p.drawString(1*inch, y_position, "Books & Materials: 3,000 DZD")
            y_position -= 0.2*inch
            p.drawString(1*inch, y_position, "Total Due: 33,000 DZD")
            y_position -= 0.4*inch

        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="fee_statements_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error generating fee statements PDF: {e}")
        return HttpResponse(f"Error generating fee statements PDF: {str(e)}", status=500)

def admin_generate_fee_statements_excel(students, language):
    """Generate Excel fee statements"""
    try:
        data = []
        for student in students:
            data.append({
                'Student Name': student.get_full_name(),
                'Student ID': student.student_id,
                'Grade Level': student.get_grade_level_display(),
                'Tuition Fee': '25,000 DZD',
                'Transportation': '5,000 DZD',
                'Books & Materials': '3,000 DZD',
                'Total Due': '33,000 DZD'
            })

        df = pd.DataFrame(data)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="fee_statements_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Fee Statements')
            
        return response
    except Exception as e:
        logger.error(f"Error generating fee statements Excel: {e}")
        return HttpResponse(f"Error generating fee statements Excel: {str(e)}", status=500)

def admin_generate_id_cards(request, format_type='pdf', language='en'):
    """Generate ID cards"""
    try:
        students = Student.objects.filter(is_active=True)

        if format_type == 'pdf':
            return admin_generate_id_cards_pdf(students, language)
        else:
            return HttpResponse("Excel format not available for ID cards")
    except Exception as e:
        logger.error(f"Error generating ID cards: {e}")
        return HttpResponse(f"Error generating ID cards: {str(e)}", status=500)

def admin_generate_id_cards_pdf(students, language):
    """Generate PDF ID cards"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        # Create ID cards (2 per row, 3 rows per page)
        x_positions = [1*inch, 4.5*inch]
        y_positions = [9*inch, 6.5*inch, 4*inch]

        card_count = 0
        for student in students[:6]:  # Limit for demo
            if card_count >= 6:  # 6 cards per page
                p.showPage()
                card_count = 0
                y_positions = [9*inch, 6.5*inch, 4*inch]

            x = x_positions[card_count % 2]
            y = y_positions[card_count // 2]

            # ID card border
            p.setStrokeColorRGB(0, 0, 0)
            p.rect(x, y-2.5*inch, 3.2*inch, 2.2*inch)

            # School name
            p.setFont("Helvetica-Bold", 10)
            p.drawString(x+0.2*inch, y-0.3*inch, "Trust Academy")

            # Student photo placeholder
            p.rect(x+0.2*inch, y-1.2*inch, 1*inch, 1.2*inch)
            p.drawString(x+0.4*inch, y-0.8*inch, "PHOTO")

            # Student info
            p.setFont("Helvetica-Bold", 9)
            p.drawString(x+1.4*inch, y-0.5*inch, student.get_full_name())
            p.setFont("Helvetica", 8)
            p.drawString(x+1.4*inch, y-0.8*inch, f"ID: {student.student_id}")
            p.drawString(x+1.4*inch, y-1.1*inch, f"Grade: {student.get_grade_level_display()}")
            p.drawString(x+1.4*inch, y-1.4*inch, f"Class: {student.class_room.name if student.class_room else 'N/A'}")

            card_count += 1

        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="id_cards_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error generating ID cards PDF: {e}")
        return HttpResponse(f"Error generating ID cards PDF: {str(e)}", status=500)

def admin_generate_calendar(request, format_type='pdf', language='en'):
    """Generate school calendar"""
    try:
        if format_type == 'pdf':
            return admin_generate_calendar_pdf(language)
        else:
            return admin_generate_calendar_excel(language)
    except Exception as e:
        logger.error(f"Error generating calendar: {e}")
        return HttpResponse(f"Error generating calendar: {str(e)}", status=500)

def admin_generate_calendar_pdf(language):
    """Generate PDF school calendar"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        
        # Header
        p.setFont("Helvetica-Bold", 16)
        p.drawString(1*inch, 10.5*inch, "School Calendar - Trust Academy")
        p.setFont("Helvetica", 12)
        p.drawString(1*inch, 10*inch, f"Academic Year: 2024-2025")
        
        # Sample calendar content
        y_position = 9*inch
        p.setFont("Helvetica-Bold", 12)
        p.drawString(1*inch, y_position, "Important Dates:")
        
        dates = [
            "September 5, 2024 - First Day of School",
            "October 29-November 2, 2024 - Mid-term Break", 
            "December 21, 2024-January 5, 2025 - Winter Break",
            "March 15-23, 2025 - Spring Break",
            "June 15, 2025 - Last Day of School"
        ]
        
        y_position -= 0.3*inch
        p.setFont("Helvetica", 10)
        for date in dates:
            p.drawString(1.5*inch, y_position, date)
            y_position -= 0.2*inch
        
        p.save()
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="school_calendar_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error generating calendar PDF: {e}")
        return HttpResponse(f"Error generating calendar PDF: {str(e)}", status=500)

def admin_generate_calendar_excel(language):
    """Generate Excel school calendar"""
    try:
        data = [
            {'Event': 'First Day of School', 'Date': 'September 5, 2024'},
            {'Event': 'Mid-term Break', 'Date': 'October 29-November 2, 2024'},
            {'Event': 'Winter Break', 'Date': 'December 21, 2024-January 5, 2025'},
            {'Event': 'Spring Break', 'Date': 'March 15-23, 2025'},
            {'Event': 'Last Day of School', 'Date': 'June 15, 2025'}
        ]
        
        df = pd.DataFrame(data)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="school_calendar_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Calendar')
            
        return response
    except Exception as e:
        logger.error(f"Error generating calendar Excel: {e}")
        return HttpResponse(f"Error generating calendar Excel: {str(e)}", status=500)

def admin_generate_schedules(request, format_type='pdf', language='en'):
    """Generate class schedules"""
    try:
        classes = ClassRoom.objects.all()
        
        if format_type == 'pdf':
            return admin_generate_schedules_pdf(classes, language)
        else:
            return admin_generate_schedules_excel(classes, language)
    except Exception as e:
        logger.error(f"Error generating schedules: {e}")
        return HttpResponse(f"Error generating schedules: {str(e)}", status=500)

def admin_generate_schedules_pdf(classes, language):
    """Generate PDF class schedules"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        
        p.setFont("Helvetica-Bold", 16)
        p.drawString(1*inch, 10.5*inch, "Class Schedules - Trust Academy")
        
        y_position = 9.5*inch
        for class_room in classes:
            if y_position < 2*inch:
                p.showPage()
                y_position = 10*inch
            
            p.setFont("Helvetica-Bold", 12)
            p.drawString(1*inch, y_position, f"Class: {class_room}")
            y_position -= 0.3*inch
            
            p.setFont("Helvetica", 10)
            schedule_items = [
                "Monday: Math (8:00-9:00), Science (9:00-10:00)",
                "Tuesday: English (8:00-9:00), History (9:00-10:00)",
                "Wednesday: Math (8:00-9:00), Art (9:00-10:00)",
                "Thursday: Science (8:00-9:00), PE (9:00-10:00)",
                "Friday: Review (8:00-9:00), Tests (9:00-10:00)"
            ]
            
            for item in schedule_items:
                p.drawString(1.5*inch, y_position, item)
                y_position -= 0.2*inch
            
            y_position -= 0.3*inch
        
        p.save()
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="class_schedules_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error generating schedules PDF: {e}")
        return HttpResponse(f"Error generating schedules PDF: {str(e)}", status=500)

def admin_generate_schedules_excel(classes, language):
    """Generate Excel class schedules"""
    try:
        data = []
        for class_room in classes:
            data.append({
                'Class': str(class_room),
                'Monday': 'Math (8:00-9:00), Science (9:00-10:00)',
                'Tuesday': 'English (8:00-9:00), History (9:00-10:00)',
                'Wednesday': 'Math (8:00-9:00), Art (9:00-10:00)',
                'Thursday': 'Science (8:00-9:00), PE (9:00-10:00)',
                'Friday': 'Review (8:00-9:00), Tests (9:00-10:00)'
            })
        
        df = pd.DataFrame(data)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="class_schedules_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Schedules')
            
        return response
    except Exception as e:
        logger.error(f"Error generating schedules Excel: {e}")
        return HttpResponse(f"Error generating schedules Excel: {str(e)}", status=500)

def admin_generate_attendance_certificates(request, format_type='pdf', language='en'):
    """Generate attendance certificates"""
    try:
        students = Student.objects.filter(is_active=True)
        
        if format_type == 'pdf':
            return admin_generate_attendance_certificates_pdf(students, language)
        else:
            return admin_generate_attendance_certificates_excel(students, language)
    except Exception as e:
        logger.error(f"Error generating attendance certificates: {e}")
        return HttpResponse(f"Error generating attendance certificates: {str(e)}", status=500)

def admin_generate_attendance_certificates_pdf(students, language):
    """Generate PDF attendance certificates"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        for student in students[:3]:  # Limit for demo
            # Certificate border
            p.setStrokeColorRGB(0.8, 0.8, 0.8)
            p.rect(0.5*inch, 0.5*inch, 7.5*inch, 10*inch)

            # Title
            p.setFont("Helvetica-Bold", 22)
            p.drawCentredString(4.25*inch, 9*inch, "CERTIFICATE OF ATTENDANCE")

            # Student name
            p.setFont("Helvetica-Bold", 18)
            p.drawCentredString(4.25*inch, 7.5*inch, student.get_full_name())

            # Message
            p.setFont("Helvetica", 14)
            p.drawCentredString(4.25*inch, 6.5*inch, "has maintained excellent attendance")
            p.drawCentredString(4.25*inch, 6*inch, f"during the academic year 2024-2025")
            p.drawCentredString(4.25*inch, 5.5*inch, f"in Grade {student.get_grade_level_display()}")

            # Attendance stats
            p.drawCentredString(4.25*inch, 4.5*inch, "Attendance Rate: 95%")
            p.drawCentredString(4.25*inch, 4*inch, "Days Present: 170/180")

            # Date
            p.drawCentredString(4.25*inch, 3*inch, timezone.now().strftime('%B %d, %Y'))

            # Signature
            p.drawCentredString(4.25*inch, 2*inch, "School Principal")

            p.showPage()

        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="attendance_certificates_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error generating attendance certificates PDF: {e}")
        return HttpResponse(f"Error generating attendance certificates PDF: {str(e)}", status=500)

def admin_generate_attendance_certificates_excel(students, language):
    """Generate Excel attendance certificates data"""
    try:
        data = []
        for student in students:
            data.append({
                'Student Name': student.get_full_name(),
                'Student ID': student.student_id,
                'Grade Level': student.get_grade_level_display(),
                'Class': str(student.class_room) if student.class_room else 'N/A',
                'Attendance Rate': '95%',
                'Days Present': '170/180',
                'Certificate Issued': 'Yes'
            })
        
        df = pd.DataFrame(data)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="attendance_certificates_{timezone.now().strftime("%Y%m%d")}.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Attendance Certificates')
            
        return response
    except Exception as e:
        logger.error(f"Error generating attendance certificates Excel: {e}")
        return HttpResponse(f"Error generating attendance certificates Excel: {str(e)}", status=500)
