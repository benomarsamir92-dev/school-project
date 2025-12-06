import io
#import pandas as pd
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.utils import timezone
from django.db import models
from django.core.paginator import Paginator
from django.core.cache import cache
from django.views.decorators.cache import never_cache
from django.views.generic import View
from .models import Student, Staff, ClassRoom, Subject, Payment, Attendance, Grade, InventoryItem, StudentCertificate, Schedule
from .utils import generate_whatsapp_link

# Import for document generation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
import tempfile
import os

from django.utils.translation import gettext as _
from django.utils.translation import activate, get_language

# Set up logger
logger = logging.getLogger(__name__)

# Permission check functions
def staff_check(user):
    """Check if user is staff"""
    return hasattr(user, 'staff')

def teacher_check(user):
    """Check if user is a teacher"""
    return hasattr(user, 'staff') and user.staff.position == 'teacher'

def admin_staff_check(user):
    """Check if user is admin staff"""
    return hasattr(user, 'staff') and user.staff.position in ['admin', 'principal']

# Custom Mixins for class-based views
class StaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return staff_check(self.request.user)

class TeacherRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return teacher_check(self.request.user)

class AdminStaffRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return admin_staff_check(self.request.user)

# Authentication Views
def staff_login(request):
    """Staff login view"""
    try:
        if request.method == 'POST':
            form = AuthenticationForm(request, data=request.POST)
            if form.is_valid():
                username = form.cleaned_data.get('username')
                password = form.cleaned_data.get('password')
                user = authenticate(username=username, password=password)

                if user is not None and hasattr(user, 'staff'):
                    login(request, user)
                    logger.info(f"Staff login successful: {username}")
                    messages.success(request, f'Welcome back, {user.staff.get_full_name()}!')
                    return redirect('staff_dashboard')
                else:
                    logger.warning(f"Failed staff login attempt: {username}")
                    messages.error(request, 'Invalid staff credentials or account not found.')
            else:
                logger.warning(f"Invalid login form: {form.errors}")
                messages.error(request, 'Invalid username or password.')
        else:
            form = AuthenticationForm()

        return render(request, 'staff/login.html', {'form': form})
        
    except Exception as e:
        logger.error(f"Error in staff_login: {e}")
        messages.error(request, 'An error occurred during login.')
        return render(request, 'staff/login.html', {'form': AuthenticationForm()})

def staff_logout(request):
    """Staff logout view"""
    try:
        logout(request)
        messages.info(request, 'You have been logged out successfully.')
        return redirect('staff_login')
    except Exception as e:
        logger.error(f"Error in staff_logout: {e}")
        messages.error(request, 'Error during logout.')
        return redirect('staff_login')

# Dashboard Views
@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def staff_dashboard(request):
    """Main staff dashboard"""
    try:
        staff = request.user.staff
        context = {
            'staff': staff,
            'today': timezone.now().date(),
            'schedules': Schedule.objects.all()[:5],  # ADDED: Schedules for dashboard
        }

        # Add position-specific data
        if staff.position == 'teacher':
            context['my_classes'] = ClassRoom.objects.filter(teacher=staff)
            context['my_subjects'] = Subject.objects.filter(teacher=staff)
            context['recent_attendance'] = Attendance.objects.filter(
                student__class_room__teacher=staff
            ).order_by('-date')[:5]

        elif staff.position in ['admin', 'principal']:
            context['total_students'] = Student.objects.filter(is_active=True).count()
            context['total_staff'] = Staff.objects.filter(is_active=True).count()
            context['pending_payments'] = Payment.objects.filter(status='pending').count()
            context['recent_students'] = Student.objects.filter(is_active=True).order_by('-enrollment_date')[:5]

        return render(request, 'staff/dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in staff_dashboard: {e}")
        messages.error(request, 'Error loading dashboard.')
        return render(request, 'staff/dashboard.html', {'staff': request.user.staff})
    
@login_required
@user_passes_test(teacher_check, login_url='/staff/login/')
def teacher_dashboard(request):
    """Teacher-specific dashboard"""
    try:
        staff = request.user.staff
        my_classes = ClassRoom.objects.filter(teacher=staff)
        my_subjects = Subject.objects.filter(teacher=staff)

        # Today's attendance summary
        today_attendance = Attendance.objects.filter(
            student__class_room__in=my_classes,
            date=timezone.now().date()
        )

        context = {
            'staff': staff,
            'my_classes': my_classes,
            'my_subjects': my_subjects,
            'today_attendance': today_attendance,
            'attendance_summary': {
                'present': today_attendance.filter(status='present').count(),
                'absent': today_attendance.filter(status='absent').count(),
                'late': today_attendance.filter(status='late').count(),
            }
        }

        return render(request, 'staff/teacher_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in teacher_dashboard: {e}")
        messages.error(request, 'Error loading teacher dashboard.')
        return redirect('staff_dashboard')

@login_required
@user_passes_test(admin_staff_check, login_url='/staff/login/')
def admin_dashboard(request):
    """Admin staff dashboard"""
    try:
        staff = request.user.staff

        context = {
            'staff': staff,
            'stats': {
                'total_students': Student.objects.filter(is_active=True).count(),
                'total_staff': Staff.objects.filter(is_active=True).count(),
                'active_classes': ClassRoom.objects.count(),
                'pending_payments': Payment.objects.filter(status='pending').count(),
                'today_attendance': Attendance.objects.filter(date=timezone.now().date()).count(),
            },
            'recent_students': Student.objects.filter(is_active=True).order_by('-enrollment_date')[:5],
            'recent_payments': Payment.objects.all().order_by('-created_at')[:5],
        }

        return render(request, 'staff/admin_dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Error in admin_dashboard: {e}")
        messages.error(request, 'Error loading admin dashboard.')
        return redirect('staff_dashboard')

# Student Management Views
@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def student_list(request):
    """List all students with pagination"""
    try:
        students = Student.objects.filter(is_active=True).order_by('grade_level', 'first_name')
        
        paginator = Paginator(students, 25)  # 25 students per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'staff': request.user.staff,
            'page_obj': page_obj,
        }

        return render(request, 'staff/student_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in student_list: {e}")
        messages.error(request, 'Error loading student list.')
        return render(request, 'staff/student_list.html', {'staff': request.user.staff})

@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def student_detail(request, pk):
    """Student detail view"""
    try:
        student = get_object_or_404(Student, pk=pk)

        # Teachers can only see their own students
        if request.user.staff.position == 'teacher':
            if not ClassRoom.objects.filter(teacher=request.user.staff, student=student).exists():
                logger.warning(f"Unauthorized access attempt to student {pk} by teacher {request.user.staff.id}")
                return HttpResponseForbidden("You can only view your own students.")

        context = {
            'staff': request.user.staff,
            'student': student,
            'attendance_records': Attendance.objects.filter(student=student).order_by('-date')[:10],
            'grades': Grade.objects.filter(student=student).order_by('-year', '-semester'),
            'payments': Payment.objects.filter(student=student).order_by('-due_date'),
        }

        return render(request, 'staff/student_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in student_detail: {e}")
        messages.error(request, 'Error loading student details.')
        return redirect('student_list')

# Attendance Views
@login_required
@user_passes_test(teacher_check, login_url='/staff/login/')
def take_attendance(request, class_id=None):
    """Take attendance for a class"""
    try:
        staff = request.user.staff

        if class_id:
            class_room = get_object_or_404(ClassRoom, pk=class_id, teacher=staff)
        else:
            # Get teacher's first class if no class specified
            class_room = ClassRoom.objects.filter(teacher=staff).first()
            if not class_room:
                messages.error(request, 'You are not assigned to any classes.')
                return redirect('teacher_dashboard')

        students = Student.objects.filter(class_room=class_room, is_active=True)

        if request.method == 'POST':
            date = request.POST.get('date', timezone.now().date())
            
            # Validate date (only allow today for teachers)
            if date != timezone.now().date():
                messages.error(request, 'Teachers can only record attendance for today.')
                return redirect('take_attendance', class_id=class_room.id)

            attendance_count = 0
            for student in students:
                status = request.POST.get(f'status_{student.id}', 'present')
                notes = request.POST.get(f'notes_{student.id}', '')

                # Update or create attendance record
                attendance, created = Attendance.objects.update_or_create(
                    student=student,
                    date=date,
                    defaults={
                        'status': status,
                        'notes': notes,
                        'recorded_by': staff,
                    }
                )
                attendance_count += 1

            logger.info(f"Attendance recorded for {attendance_count} students in {class_room} by {staff}")
            messages.success(request, f'Attendance recorded for {class_room} on {date}')
            return redirect('take_attendance', class_id=class_room.id)

        # Get today's existing attendance
        today_attendance = {
            att.student.id: att
            for att in Attendance.objects.filter(
                student__in=students,
                date=timezone.now().date()
            )
        }

        context = {
            'staff': staff,
            'class_room': class_room,
            'students': students,
            'today_attendance': today_attendance,
            'today': timezone.now().date(),
        }

        return render(request, 'staff/take_attendance.html', context)
        
    except Exception as e:
        logger.error(f"Error in take_attendance: {e}")
        messages.error(request, 'Error recording attendance.')
        return redirect('teacher_dashboard')

@login_required
@user_passes_test(teacher_check, login_url='/staff/login/')
def attendance_history(request, class_id):
    """View attendance history for a class"""
    try:
        staff = request.user.staff
        class_room = get_object_or_404(ClassRoom, pk=class_id, teacher=staff)

        # Get date range from request or default to current month
        today = timezone.now().date()
        start_date = request.GET.get('start_date', today.replace(day=1))
        end_date = request.GET.get('end_date', today)

        attendance_records = Attendance.objects.filter(
            student__class_room=class_room,
            date__range=[start_date, end_date]
        ).order_by('-date', 'student')

        # Paginate results
        paginator = Paginator(attendance_records, 50)  # 50 records per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'staff': staff,
            'class_room': class_room,
            'page_obj': page_obj,
            'start_date': start_date,
            'end_date': end_date,
        }

        return render(request, 'staff/attendance_history.html', context)
        
    except Exception as e:
        logger.error(f"Error in attendance_history: {e}")
        messages.error(request, 'Error loading attendance history.')
        return redirect('teacher_dashboard')

# Grade Management Views
@login_required
@user_passes_test(teacher_check, login_url='/staff/login/')
def enter_grades(request, subject_id):
    """Enter grades for a subject"""
    try:
        staff = request.user.staff
        subject = get_object_or_404(Subject, pk=subject_id, teacher=staff)

        students = Student.objects.filter(
            grade_level=subject.grade_level,
            is_active=True
        ).order_by('first_name')

        if request.method == 'POST':
            semester = request.POST.get('semester')
            year = request.POST.get('year', timezone.now().year)

            grades_entered = 0
            for student in students:
                grade_value = request.POST.get(f'grade_{student.id}')
                comments = request.POST.get(f'comments_{student.id}', '')

                if grade_value:  # Only save if grade is provided
                    grade, created = Grade.objects.update_or_create(
                        student=student,
                        subject=subject,
                        semester=semester,
                        year=year,
                        defaults={
                            'score': grade_value,
                            'comments': comments,
                            'graded_by': staff,
                        }
                    )
                    grades_entered += 1

            logger.info(f"Grades entered for {grades_entered} students in {subject} by {staff}")
            messages.success(request, f'Grades entered for {subject.name}')
            return redirect('enter_grades', subject_id=subject.id)

        context = {
            'staff': staff,
            'subject': subject,
            'students': students,
            'current_year': timezone.now().year,
        }

        return render(request, 'staff/enter_grades.html', context)
        
    except Exception as e:
        logger.error(f"Error in enter_grades: {e}")
        messages.error(request, 'Error entering grades.')
        return redirect('teacher_dashboard')

# WhatsApp Integration Views
@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
@never_cache
def send_whatsapp_message(request, student_id):
    """Send WhatsApp message to student's parent with rate limiting"""
    try:
        # Rate limiting: max 10 messages per minute per staff
        cache_key = f"whatsapp_rate_limit_{request.user.staff.id}"
        message_count = cache.get(cache_key, 0)
        
        if message_count >= 10:
            logger.warning(f"WhatsApp rate limit exceeded for staff {request.user.staff.id}")
            return JsonResponse({'success': False, 'error': 'Rate limit exceeded. Please wait a minute.'})

        student = get_object_or_404(Student, pk=student_id)

        # Check permission
        if request.user.staff.position == 'teacher':
            if not ClassRoom.objects.filter(teacher=request.user.staff, student=student).exists():
                logger.warning(f"Unauthorized WhatsApp attempt for student {student_id} by teacher {request.user.staff.id}")
                return JsonResponse({'success': False, 'error': 'You can only message your own students.'})

        if request.method == 'POST':
            message = request.POST.get('message', '').strip()
            
            # Validate message
            if not message:
                return JsonResponse({'success': False, 'error': 'Message cannot be empty.'})
            
            if len(message) > 1000:
                return JsonResponse({'success': False, 'error': 'Message too long. Maximum 1000 characters.'})
                
            if not student.parent_phone:
                return JsonResponse({'success': False, 'error': 'No phone number available for this student.'})

            whatsapp_url = generate_whatsapp_link(student.parent_phone, message)
            
            # Update rate limit
            cache.set(cache_key, message_count + 1, 60)  # 60 seconds
            
            logger.info(f"WhatsApp message sent to {student.parent_phone} for student {student_id} by staff {request.user.staff.id}")
            return JsonResponse({'success': True, 'whatsapp_url': whatsapp_url})
        else:
            return JsonResponse({'success': False, 'error': 'Invalid request method'})
            
    except Exception as e:
        logger.error(f"Error in send_whatsapp_message: {e}")
        return JsonResponse({'success': False, 'error': 'Internal server error'})

# Document Generation Views
@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def document_generator(request):
    """Main document generator page"""
    try:
        classes = ClassRoom.objects.all()
        students = Student.objects.filter(is_active=True)

        context = {
            'staff': request.user.staff,
            'classes': classes,
            'students': students,
        }

        return render(request, 'staff/document_generator.html', context)
        
    except Exception as e:
        logger.error(f"Error in document_generator: {e}")
        messages.error(request, 'Error loading document generator.')
        return render(request, 'staff/document_generator.html', {'staff': request.user.staff})

@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def generate_student_list(request, class_id=None, format_type='pdf', language='en'):
    """Generate student list in PDF/Excel with proper translation"""
    try:
        if class_id and class_id != 'all':
            class_room = get_object_or_404(ClassRoom, pk=class_id)
            students = Student.objects.filter(class_room=class_room, is_active=True)
            title = f"Student List - {class_room}"
        else:
            students = Student.objects.filter(is_active=True)
            title = "All Students"

        # Enhanced language support with proper activation
        translations = {
            'en': {
                'code': 'en',
                'title': 'Student List - Trust Academy',
                'name': 'Name',
                'student_id': 'Student ID',
                'grade': 'Grade',
                'parent': 'Parent',
                'phone': 'Phone',
                'date': 'Date'
            },
            'fr': {
                'code': 'fr',
                'title': 'Liste des Étudiants - Trust Academy',
                'name': 'Nom',
                'student_id': 'ID Étudiant',
                'grade': 'Niveau',
                'parent': 'Parent',
                'phone': 'Téléphone',
                'date': 'Date'
            },
            'ar': {
                'code': 'ar',
                'title': 'قائمة الطلاب - Trust Academy',
                'name': 'الاسم',
                'student_id': 'رقم الطالب',
                'grade': 'الصف',
                'parent': 'ولي الأمر',
                'phone': 'الهاتف',
                'date': 'التاريخ'
            }
        }

        lang = translations.get(language, translations['en'])
        
        # Activate the requested language
        activate(lang['code'])

        if format_type == 'excel':
            return generate_student_excel(students, title, lang)
        else:
            return generate_student_pdf(students, title, lang)
            
    except Exception as e:
        logger.error(f"Error generating student list: {e}")
        messages.error(request, 'Error generating student list.')
        return redirect('document_generator')

def generate_student_pdf(students, title, lang):
    """Generate PDF student list with RTL support for Arabic"""
    try:
        current_language = get_language()
        activate(lang['code'])
        
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        # Check if language is RTL (Arabic)
        is_rtl = lang['code'] == 'ar'
        
        if is_rtl:
            # For RTL languages, adjust the layout
            p.setFont("Helvetica-Bold", 16)
            p.drawString(6*inch, 10.5*inch, lang['title'])  # Right-aligned for Arabic
            p.setFont("Helvetica", 12)
            p.drawString(6*inch, 10*inch, f"{lang['date']}: {timezone.now().strftime('%Y-%m-%d')}")

            # Table headers - right-aligned for RTL
            y_position = 9.5*inch
            p.setFont("Helvetica-Bold", 10)
            p.drawString(7*inch, y_position, lang['phone'])
            p.drawString(5.5*inch, y_position, lang['parent'])
            p.drawString(4*inch, y_position, lang['grade'])
            p.drawString(2*inch, y_position, lang['name'])
            p.drawString(1*inch, y_position, lang['student_id'])

            # Student data - right-aligned
            p.setFont("Helvetica", 9)
            y_position -= 0.3*inch

            for student in students:
                if y_position < 1*inch:
                    p.showPage()
                    y_position = 10*inch

                p.drawString(7*inch, y_position, student.parent_phone)
                p.drawString(5.5*inch, y_position, student.parent_name)
                p.drawString(4*inch, y_position, student.get_grade_level_display())
                p.drawString(2*inch, y_position, student.get_full_name())
                p.drawString(1*inch, y_position, student.student_id)
                y_position -= 0.25*inch
        else:
            # Original LTR layout for other languages
            p.setFont("Helvetica-Bold", 16)
            p.drawString(1*inch, 10.5*inch, lang['title'])
            p.setFont("Helvetica", 12)
            p.drawString(1*inch, 10*inch, f"{lang['date']}: {timezone.now().strftime('%Y-%m-%d')}")

            # Table headers
            y_position = 9.5*inch
            p.setFont("Helvetica-Bold", 10)
            p.drawString(1*inch, y_position, lang['student_id'])
            p.drawString(2*inch, y_position, lang['name'])
            p.drawString(4*inch, y_position, lang['grade'])
            p.drawString(5.5*inch, y_position, lang['parent'])
            p.drawString(7*inch, y_position, lang['phone'])

            # Student data
            p.setFont("Helvetica", 9)
            y_position -= 0.3*inch

            for student in students:
                if y_position < 1*inch:
                    p.showPage()
                    y_position = 10*inch

                p.drawString(1*inch, y_position, student.student_id)
                p.drawString(2*inch, y_position, student.get_full_name())
                p.drawString(4*inch, y_position, student.get_grade_level_display())
                p.drawString(5.5*inch, y_position, student.parent_name)
                p.drawString(7*inch, y_position, student.parent_phone)
                y_position -= 0.25*inch

        p.save()
        buffer.seek(0)

        # Reactivate original language
        activate(current_language)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="student_list_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"Error generating student PDF: {e}")
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

def generate_student_excel(students, title, lang):
    """Generate Excel student list"""
    try:
        data = []
        for student in students:
            data.append({
                lang['student_id']: student.student_id,
                lang['name']: student.get_full_name(),
                lang['grade']: student.get_grade_level_display(),
                lang['parent']: student.parent_name,
                lang['phone']: student.parent_phone,
            })

        df = pd.DataFrame(data)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="student_list_{timezone.now().strftime("%Y%m%d")}.xlsx"'

        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Students')
            
        return response
        
    except Exception as e:
        logger.error(f"Error generating student Excel: {e}")
        return HttpResponse(f"Error generating Excel: {str(e)}", status=500)

@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def generate_meeting_invitation(request, meeting_type='parent', format_type='pdf', language='en'):
    """Generate meeting invitations"""
    try:
        translations = {
            'en': {
                'parent_title': 'Parent-Teacher Meeting Invitation - Trust Academy',
                'staff_title': 'Staff Meeting Invitation - Trust Academy',
                'date': 'Date',
                'time': 'Time',
                'location': 'Location',
                'agenda': 'Agenda',
                'dear': 'Dear',
                'sincerely': 'Sincerely',
                'principal': 'School Principal'
            },
            'fr': {
                'parent_title': 'Invitation Réunion Parents-Enseignants - Trust Academy',
                'staff_title': 'Invitation Réunion du Personnel - Trust Academy',
                'date': 'Date',
                'time': 'Heure',
                'location': 'Lieu',
                'agenda': 'Ordre du Jour',
                'dear': 'Cher',
                'sincerely': 'Cordialement',
                'principal': 'Directeur de l\'École'
            },
            'ar': {
                'parent_title': 'دعوة اجتماع أولياء الأمور - Trust Academy',
                'staff_title': 'دعوة اجتماع الموظفين - Trust Academy',
                'date': 'التاريخ',
                'time': 'الوقت',
                'location': 'المكان',
                'agenda': 'جدول الأعمال',
                'dear': 'عزيزي',
                'sincerely': 'مع خالص التحيات',
                'principal': 'مدير المدرسة'
            }
        }

        lang = translations.get(language, translations['en'])

        # Generate simple PDF invitation
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        p.setFont("Helvetica-Bold", 18)
        p.drawString(2*inch, 10*inch, lang['parent_title'] if meeting_type == 'parent' else lang['staff_title'])

        p.setFont("Helvetica", 12)
        p.drawString(1*inch, 9*inch, f"{lang['date']}: {(timezone.now() + timezone.timedelta(days=7)).strftime('%Y-%m-%d')}")
        p.drawString(1*inch, 8.5*inch, f"{lang['time']}: 14:00")
        p.drawString(1*inch, 8*inch, f"{lang['location']}: School Main Hall")
        p.drawString(1*inch, 7.5*inch, f"{lang['agenda']}: Academic progress discussion")

        p.setFont("Helvetica", 10)
        p.drawString(1*inch, 6*inch, f"{lang['sincerely']},")
        p.drawString(1*inch, 5.5*inch, lang['principal'])

        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="meeting_invitation_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"Error generating meeting invitation: {e}")
        return HttpResponse(f"Error generating invitation: {str(e)}", status=500)

@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def generate_staff_list(request, format_type='pdf', language='en'):
    """Generate staff list"""
    try:
        staff_members = Staff.objects.filter(is_active=True)

        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)

        p.setFont("Helvetica-Bold", 16)
        p.drawString(1*inch, 10.5*inch, "Staff Directory - Trust Academy")
        p.setFont("Helvetica", 12)
        p.drawString(1*inch, 10*inch, f"Generated on: {timezone.now().strftime('%Y-%m-%d')}")

        # Table headers
        y_position = 9.5*inch
        p.setFont("Helvetica-Bold", 10)
        p.drawString(1*inch, y_position, "Staff ID")
        p.drawString(2*inch, y_position, "Name")
        p.drawString(4*inch, y_position, "Position")
        p.drawString(6*inch, y_position, "Phone")

        # Staff data
        p.setFont("Helvetica", 9)
        y_position -= 0.3*inch

        for staff in staff_members:
            if y_position < 1*inch:
                p.showPage()
                y_position = 10*inch

            p.drawString(1*inch, y_position, staff.staff_id)
            p.drawString(2*inch, y_position, staff.get_full_name())
            p.drawString(4*inch, y_position, staff.get_position_display())
            p.drawString(6*inch, y_position, staff.phone)
            y_position -= 0.25*inch

        p.save()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="staff_directory_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"Error generating staff list: {e}")
        return HttpResponse(f"Error generating staff list: {str(e)}", status=500)

# Public Views (no login required)
def home(request):
    """Public homepage"""
    try:
        return render(request, 'public/home.html')
    except Exception as e:
        logger.error(f"Error loading home page: {e}")
        return HttpResponse("Error loading home page", status=500)

def about(request):
    """About page"""
    try:
        return render(request, 'public/about.html')
    except Exception as e:
        logger.error(f"Error loading about page: {e}")
        return HttpResponse("Error loading about page", status=500)

def contact(request):
    """Contact page"""
    try:
        return render(request, 'public/contact.html')
    except Exception as e:
        logger.error(f"Error loading contact page: {e}")
        return HttpResponse("Error loading contact page", status=500)

# API Views
@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def api_student_search(request):
    """API for searching students"""
    try:
        query = request.GET.get('q', '').strip()

        if query:
            students = Student.objects.filter(
                models.Q(first_name__icontains=query) |
                models.Q(last_name__icontains=query) |
                models.Q(student_id__icontains=query)
            ).filter(is_active=True)[:10]

            results = [
                {
                    'id': student.id,
                    'text': f"{student.get_full_name()} ({student.student_id}) - {student.get_grade_level_display()}"
                }
                for student in students
            ]
        else:
            results = []

        return JsonResponse({'results': results})
        
    except Exception as e:
        logger.error(f"Error in api_student_search: {e}")
        return JsonResponse({'results': [], 'error': 'Search failed'})

# Error Handlers
def handler403(request, exception):
    """Custom 403 error handler"""
    logger.warning(f"403 error: {exception}")
    return render(request, 'errors/403.html', status=403)

def handler404(request, exception):
    """Custom 404 error handler"""
    logger.warning(f"404 error: {exception}")
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    """Custom 500 error handler"""
    logger.error("500 error occurred")
    return render(request, 'errors/500.html', status=500)

# Schedule Views
@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def schedule_list(request):
    """List all schedules - automatically uses current language"""
    try:
        grade_level = request.GET.get('grade_level', 'tps')
        schedules = Schedule.objects.filter(grade_level=grade_level).order_by('day')
        
        context = {
            'staff': request.user.staff,
            'schedules': schedules,
            'grade_level': grade_level,
            'grade_levels': Schedule.GRADE_LEVEL_CHOICES,
        }
        
        return render(request, 'staff/schedule_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in schedule_list: {e}")
        messages.error(request, _('Error loading schedules.'))
        return render(request, 'staff/schedule_list.html', {'staff': request.user.staff})

@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def generate_schedule_pdf(request, grade_level='grade1'):  # CHANGED DEFAULT TO 'grade1'
    """Generate PDF schedule in current language"""
    try:
        schedules = Schedule.objects.filter(grade_level=grade_level).order_by('day')
        
        if not schedules.exists():
            messages.error(request, f"No schedules found for {grade_level}")
            return redirect('schedule_list')
        
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        
        # Get the display name for the grade level
        grade_display = dict(Schedule.GRADE_LEVEL_CHOICES).get(grade_level, grade_level)
        title = _("Class Schedule - %(grade)s") % {'grade': grade_display}
        
        # Header
        p.setFont("Helvetica-Bold", 16)
        p.drawString(1*inch, 10.5*inch, title)
        p.setFont("Helvetica", 12)
        p.drawString(1*inch, 10*inch, f"{_('Generated on')}: {timezone.now().strftime('%d/%m/%Y')}")
        
        # Table headers - translated
        headers = [
            _('Day'), _('08h-09h30'), _('09h30-10h30'), _('10h30-11h30'), 
            _('11h30-12h00'), _('12h00-13h00'), _('13h30-14h30'), 
            _('14h30-15h00'), _('15h00-15h30'), _('After 15h30')
        ]
        
        # Simple table implementation
        y_position = 9.5*inch
        p.setFont("Helvetica-Bold", 10)
        
        # Draw headers
        x_positions = [1*inch, 1.8*inch, 2.6*inch, 3.4*inch, 4.2*inch, 5*inch, 5.8*inch, 6.6*inch, 7.4*inch]
        for i, header in enumerate(headers[:9]):  # Limit to first 9 headers
            p.drawString(x_positions[i], y_position, header)
        
        # Schedule data
        p.setFont("Helvetica", 8)
        y_position -= 0.3*inch
        
        for schedule in schedules:
            if y_position < 1*inch:
                p.showPage()
                y_position = 10*inch
            
            # Day
            p.drawString(1*inch, y_position, schedule.get_day_display())
            
            # Time slots
            time_slots = [
                schedule.time_0800_0930, schedule.time_0930_1030, schedule.time_1030_1130,
                schedule.time_1130_1200, schedule.time_1200_1300, schedule.time_1330_1430,
                schedule.time_1430_1500, schedule.time_1500_1530, schedule.time_after_1530
            ]
            
            for i, activity in enumerate(time_slots[:9]):
                if activity:
                    # Truncate long text
                    if len(activity) > 12:
                        activity = activity[:12] + "..."
                    p.drawString(x_positions[i], y_position, activity or "")
            
            y_position -= 0.25*inch

        p.save()
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="schedule_{grade_level}_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"Error generating schedule PDF: {e}")
        return HttpResponse(f"Error generating schedule PDF: {str(e)}", status=500)


# Certificate Views
@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def certificate_student_list(request):
    """Show all students to select for certificate"""
    try:
        students = Student.objects.filter(is_active=True).order_by('grade_level', 'first_name')[:20]
        
        context = {
            'staff': request.user.staff,
            'students': students,
        }
        
        return render(request, 'staff/certificate_student_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in certificate_student_list: {e}")
        messages.error(request, 'Error loading students.')
        return render(request, 'staff/certificate_student_list.html', {'staff': request.user.staff})

@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def generate_school_certificate(request, student_id):
    """Generate official school certificate"""
    try:
        student = get_object_or_404(Student, pk=student_id)
        
        # Create certificate
        certificate = Certificate.objects.create(
            student=student,
            issued_by=request.user.staff
        )
        
        context = {
            'staff': request.user.staff,
            'student': student,
            'certificate': certificate,
            'current_language': 'ar',
        }
        
        return render(request, 'staff/official_certificate_preview.html', context)
        
    except Exception as e:
        logger.error(f"Error generating certificate: {e}")
        messages.error(request, 'Error generating certificate.')
        return redirect('certificate_student_list')

@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def official_certificate_preview(request, certificate_id):
    """Preview official certificate"""
    try:
        certificate = get_object_or_404(Certificate, pk=certificate_id)
        language = request.GET.get('lang', 'ar')
        
        context = {
            'staff': request.user.staff,
            'certificate': certificate,
            'student': certificate.student,
            'current_language': language,
        }
        
        return render(request, 'staff/official_certificate_preview.html', context)
        
    except Exception as e:
        logger.error(f"Error in certificate preview: {e}")
        messages.error(request, 'Error loading certificate.')
        return redirect('certificate_student_list')

@login_required
@user_passes_test(staff_check, login_url='/staff/login/')
def download_official_certificate_pdf(request, certificate_id, language='ar'):
    """Download official certificate as PDF"""
    try:
        certificate = get_object_or_404(Certificate, pk=certificate_id)
        return generate_official_certificate_pdf(certificate, language)
        
    except Exception as e:
        logger.error(f"Error downloading certificate: {e}")
        messages.error(request, 'Error downloading certificate.')
        return redirect('official_certificate_preview', certificate_id=certificate_id)

def generate_official_certificate_pdf(certificate, language='ar'):
    """Generate official certificate PDF"""
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        
        # Simple certificate for now
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, 750, "Official School Certificate")
        
        p.setFont("Helvetica", 12)
        p.drawString(100, 700, f"Student: {certificate.student.get_full_name()}")
        p.drawString(100, 670, f"Grade: {certificate.student.get_grade_level_display()}")
        p.drawString(100, 640, f"Student ID: {certificate.student.student_id}")
        p.drawString(100, 610, f"Issue Date: {certificate.issue_date}")
        
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, 550, "Trust Academy - Boumerdes")
        p.drawString(100, 520, "License: 2491/21")
        
        p.save()
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        filename = f"certificate_{certificate.student.student_id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        logger.error(f"Error generating PDF: {e}")
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)

# Make sure this is the VERY LAST LINE - no code after this!
