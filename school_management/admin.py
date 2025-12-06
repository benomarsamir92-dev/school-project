from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import HttpResponse
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db import models

# Import from separate modules
from .models import Student, Staff, ClassRoom, Subject, Payment, Attendance, Grade, InventoryItem, SchoolConfig, StudentCertificate, Schedule, Payroll
from .whatsapp_utils import *
from .documents import *
from .certificates import generate_certificate_for_admin
from dateutil.relativedelta import relativedelta
from datetime import datetime
from django.db.models import Avg

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import mm
import io
import os
from django import forms
from decimal import Decimal

# ==============================
# Store original get_urls and override with custom URLs
# ==============================
original_get_urls = admin.site.get_urls

def custom_get_urls():
    urls = original_get_urls()
    custom_urls = [
        #path('documents/', admin.site.admin_view(admin_document_generator), name='document_generator'),

        # Student lists
        path('documents/students/<int:class_id>/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_student_list), name='generate_student_list'),
        path('documents/students/all/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_student_list), name='generate_all_students'),

        # Staff directory
        path('documents/staff/all/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_staff_list), name='generate_staff_list'),

        # NEW DOCUMENT URLs
        path('documents/parent-invitation/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_parent_invitation), name='generate_parent_invitation'),
        path('documents/report-cards/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_report_cards), name='generate_report_cards'),
        path('documents/payslips/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_payslips), name='generate_payslips'),
        path('documents/certificates/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_certificates), name='generate_certificates'),
        path('documents/fee-statements/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_fee_statements), name='generate_fee_statements'),
        path('documents/id-cards/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_id_cards), name='generate_id_cards'),

        # Additional URLs
        path('documents/class-grades/<int:class_id>/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_student_list), name='generate_class_grades'),
        path('documents/calendar/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_calendar), name='generate_calendar'),
        path('documents/schedules/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_schedules), name='generate_schedules'),
        path('documents/attendance-certificates/<str:format_type>/<str:language>/', admin.site.admin_view(admin_generate_attendance_certificates), name='generate_attendance_certificates'),
    ]
    return custom_urls + urls

admin.site.get_urls = custom_get_urls

# Set custom admin index template to show documents
#admin.site.index_template = 'admin/custom_index.html'

# Custom admin site headers with translations
admin.site.site_title = _("Trust Academy Administration")
admin.site.site_header = _("Trust Academy School Management")
admin.site.index_title = _("Dashboard")

# ==============================
# Mixin Classes for Common Functionality
# ==============================

class WhatsAppMixin:
    """Mixin for WhatsApp-related functionality"""
    
    def whatsapp_link(self, phone_number, message, button_text):
        """Generate WhatsApp link HTML"""
        if not phone_number:
            return _("No phone")
        
        whatsapp_url = generate_whatsapp_link(phone_number, message)
        return format_html(
            '<a href="{}" target="_blank" style="background-color:#25D366;color:white;padding:5px 10px;'
            'text-decoration:none;border-radius:5px;font-size:12px;">?? {}</a>',
            whatsapp_url, button_text
        )

class ExportMixin:
    """Mixin for export functionality"""
    
    def export_as_csv(self, request, queryset):
        """Export selected items as CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(
            self.model._meta.verbose_name_plural
        )
        
        writer = csv.writer(response)
        
        # Write headers
        field_names = [field.name for field in self.model._meta.fields]
        writer.writerow(field_names)
        
        # Write data
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])
        
        return response
    export_as_csv.short_description = _("Export selected as CSV")

# ==============================
# Custom Admin Classes
# ==============================

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin, WhatsAppMixin):
    list_display = ['student_id', 'get_full_name', 'get_full_name_arabic', 'grade_level', 'parent_phone', 'whatsapp_link_column', 'enrollment_date', 'is_active']
    list_filter = ['grade_level', 'is_active', 'enrollment_date']
    search_fields = ['first_name', 'last_name', 'first_name_arabic', 'last_name_arabic', 'student_id', 'parent_phone', 'grade_level']
    list_editable = ['is_active']
    actions = ['send_welcome_whatsapp', 'send_custom_message_whatsapp', 'send_meeting_message', 'export_students_html']
    
    # Define the fieldsets to organize the form
    fieldsets = (
        ('Basic Information', {
            'fields': ('student_id', 'first_name', 'last_name', 'first_name_arabic', 'last_name_arabic', 'gender', 'date_of_birth')
        }),
        ('Academic Information', {
            'fields': ('class_room', 'grade_level', 'enrollment_date', 'is_active')
        }),
        ('Parent Information', {
            'fields': ('parent_name', 'parent_phone', 'parent_email')
        }),
    )
    
    class Meta:
        verbose_name = _("Student")
        verbose_name_plural = _("Students")
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['student_id'].label = _('Student ID')
        form.base_fields['first_name'].label = _('First name')
        form.base_fields['last_name'].label = _('Last name')
        form.base_fields['first_name_arabic'].label = _('First name in Arabic')
        form.base_fields['last_name_arabic'].label = _('Last name in Arabic')
        form.base_fields['gender'].label = _('Gender')
        form.base_fields['date_of_birth'].label = _('Date of birth')
        form.base_fields['class_room'].label = _('Class room')
        form.base_fields['grade_level'].label = _('Grade level')
        form.base_fields['parent_name'].label = _('Parent name')
        form.base_fields['parent_phone'].label = _('Parent phone')
        form.base_fields['parent_email'].label = _('Parent email')
        form.base_fields['enrollment_date'].label = _('Enrollment date')
        form.base_fields['is_active'].label = _('Is active')
        return form

    def get_full_name_arabic(self, obj):
        return obj.get_full_name_arabic()
    get_full_name_arabic.short_description = _('الاسم الكامل بالعربية')
    get_full_name_arabic.admin_order_field = 'last_name_arabic'

    def whatsapp_link_column(self, obj):
        if obj.parent_phone:
            default_message = _("Hello, this message is regarding your child {} from school.").format(obj.get_full_name())
            return self.whatsapp_link(obj.parent_phone, default_message, _('WhatsApp'))
        return _("No phone")
    whatsapp_link_column.short_description = _('WhatsApp')

    def send_welcome_whatsapp(self, request, queryset):
        success_count = 0
        for student in queryset:
            if student.parent_phone and send_welcome_message_whatsapp(student):
                success_count += 1
        self.message_user(request, _("Successfully sent {} welcome messages via WhatsApp").format(success_count))
    send_welcome_whatsapp.short_description = _("📱 Send welcome WhatsApp messages")

    def send_custom_message_whatsapp(self, request, queryset):
        for student in queryset:
            if student.parent_phone:
                default_message = _("Hello, this message is regarding your child {} from school.").format(student.get_full_name())
                whatsapp_url = generate_whatsapp_link(student.parent_phone, default_message)
                self.message_user(request, _("WhatsApp link for {}: {}").format(student.get_full_name(), whatsapp_url))
    send_custom_message_whatsapp.short_description = _("📱 Generate WhatsApp links")

    def send_meeting_message(self, request, queryset):
        """Create WhatsApp broadcast with direct clickable links"""
        phone_numbers = []
        student_list = []
        
        for student in queryset:
            if student.parent_phone:
                # Clean phone number format
                clean_phone = student.parent_phone.replace('+', '').replace(' ', '')
                phone_numbers.append(clean_phone)
                student_list.append(f"{student.get_full_name()} - {student.parent_phone}")
        
        if phone_numbers:
            # Create the message template in French
            message_template = """Cher parent,

Nous aimerions vous inviter à une réunion parents-professeurs pour discuter des progrès de votre enfant.

Date : [Veuillez spécifier la date]
Heure : [Veuillez spécifier l'heure]  
Lieu : École Trust Academy

Veuillez confirmer votre présence. Merci.

Cordialement,
L'Administration Scolaire
Trust Academy"""
            
            # URL encode the message
            import urllib.parse
            encoded_message = urllib.parse.quote(message_template)
            
            # Create WhatsApp link
            whatsapp_url = f"https://wa.me/?text={encoded_message}"
            
            instructions = format_html("""
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #ddd;">
                <h3 style="color: #25D366; margin-top: 0;">📋 Invitation de Réunion WhatsApp</h3>
                
                <p><strong>Étape 1 :</strong> Cliquez sur ce bouton pour ouvrir WhatsApp avec le message prêt :</p>
                <p><a href="{}" target="_blank" style="background: #25D366; color: white; padding: 12px 20px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold; font-size: 16px;">📱 OUVIR WHATSAPP & ENVOYER LE MESSAGE</a></p>
                
                <p><strong>Étape 2 :</strong> Choisissez où envoyer :</p>
                <ul>
                    <li>💚 <strong>Envoyez d'abord à vous-même</strong> (pour sauvegarder le modèle)</li>
                    <li>👥 <strong>Créez un groupe</strong> avec ces {} parents</li>
                    <li>📢 <strong>Utilisez la diffusion</strong> pour des messages individuels</li>
                </ul>
                
                <div style="background: white; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <strong>Numéros des parents à ajouter au groupe :</strong><br>
                    {}
                </div>
                
                <div style="background: #e8f5e8; padding: 15px; border-radius: 5px;">
                    <strong>Parents Sélectionnés ({}/{}):</strong><br>
                    {}
                </div>
            </div>
            """, 
            whatsapp_url,
            len(phone_numbers),
            '<br>'.join([f"• {phone}" for phone in phone_numbers]),
            len(phone_numbers),
            len(queryset),
            '<br>'.join([f"• {item}" for item in student_list])
            )
            
            self.message_user(request, instructions)
        else:
            self.message_user(request, "❌ Aucun numéro de téléphone de parent trouvé", level='warning')
    send_meeting_message.short_description = "📅 Envoyer l'invitation de réunion"

    def export_students_html(self, request, queryset):
        """Export selected students list as HTML (Simple version)"""
        from django.http import HttpResponse
        from datetime import datetime
        
        current_date = datetime.now().strftime('%Y/%m/%d')
        total_students = len(queryset)
        active_students = queryset.filter(is_active=True).count()
        
        html_content = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <title>قائمة الطلاب</title>
            <style>
                @media print {{
                    @page {{ margin: 15mm; }}
                    body {{ margin: 0; background: white; }}
                    .no-print {{ display: none; }}
                }}
                body {{
                    font-family: 'Arial', Tahoma, sans-serif;
                    margin: 20px;
                    padding: 0;
                    direction: rtl;
                    text-align: right;
                }}
                .header {{
                    text-align: center;
                    border-bottom: 2px solid #1a237e;
                    padding-bottom: 15px;
                    margin-bottom: 20px;
                }}
                .title {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #1a237e;
                    margin-bottom: 10px;
                }}
                .subtitle {{
                    font-size: 16px;
                    color: #5f6368;
                    margin-bottom: 5px;
                }}
                .student-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                .student-table th {{
                    background: #1a237e;
                    color: white;
                    padding: 12px;
                    text-align: right;
                    border: 1px solid #ddd;
                }}
                .student-table td {{
                    padding: 10px;
                    border: 1px solid #ddd;
                    text-align: right;
                }}
                .student-table tr:nth-child(even) {{
                    background: #f8f9fa;
                }}
                .footer {{
                    text-align: center;
                    margin-top: 30px;
                    padding-top: 15px;
                    border-top: 1px solid #ddd;
                    color: #6c757d;
                    font-size: 14px;
                }}
                .info-row {{
                    margin: 10px 0;
                    padding: 8px;
                    background: #e3f2fd;
                    border-right: 3px solid #1976d2;
                }}
                .print-btn {{
                    background: #1a237e;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                    margin: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="no-print">
                <button class="print-btn" onclick="window.print()">🖨️ طباعة القائمة</button>
                <button class="print-btn" onclick="window.close()">❌ إغلاق</button>
            </div>

            <div class="header">
                <div class="title">قائمة الطلاب - Trust Academy</div>
                <div class="subtitle">تاريخ التصدير: {current_date}</div>
                <div class="subtitle">إجمالي الطلاب: {total_students} | الطلاب النشطين: {active_students}</div>
            </div>
            
            <div class="info-row">
                <strong>ملخص:</strong> تم تصدير قائمة تحتوي على {total_students} طالب
            </div>
            
            <table class="student-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>رقم الطالب</th>
                        <th>الاسم الكامل</th>
                        <th>الاسم بالعربية</th>
                        <th>المستوى</th>
                        <th>الصف</th>
                        <th>ولي الأمر</th>
                        <th>الهاتف</th>
                        <th>الحالة</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for i, student in enumerate(queryset, 1):
            status = "نشط" if student.is_active else "غير نشط"
            class_room = student.class_room.name if student.class_room else "-"
            parent_name = student.parent_name or "-"
            parent_phone = student.parent_phone or "-"
            arabic_name = student.get_full_name_arabic() or "-"
            
            html_content += f"""
                    <tr>
                        <td>{i}</td>
                        <td>{student.student_id}</td>
                        <td>{student.last_name} {student.first_name}</td>
                        <td>{arabic_name}</td>
                        <td>{student.grade_level}</td>
                        <td>{class_room}</td>
                        <td>{parent_name}</td>
                        <td>{parent_phone}</td>
                        <td>{status}</td>
                    </tr>
            """
        
        html_content += f"""
                </tbody>
            </table>
            
            <div class="footer">
                Trust Academy School - {current_date}<br>
                تم إنشاء هذا التقرير تلقائياً من نظام إدارة المدرسة
            </div>
        </body>
        </html>
        """
        
        response = HttpResponse(html_content, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="students_list_{current_date}.html"'
        return response
    export_students_html.short_description = _("📄 Export students list")

@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'get_full_name', 'position', 'phone', 'hire_date', 'is_active']
    list_filter = ['position', 'is_active', 'hire_date', 'gender', 'family_situation']
    search_fields = [
        'first_name', 'last_name', 'first_name_arabic', 'last_name_arabic', 
        'staff_id', 'phone', 'social_security_number', 'cin_number'
    ]
    actions = ['generate_french_work_certificate', 'generate_arabic_work_certificate']
    
    # Complete fieldsets with all payroll information
    fieldsets = (
        ('Informations Personnelles', {
            'fields': (
                'staff_id',
                ('first_name', 'last_name'),
                ('first_name_arabic', 'last_name_arabic'),
                'position',
                'gender',
                ('date_of_birth', 'place_of_birth'),
                'nationality',
                'cin_number',
                'family_situation',
                'number_of_children'
            )
        }),
        ('Informations de Contact', {
            'fields': (
                'phone',
                'emergency_phone',
                'email',
                'address',
                'city'
            )
        }),
        ('Informations Professionnelles', {
            'fields': (
                'hire_date',
                'department',
                'qualification',
                'salary',
                'is_active'
            )
        }),
        ('Informations Administratives (Paie)', {
            'fields': (
                'social_security_number',
                'bank_name',
                'bank_account_number',
            )
        }),
        ('Notes et Informations Supplémentaires', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    class Meta:
        verbose_name = _("Staff")
        verbose_name_plural = _("Staff")
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Set field labels in French
        field_labels = {
            'staff_id': 'Matricule',
            'first_name': 'Prénom (Latin)',
            'last_name': 'Nom (Latin)',
            'first_name_arabic': 'Prénom (Arabe)',
            'last_name_arabic': 'Nom (Arabe)',
            'position': 'Poste',
            'gender': 'Genre',
            'date_of_birth': 'Date de naissance',
            'place_of_birth': 'Lieu de naissance',
            'nationality': 'Nationalité',
            'cin_number': 'Numéro CIN',
            'family_situation': 'Situation familiale',
            'number_of_children': "Nombre d'enfants",
            'phone': 'Téléphone',
            'emergency_phone': 'Téléphone d\'urgence',
            'email': 'Email',
            'address': 'Adresse complète',
            'city': 'Ville',
            'hire_date': 'Date d\'embauche',
            'department': 'Département',
            'qualification': 'Qualification',
            'salary': 'Salaire de base (DZD)',
            'is_active': 'Actif',
            'social_security_number': 'Numéro de sécurité sociale',
            'bank_name': 'Nom de la banque',
            'bank_account_number': 'Numéro de compte bancaire',
            'notes': 'Notes',
        }
        
        for field_name, label in field_labels.items():
            if field_name in form.base_fields:
                form.base_fields[field_name].label = label
                
                # Add help text for important fields
                if field_name == 'social_security_number':
                    form.base_fields[field_name].help_text = 'Numéro à 15 chiffres'
                elif field_name == 'bank_account_number':
                    form.base_fields[field_name].help_text = 'Numéro RIB ou IBAN'
                elif field_name == 'date_of_birth':
                    form.base_fields[field_name].help_text = 'Format: JJ/MM/AAAA'
                elif field_name == 'cin_number':
                    form.base_fields[field_name].help_text = "Carte d'Identité Nationale"
        
        return form

    def get_full_name(self, obj):
        arabic_name = obj.get_full_name_arabic()
        if arabic_name:
            return f"{obj.first_name} {obj.last_name} / {arabic_name}"
        return f"{obj.first_name} {obj.last_name}"
    get_full_name.short_description = "Nom complet"
    
    # FRENCH – PERFECTLY CENTERED (NO MORE LEFT/RIGHT MARGIN DIFFERENCE)
    def generate_french_work_certificate(self, request, queryset):
        current_date = datetime.now().strftime('%d/%m/%Y')
        html = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Attestation de Travail</title>
    <style>
        @page { size: A4; margin: 0; }
        html, body { height: 297mm; margin: 0; padding: 0; background: #f9f9f9; }
        @media print {
            .print-btn { display: none !important; }
            body { background: white; }
        }
        .print-btn {
            position: fixed; top: 15px; right: 20px; z-index: 9999;
            background: #1a237e; color: white; padding: 12px 30px; border: none;
            border-radius: 8px; cursor: pointer; font-size: 16px;
        }
        /* THIS IS THE FIX → forces perfect centering */
        .page {
            width: 210mm;
            height: 297mm;
            margin-left: 20mm;
            margin-right: -20mm;
            /* margin: 0 auto*/
            background: white;
            position: relative;
            box-sizing: border-box;
            border: 4px solid #1a237e;
            top: 13mm; /* ← THIS MOVES IT DOWN */
            padding: 28mm 22mm; /* balanced padding */
            page-break-after: always;
        }
        .watermark { position: absolute; top:50%; left:50%; transform:translate(-50%,-50%) rotate(-45deg); font-size:100px; color:rgba(0,0,0,0.03); font-weight:bold; pointer-events:none; }
        .stamp { position: absolute; bottom:70px; left:60px; font-size:90px; color:#d32f2f; opacity:0.15; transform:rotate(-20deg); font-weight:bold; }
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Imprimer</button>
"""
        for i, staff in enumerate(queryset):
            duration = relativedelta(datetime.now().date(), staff.hire_date)
            years, months = duration.years, duration.months
            seniority = f"{years} an{'s' if years > 1 else ''}" + (f" et {months} mois" if months else "") or "Moins d'un mois"
            
            # Get additional information if available
            date_of_birth = staff.date_of_birth.strftime('%d/%m/%Y') if staff.date_of_birth else "Non spécifié"
            place_of_birth = staff.place_of_birth or "Non spécifié"
            cin_number = staff.cin_number or "Non spécifié"
            
            html += f"""
    <div class="page">
        <div class="watermark">TRUST ACADEMY</div>
        <div class="stamp">OFFICIEL</div>
        <div style="text-align:center; border-bottom:4px solid #1a237e; padding-bottom:20px; margin-bottom:30px;">
            <div style="font-size:30px; font-weight:bold; color:#1a237e;">TRUST ACADEMY</div>
            <div style="font-size:16px; color:#555; margin:8px 0;">École Privée Agréée • Boumerdès, Algérie</div>
            <div style="font-size:15px; color:#555;">Licence N° 2491/21</div>
        </div>
        <h1 style="text-align:center; color:#c62828; font-size:28px; text-decoration:underline; margin:40px 0;">
            ATTESTATION DE TRAVAIL
        </h1>
        <p style="font-size:17px; line-height:2; text-align:justify;">
            Le Directeur de l'établissement <strong>TRUST ACADEMY</strong>, sis à Boumerdès, Algérie,<br>
            <strong>ATTESTE PAR LA PRÉSENTE</strong> que :
        </p>
        <div style="background:#e3f2fd; padding:25px; border-left:6px solid #1976d2; border-radius:10px; margin:30px 0;">
            <div style="display:flex; margin:12px 0; font-size:16px;">
                <div style="font-weight:bold; color:#1a237e; width:200px;">Nom et Prénom :</div>
                <div style="font-weight:bold;">{staff.last_name.upper()} {staff.first_name}</div>
            </div>
            <div style="display:flex; margin:12px 0; font-size:16px;">
                <div style="font-weight:bold; color:#1a237e; width:200px;">Date de naissance :</div>
                <div style="font-weight:bold;">{date_of_birth}</div>
            </div>
            <div style="display:flex; margin:12px 0; font-size:16px;">
                <div style="font-weight:bold; color:#1a237e; width:200px;">Lieu de naissance :</div>
                <div style="font-weight:bold;">{place_of_birth}</div>
            </div>
            <div style="display:flex; margin:12px 0; font-size:16px;">
                <div style="font-weight:bold; color:#1a237e; width:200px;">N° CIN :</div>
                <div style="font-weight:bold;">{cin_number}</div>
            </div>
            <div style="display:flex; margin:12px 0; font-size:16px;">
                <div style="font-weight:bold; color:#1a237e; width:200px;">Fonction :</div>
                <div style="font-weight:bold;">{staff.get_position_display()}</div>
            </div>
            <div style="display:flex; margin:12px 0; font-size:16px;">
                <div style="font-weight:bold; color:#1a237e; width:200px;">Date d'embauche :</div>
                <div style="font-weight:bold;">{staff.hire_date.strftime('%d/%m/%Y')}</div>
            </div>
            <div style="display:flex; margin:12px 0; font-size:16px;">
                <div style="font-weight:bold; color:#1a237e; width:200px;">Ancienneté :</div>
                <div style="font-weight:bold;">{seniority}</div>
            </div>
        </div>
        <p style="font-size:17px; line-height:2; text-align:justify;">
            travaille au sein de notre établissement en qualité de <strong>{staff.get_position_display()}</strong> depuis le <strong>{staff.hire_date.strftime('%d/%m/%Y')}</strong>.<br><br>
            La présente attestation est délivrée à l'intéressé(e) pour servir et valoir ce que de droit.
        </p>
        <div style="background:#f3e5f5; padding:20px; border-left:6px solid #8e24aa; border-radius:10px; margin-top:40px; font-style:italic; font-size:16px;">
            Fait à Boumerdès, le <strong>{current_date}</strong>
        </div>
        <div style="text-align:right; margin-top:70px;">
            <div style="border-top:3px solid #000; width:320px; margin:40px 0 15px;"></div>
            <div style="font-weight:bold; font-size:18px;">Le Directeur</div>
            <div style="font-weight:bold; font-size:16px;">Trust Academy</div>
        </div>
    </div>
"""
            if i < len(queryset) - 1:
                html += '<div style="page-break-before: always;"></div>'
        html += "</body></html>"
        
        response = HttpResponse(html, content_type='text/html; charset=utf-8')
        
        if len(queryset) == 1:
            staff = queryset.first()
            filename = f"Attestation_Travail_{staff.last_name}_{staff.first_name}.html"
        else:
            filename = f"Attestations_Travail_{current_date.replace('/', '-')}.html"
            
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    generate_french_work_certificate.short_description = "Attestation Français"
    
    # ARABIC – SAME PERFECT CENTERING FIX
    def generate_arabic_work_certificate(self, request, queryset):
        current_date = datetime.now().strftime('%d/%m/%Y')
        html = """<!DOCTYPE html>
<html dir="rtl" lang="ar">
<head>
    <meta charset="UTF-8">
    <title>شهادة عمل</title>
    <style>
        @page { size: A4; margin: 0; }
        html, body { height: 297mm; margin: 0; padding: 0; background: #f9f9f9; }
        @media print {
            .print-btn { display: none !important; }
            body { background: white; }
        }
        .print-btn {
            position: fixed; top: 15px; left: 20px; z-index: 9999;
            background: #1a237e; color: white; padding: 12px 30px; border: none;
            border-radius: 8px; cursor: pointer; font-size: 16px;
        }
        .page {
            width: 194mm;
            height: 290mm;
            margin-left: +2mm;
            margin-right: -0mm;
            /* margin: 0 auto;*/
            background: white;
            position: relative;
            box-sizing: border-box;
            border: 4px solid #1a237e;
            top: 5mm; /* ← THIS MOVES IT DOWN */
            padding: 28mm 22mm;
            padding-top: 10mm !important; /* ← moves ALL text UP inside the blue frame */
            page-break-after: always;
        }
        .watermark { position: absolute; top:50%; left:50%; transform:translate(-50%,-50%) rotate(45deg); font-size:100px; color:rgba(0,0,0,0.03); font-weight:bold; pointer-events:none; }
        .stamp { position: absolute; bottom:70px; right:60px; font-size:90px; color:#d32f2f; opacity:0.15; transform:rotate(20deg); font-weight:bold; }
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">طباعة الشهادة</button>
"""
        for i, staff in enumerate(queryset):
            duration = relativedelta(datetime.now().date(), staff.hire_date)
            years, months = duration.years, duration.months
            seniority = f"{years} سنة" + (f" و {months} شهر" if months else "") if years or months else "أقل من شهر"
            
            # Get additional information if available
            date_of_birth = staff.date_of_birth.strftime('%d/%m/%Y') if staff.date_of_birth else "غير محدد"
            place_of_birth = staff.place_of_birth or "غير محدد"
            cin_number = staff.cin_number or "غير محدد"
            arabic_name = staff.get_full_name_arabic() or f"{staff.first_name} {staff.last_name}"
            
            html += f"""
    <div class="page">
        <div class="watermark">تراست أكاديمي</div>
        <div class="stamp">رسمي</div>
        <div style="text-align:center; border-bottom:4px solid #1a237e; padding-bottom:20px; margin-bottom:30px;">
            <div style="font-size:30px; font-weight:bold; color:#1a237e;">مدرسة تراست أكاديمي</div>
            <div style="font-size:16px; color:#555; margin:8px 0;">مدرسة خاصة مرخصة • بومرداس، الجزائر</div>
            <div style="font-size:15px; color:#555;">رخصة رقم 2491/21</div>
        </div>
        <h1 style="text-align:center; color:#c62828; font-size:28px; text-decoration:underline; margin:40px 0;">
            شهادة عمل
        </h1>
        <p style="font-size:18px; line-height:2.2; text-align:justify;">
            يشهد مدير مدرسة <strong>تراست أكاديمي</strong> الكائنة ببومرداس - الجزائر<br>
            <strong>بأن:</strong>
        </p>
        <div style="background:#e3f2fd; padding:25px; border-right:6px solid #1976d2; border-radius:10px; margin:30px 0;">
            <div style="display:flex; justify-content:flex-start; margin:15px 0; font-size:17px;">
                <div style="width:180px; font-weight:bold; color:#1a237e;">الاسم واللقب:</div>
                <div style="flex:1; text-align:right; font-weight:bold;">{arabic_name}</div>
            </div>
            <div style="display:flex; justify-content:flex-start; margin:15px 0; font-size:17px;">
                <div style="width:180px; font-weight:bold; color:#1a237e;">تاريخ الميلاد:</div>
                <div style="flex:1; text-align:right; font-weight:bold;">{date_of_birth}</div>
            </div>
            <div style="display:flex; justify-content:flex-start; margin:15px 0; font-size:17px;">
                <div style="width:180px; font-weight:bold; color:#1a237e;">مكان الميلاد:</div>
                <div style="flex:1; text-align:right; font-weight:bold;">{place_of_birth}</div>
            </div>
            <div style="display:flex; justify-content:flex-start; margin:15px 0; font-size:17px;">
                <div style="width:180px; font-weight:bold; color:#1a237e;">رقم الهوية:</div>
                <div style="flex:1; text-align:right; font-weight:bold;">{cin_number}</div>
            </div>
            <div style="display:flex; justify-content:flex-start; margin:15px 0; font-size:17px;">
                <div style="width:180px; font-weight:bold; color:#1a237e;">المنصب:</div>
                <div style="flex:1; text-align:right; font-weight:bold;">{staff.get_position_display()}</div>
            </div>
            <div style="display:flex; justify-content:flex-start; margin:15px 0; font-size:17px;">
                <div style="width:180px; font-weight:bold; color:#1a237e;">تاريخ التعيين:</div>
                <div style="flex:1; text-align:right; font-weight:bold;">{staff.hire_date.strftime('%d/%m/%Y')}</div>
            </div>
            <div style="display:flex; justify-content:flex-start; margin:15px 0; font-size:17px;">
                <div style="width:180px; font-weight:bold; color:#1a237e;">مدة الخدمة:</div>
                <div style="flex:1; text-align:right; font-weight:bold;">{seniority}</div>
            </div>
        </div>
        <p style="font-size:18px; line-height:2.2; text-align:justify;">
            يعمل لدينا بصفة <strong>{staff.get_position_display()}</strong> منذ <strong>{staff.hire_date.strftime('%d/%m/%Y')}</strong>.<br><br>
            حررت هذه الشهادة للمعني بالأمر لتقديمها حيث يلزم.
        </p>
        <div style="background:#f3e5f5; padding:20px; border-right:6px solid #8e24aa; border-radius:10px; margin-top:40px; font-style:italic; font-size:17px;">
            حررت ببومرداس، في <strong>{current_date}</strong>
        </div>
        <div style="text-align:left; margin-top:70px;">
            <div style="border-top:3px solid #000; width:320px; margin:40px 0 15px auto;"></div>
            <div style="font-weight:bold; font-size:18px;">المدير</div>
            <div style="font-weight:bold; font-size:16px;">تراست أكاديمي</div>
        </div>
    </div>
"""
            if i < len(queryset) - 1:
                html += '<div style="page-break-before: always;"></div>'
        html += "</body></html>"
        
        response = HttpResponse(html, content_type='text/html; charset=utf-8')
        
        if len(queryset) == 1:
            staff = queryset.first()
            filename = f"شهادة_عمل_{staff.last_name}_{staff.first_name}.html"
        else:
            filename = f"شهادات_عمل_{current_date.replace('/', '-')}.html"
            
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    generate_arabic_work_certificate.short_description = "شهادة عمل (عربي)"


@admin.register(ClassRoom)
class ClassRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'grade_level', 'section', 'teacher', 'room_number', 'capacity', 'current_student_count']  # FIXED: 'grade_level' instead of 'get_grade_level_display'
    list_filter = ['grade_level']
    search_fields = ['name', 'room_number', 'teacher__first_name', 'teacher__last_name', 'grade_level']
    
    class Meta:
        verbose_name = _("Class Room")
        verbose_name_plural = _("Class Rooms")
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['name'].label = _('Name')
        form.base_fields['grade_level'].label = _('Grade level')
        form.base_fields['section'].label = _('Section')
        form.base_fields['teacher'].label = _('Teacher')
        form.base_fields['room_number'].label = _('Room number')
        form.base_fields['capacity'].label = _('Capacity')
        form.base_fields['is_active'].label = _('Is active')
        return form

    def current_student_count(self, obj):
        return obj.students.count()
    current_student_count.short_description = _("Student Count")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'grade_level', 'teacher_name_username', 'is_active']
    
    def get_form(self, request, obj=None, **kwargs):
        from django import forms
        from django.contrib.auth.models import User
        from .models import Subject
        
        class SubjectForm(forms.ModelForm):
            teacher = forms.ModelChoiceField(
                queryset=User.objects.filter(is_active=True),
                required=True,  # REQUIRED IN FORM ONLY
                widget=forms.Select,
                label="Teacher *",
                help_text="<span style='color: red;'>Required:</span> Format: Teacher Name (+username)"
            )
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if 'teacher' in self.fields:
                    self.fields['teacher'].label_from_instance = lambda obj: (
                        f"{obj.get_full_name()} (+{obj.username})" 
                        if obj.get_full_name() 
                        else f"{obj.username}"
                    )
            
            def clean(self):
                """Custom validation - teacher is required"""
                cleaned_data = super().clean()
                teacher = cleaned_data.get('teacher')
                
                if not teacher:
                    self.add_error('teacher', 'You must select a teacher for this subject.')
                
                return cleaned_data
            
            class Meta:
                model = Subject
                fields = '__all__'
        
        return SubjectForm
    
    # Custom save to ensure teacher is set
    def save_model(self, request, obj, form, change):
        if not obj.teacher:
            from django.contrib import messages
            messages.error(request, 'Error: Teacher is required.')
            return  # Don't save
        super().save_model(request, obj, form, change)
    
    def teacher_name_username(self, obj):
        if obj.teacher:
            full_name = obj.teacher.get_full_name()
            if full_name:
                return f"{full_name} (+{obj.teacher.username})"
            return f"{obj.teacher.username}"
        return "—"
    
    teacher_name_username.short_description = 'Teacher'
    teacher_name_username.admin_order_field = 'teacher__last_name'
    

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin, WhatsAppMixin):
    list_display = ['student', 'payment_type', 'amount', 'due_date', 'paid_date', 'status', 'receipt_number', 'whatsapp_link_column']
    list_filter = ['payment_type', 'status', 'due_date']
    search_fields = ['student__first_name', 'student__last_name', 'receipt_number']
    list_editable = ['status']
    actions = ['send_fee_reminders_whatsapp']
    change_form_template = 'admin/school_management/payment/select_level.html'
    
    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
    
    def add_view(self, request, form_url='', extra_context=None):
        # Custom add view that includes level information
        extra_context = extra_context or {}
        
        # Get available levels for the filter
        from .models import Student
        levels = Student.objects.filter(is_active=True).values_list('grade_level', flat=True).distinct().order_by('grade_level')
        extra_context['available_levels'] = levels
        
        # Get current level from request
        current_level = request.GET.get('level')
        if current_level:
            extra_context['current_level'] = current_level
        
        return super().add_view(request, form_url, extra_context=extra_context)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Filter students by level if level parameter is provided
        level = request.GET.get('level')
        if level and 'student' in form.base_fields:
            form.base_fields['student'].queryset = form.base_fields['student'].queryset.filter(
                grade_level=level, is_active=True
            )
            # Update help text to show filtering is active
            form.base_fields['student'].help_text = _('Showing students from level: {}').format(level)
        
        form.base_fields['student'].label = _('Student')
        form.base_fields['payment_type'].label = _('Payment type')
        form.base_fields['amount'].label = _('Amount')
        form.base_fields['due_date'].label = _('Due date')
        form.base_fields['paid_date'].label = _('Paid date')
        form.base_fields['status'].label = _('Status')
        form.base_fields['receipt_number'].label = _('Receipt number')
        return form

    def whatsapp_link_column(self, obj):
        if obj.student.parent_phone:
            message = _("Reminder: {} fee of {} DZD for {} is {}. Due: {}").format(
                obj.get_payment_type_display(), 
                obj.amount, 
                obj.student.get_full_name(), 
                obj.get_status_display(), 
                obj.due_date
            )
            return self.whatsapp_link(obj.student.parent_phone, message, _('Remind'))
        return _("No phone")
    whatsapp_link_column.short_description = _('Remind')

    def send_fee_reminders_whatsapp(self, request, queryset):
        success_count = 0
        for payment in queryset:
            if payment.status in ['pending', 'overdue'] and payment.student.parent_phone and send_fee_reminder_whatsapp(payment):
                success_count += 1
        self.message_user(request, _("Successfully sent {} fee reminders via WhatsApp").format(success_count))
    send_fee_reminders_whatsapp.short_description = _("?? Send WhatsApp fee reminders")

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin, WhatsAppMixin):
    list_display = ['student', 'date', 'status', 'notes', 'whatsapp_link_column']
    list_filter = ['date', 'status']
    search_fields = ['student__first_name', 'student__last_name']
    actions = ['send_attendance_notifications_whatsapp']
    change_form_template = 'admin/school_management/attendance/select_level.html'
    
    class Meta:
        verbose_name = _("Attendance")
        verbose_name_plural = _("Attendance")
    
    def add_view(self, request, form_url='', extra_context=None):
        # Custom add view that includes level information
        extra_context = extra_context or {}
        
        # Get available levels for the filter
        from .models import Student
        levels = Student.objects.filter(is_active=True).values_list('grade_level', flat=True).distinct().order_by('grade_level')
        extra_context['available_levels'] = levels
        
        # Get current level from request
        current_level = request.GET.get('level')
        if current_level:
            extra_context['current_level'] = current_level
        
        return super().add_view(request, form_url, extra_context=extra_context)
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Filter students by level if level parameter is provided
        level = request.GET.get('level')
        if level and 'student' in form.base_fields:
            form.base_fields['student'].queryset = form.base_fields['student'].queryset.filter(
                grade_level=level, is_active=True
            )
            # Update help text to show filtering is active
            form.base_fields['student'].help_text = _('Showing students from level: {}').format(level)
        
        form.base_fields['student'].label = _('Student')
        form.base_fields['date'].label = _('Date')
        form.base_fields['status'].label = _('Status')
        form.base_fields['notes'].label = _('Notes')
        return form

    def whatsapp_link_column(self, obj):
        if obj.status in ['absent', 'late'] and obj.student.parent_phone:
            message = _("Attendance Notice: {} was {} on {}").format(
                obj.student.get_full_name(), 
                obj.get_status_display(), 
                obj.date
            )
            if obj.notes:
                message += _(". Notes: {}").format(obj.notes)
            return self.whatsapp_link(obj.student.parent_phone, message, _('Notify'))
        return "-"
    whatsapp_link_column.short_description = _('Notify')

    def send_attendance_notifications_whatsapp(self, request, queryset):
        success_count = 0
        for attendance in queryset:
            if send_attendance_notification_whatsapp(attendance):
                success_count += 1
        self.message_user(request, _("Successfully sent {} attendance notifications via WhatsApp").format(success_count))
    send_attendance_notifications_whatsapp.short_description = _("?? Send WhatsApp attendance notifications")

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin, WhatsAppMixin):
    list_display = ['student', 'get_student_level', 'subject', 'score', 'semester', 'year', 'whatsapp_link_column']
    list_filter = ['student__grade_level', 'subject', 'semester', 'year']
    search_fields = ['student__first_name', 'student__last_name', 'student__grade_level']
    actions = ['send_grade_notifications_whatsapp', 'print_grades_report_french', 'print_grades_report_arabic']
    
    # Use custom template for the add form
    add_form_template = 'admin/school_management/grade/select_level.html'
    
    class Meta:
        verbose_name = _("Grade")
        verbose_name_plural = _("Grades")
    
    def get_queryset(self, request):
        """Show only grades for subjects taught by the logged-in teacher"""
        qs = super().get_queryset(request)
        
        # If user is not a superuser/admin, filter by their assigned subjects
        if not request.user.is_superuser:
            # Get subjects assigned to this teacher (user)
            from .models import Subject
            teacher_subjects = Subject.objects.filter(teacher=request.user)
            
            # Filter grades to only show those subjects
            qs = qs.filter(subject__in=teacher_subjects)
        
        return qs
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Filter students by level if level parameter is provided
        level = request.GET.get('level')
        if level and 'student' in form.base_fields:
            form.base_fields['student'].queryset = form.base_fields['student'].queryset.filter(
                grade_level=level, is_active=True
            )
            form.base_fields['student'].help_text = _('Showing students from level: {}').format(level)
        
        # Filter subjects for teachers (non-superusers)
        if not request.user.is_superuser and 'subject' in form.base_fields:
            from .models import Subject
            # Show only subjects assigned to this teacher
            form.base_fields['subject'].queryset = Subject.objects.filter(
                teacher=request.user,
                is_active=True
            )
            form.base_fields['subject'].help_text = _('Your assigned subjects')
        
        return form
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter foreign key choices based on user permissions"""
        
        # Filter subjects for teachers
        if db_field.name == "subject" and not request.user.is_superuser:
            from .models import Subject
            kwargs["queryset"] = Subject.objects.filter(
                teacher=request.user,
                is_active=True
            ).order_by('name')
        
        # Filter students by level
        elif db_field.name == "student" and 'level' in request.GET:
            from .models import Student
            level = request.GET.get('level')
            if level:
                kwargs["queryset"] = Student.objects.filter(
                    grade_level=level,
                    is_active=True
                ).order_by('last_name', 'first_name')
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        
        # Get available levels for the filter
        from .models import Student
        levels = Student.objects.filter(is_active=True).values_list('grade_level', flat=True).distinct().order_by('grade_level')
        extra_context['available_levels'] = levels
        
        # Get current level from request
        current_level = request.GET.get('level')
        if current_level:
            extra_context['current_level'] = current_level
        
        # For teachers, show their assigned subjects
        if not request.user.is_superuser:
            from .models import Subject
            teacher_subjects = Subject.objects.filter(teacher=request.user, is_active=True)
            extra_context['teacher_subjects'] = teacher_subjects
            extra_context['subject_count'] = teacher_subjects.count()
        
        return super().add_view(request, form_url, extra_context=extra_context)
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Prevent teachers from editing grades for subjects they don't teach"""
        if not request.user.is_superuser:
            # Check if this grade belongs to a subject taught by this teacher
            from .models import Subject
            grade = self.get_object(request, object_id)
            
            if grade and grade.subject.teacher != request.user:
                from django.contrib import messages
                from django.shortcuts import redirect
                messages.error(request, _("You don't have permission to edit this grade."))
                return redirect('admin:school_management_grade_changelist')
        
        return super().change_view(request, object_id, form_url, extra_context)
    
    def get_student_level(self, obj):
        return obj.student.grade_level
    get_student_level.short_description = _('Level')
    get_student_level.admin_order_field = 'student__grade_level'
    
    # Rest of your methods remain the same...
    def whatsapp_link_column(self, obj):
        if obj.student.parent_phone:
            message = _("Grade Update: {} scored {} in {} (Semester {}, {})").format(
                obj.student.get_full_name(),
                obj.score,
                obj.subject.name,
                obj.semester,
                obj.year
            )
            return self.whatsapp_link(obj.student.parent_phone, message, _('Share'))
        return _("No phone")
    whatsapp_link_column.short_description = _('Share')

    def send_grade_notifications_whatsapp(self, request, queryset):
        success_count = 0
        for grade in queryset:
            if send_grade_notification_whatsapp(grade):
                success_count += 1
        self.message_user(request, _("Successfully sent {} grade notifications via WhatsApp").format(success_count))
    send_grade_notifications_whatsapp.short_description = _("📱 Send WhatsApp grade notifications")


    def print_grades_report_french(self, request, queryset):
        """Generate a modern HTML grades report in French"""
        from django.http import HttpResponse
        from django.db.models import Avg, Max, Min
        
        # Get unique students from the selected grades
        student_ids = queryset.values_list('student_id', flat=True).distinct()
        
        # Get students without prefetching to avoid related name issues
        students = Student.objects.filter(id__in=student_ids)
        
        html_content = """
        <!DOCTYPE html>
        <html dir="ltr" lang="fr">
        <head>
            <meta charset="UTF-8">
            <title>Bulletin de Notes</title>
            <style>
                @media print {
                    @page {
                        size: A4;
                        margin: 10mm;
                    }
                    body {
                        margin: 0 !important;
                        padding: 0 !important;
                        background: white !important;
                    }
                    .no-print {
                        display: none !important;
                    }
                    .student-report {
                        page-break-after: always;
                        margin: 0 auto !important;
                        box-shadow: none !important;
                    }
                    /* Remove headers and footers */
                    @page { margin: 0; }
                    body { margin: 1.6cm; }
                }
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 15px;
                    background: #f8f9fa;
                    color: #333;
                }
                .student-report {
                    background: white;
                    padding: 25px;
                    margin: 10px auto;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    border-radius: 8px;
                    max-width: 210mm;
                    min-height: 280mm;
                }
                .header {
                    text-align: center;
                    border-bottom: 3px solid #2c5aa0;
                    padding-bottom: 15px;
                    margin-bottom: 25px;
                }
                .school-name {
                    font-size: 24px;
                    font-weight: bold;
                    color: #2c5aa0;
                    margin-bottom: 8px;
                }
                .report-title {
                    font-size: 20px;
                    color: #555;
                    margin-bottom: 10px;
                }
                .student-info {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                    margin-bottom: 25px;
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 6px;
                }
                .info-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 6px 0;
                }
                .info-label {
                    font-weight: bold;
                    color: #555;
                }
                .info-value {
                    color: #333;
                }
                .grades-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                    font-size: 13px;
                }
                .grades-table th {
                    background: #2c5aa0;
                    color: white;
                    padding: 10px;
                    text-align: left;
                    font-weight: bold;
                }
                .grades-table td {
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                }
                .grades-table tr:nth-child(even) {
                    background: #f8f9fa;
                }
                .grade-excellent { color: #2e7d32; font-weight: bold; }
                .grade-good { color: #689f38; }
                .grade-average { color: #f57c00; }
                .grade-poor { color: #d32f2f; font-weight: bold; }
                .summary-card {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 15px;
                    border-radius: 6px;
                    margin: 15px 0;
                }
                .summary-stats {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 12px;
                    text-align: center;
                }
                .stat-item h3 {
                    margin: 0;
                    font-size: 20px;
                    font-weight: bold;
                }
                .stat-item p {
                    margin: 3px 0 0 0;
                    opacity: 0.9;
                    font-size: 14px;
                }
                .print-btn {
                    background: #2c5aa0;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 14px;
                    margin: 8px;
                }
                .no-print {
                    text-align: center;
                    margin: 15px;
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    background: white;
                    padding: 10px;
                    z-index: 1000;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .arabic-name {
                    font-family: 'Arial', Tahoma, sans-serif;
                    font-size: 14px;
                    color: #666;
                    margin-top: 3px;
                }
                .semester-title {
                    color: #2c5aa0;
                    border-bottom: 2px solid #2c5aa0;
                    padding-bottom: 6px;
                    margin: 20px 0 15px 0;
                    font-size: 16px;
                }
            </style>
        </head>
        <body>
            <div class="no-print">
                <button class="print-btn" onclick="window.print()">🖨️ Imprimer les bulletins</button>
                <button class="print-btn" onclick="window.close()">❌ Fermer</button>
            </div>
        """
        
        for i, student in enumerate(students):
            # Get grades for this student directly
            grades = Grade.objects.filter(student=student).order_by('semester', 'subject__name')
            
            # Calculate statistics
            total_grades = grades.count()
            average_score = grades.aggregate(Avg('score'))['score__avg'] or 0
            max_score = grades.aggregate(Max('score'))['score__max'] or 0
            min_score = grades.aggregate(Min('score'))['score__min'] or 0
            
            # Group grades by semester
            semesters = {}
            for grade in grades:
                if grade.semester not in semesters:
                    semesters[grade.semester] = []
                semesters[grade.semester].append(grade)
            
            html_content += f"""
            <div class="student-report">
                <div class="header">
                    <div class="school-name">TRUST ACADEMY</div>
                    <div class="report-title">Bulletin de Notes Scolaires</div>
                </div>
                
                <div class="student-info">
                    <div class="info-item">
                        <span class="info-label">Nom et Prénom:</span>
                        <span class="info-value">
                            {student.last_name} {student.first_name}
                        </span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Nom en Arabe:</span>
                        <span class="info-value">
                            {student.first_name_arabic or ''} {student.last_name_arabic or ''}
                        </span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Matricule:</span>
                        <span class="info-value">{student.student_id}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Niveau:</span>
                        <span class="info-value">{student.grade_level}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Classe:</span>
                        <span class="info-value">{student.class_room or 'N/A'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Année Scolaire:</span>
                        <span class="info-value">{timezone.now().year}-{timezone.now().year + 1}</span>
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="summary-stats">
                        <div class="stat-item">
                            <h3>{average_score:.1f}</h3>
                            <p>Moyenne Générale</p>
                        </div>
                        <div class="stat-item">
                            <h3>{max_score}</h3>
                            <p>Note Maximale</p>
                        </div>
                        <div class="stat-item">
                            <h3>{min_score}</h3>
                            <p>Note Minimale</p>
                        </div>
                    </div>
                </div>
            """
            
            # Add grades tables for each semester
            for semester, semester_grades in semesters.items():
                html_content += f"""
                <div class="semester-title">
                    Semestre {semester}
                </div>
                <table class="grades-table">
                    <thead>
                        <tr>
                            <th>Matière</th>
                            <th>Note</th>
                            <th>Appréciation</th>
                            <th>Année</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                
                for grade in semester_grades:
                    # CORRECTED: Proper grade appreciation logic for 10-point system
                    if grade.score >= 9:
                        grade_class = "grade-excellent"
                        appreciation = "Excellent"
                    elif grade.score >= 8:
                        grade_class = "grade-excellent"
                        appreciation = "Très Bien"
                    elif grade.score >= 7:
                        grade_class = "grade-good"
                        appreciation = "Bien"
                    elif grade.score >= 6:
                        grade_class = "grade-average"
                        appreciation = "Assez Bien"
                    elif grade.score >= 5:
                        grade_class = "grade-poor"
                        appreciation = "Passable"
                    else:
                        grade_class = "grade-poor"
                        appreciation = "Insuffisant"
                    
                    html_content += f"""
                        <tr>
                            <td>{grade.subject.name}</td>
                            <td class="{grade_class}">{grade.score}</td>
                            <td class="{grade_class}">{appreciation}</td>
                            <td>{grade.year}</td>
                        </tr>
                    """
                
                html_content += """
                    </tbody>
                </table>
                """
            
            # Add footer with signature area
            html_content += """
                <div style="margin-top: 40px; border-top: 1px solid #ddd; padding-top: 20px;">
                    <div style="display: flex; justify-content: space-between;">
                        <div style="text-align: center;">
                            <div style="border-top: 1px solid #000; width: 200px; margin-bottom: 5px;"></div>
                            <div>Le Directeur</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="border-top: 1px solid #000; width: 200px; margin-bottom: 5px;"></div>
                            <div>Le Professeur Principal</div>
                        </div>
                    </div>
                </div>
            </div>
            """
            
            # Add page break except for the last student
            if i < len(students) - 1:
                html_content += '<div style="page-break-before: always;"></div>'
        
        html_content += """
        </body>
        </html>
        """
        
        response = HttpResponse(html_content, content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="bulletins_notes_francais.html"'
        return response
    
    print_grades_report_french.short_description = _("📊 Imprimer bulletins (Français)")

    def print_grades_report_arabic(self, request, queryset):
        """Generate a modern HTML grades report in Arabic"""
        from django.http import HttpResponse
        from django.db.models import Avg, Max, Min
        
        # Get unique students from the selected grades
        student_ids = queryset.values_list('student_id', flat=True).distinct()
        
        # Get students without prefetching to avoid related name issues
        students = Student.objects.filter(id__in=student_ids)
        
        html_content = """
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <title>كشف الدرجات</title>
            <style>
                @media print {
                    @page {
                        size: A4;
                        margin: 10mm;
                    }
                    body {
                        margin: 0 !important;
                        padding: 0 !important;
                        background: white !important;
                    }
                    .no-print {
                        display: none !important;
                    }
                    .student-report {
                        page-break-after: always;
                        margin: 0 auto !important;
                        box-shadow: none !important;
                    }
                    /* Remove headers and footers */
                    @page { margin: 0; }
                    body { margin: 1.6cm; }
                }
                body {
                    font-family: 'Arial', Tahoma, sans-serif;
                    margin: 0;
                    padding: 15px;
                    background: #f8f9fa;
                    color: #333;
                    direction: rtl;
                    text-align: right;
                }
                .student-report {
                    background: white;
                    padding: 25px;
                    margin: 10px auto;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    border-radius: 8px;
                    max-width: 210mm;
                    min-height: 280mm;
                }
                .header {
                    text-align: center;
                    border-bottom: 3px solid #2c5aa0;
                    padding-bottom: 15px;
                    margin-bottom: 25px;
                }
                .school-name {
                    font-size: 24px;
                    font-weight: bold;
                    color: #2c5aa0;
                    margin-bottom: 8px;
                }
                .report-title {
                    font-size: 20px;
                    color: #555;
                    margin-bottom: 10px;
                }
                .student-info {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 12px;
                    margin-bottom: 25px;
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 6px;
                }
                .info-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 6px 0;
                }
                .info-label {
                    font-weight: bold;
                    color: #555;
                }
                .info-value {
                    color: #333;
                }
                .grades-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                    font-size: 13px;
                }
                .grades-table th {
                    background: #2c5aa0;
                    color: white;
                    padding: 10px;
                    text-align: right;
                    font-weight: bold;
                }
                .grades-table td {
                    padding: 10px;
                    border-bottom: 1px solid #ddd;
                    text-align: right;
                }
                .grades-table tr:nth-child(even) {
                    background: #f8f9fa;
                }
                .grade-excellent { color: #2e7d32; font-weight: bold; }
                .grade-good { color: #689f38; }
                .grade-average { color: #f57c00; }
                .grade-poor { color: #d32f2f; font-weight: bold; }
                .summary-card {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 15px;
                    border-radius: 6px;
                    margin: 15px 0;
                }
                .summary-stats {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 12px;
                    text-align: center;
                }
                .stat-item h3 {
                    margin: 0;
                    font-size: 20px;
                    font-weight: bold;
                }
                .stat-item p {
                    margin: 3px 0 0 0;
                    opacity: 0.9;
                    font-size: 14px;
                }
                .print-btn {
                    background: #2c5aa0;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 14px;
                    margin: 8px;
                }
                .no-print {
                    text-align: center;
                    margin: 15px;
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    background: white;
                    padding: 10px;
                    z-index: 1000;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }
                .latin-name {
                    font-family: 'Segoe UI', sans-serif;
                    font-size: 14px;
                    color: #666;
                    margin-top: 3px;
                }
                .semester-title {
                    color: #2c5aa0;
                    border-bottom: 2px solid #2c5aa0;
                    padding-bottom: 6px;
                    margin: 20px 0 15px 0;
                    font-size: 16px;
                }
            </style>
        </head>
        <body>
            <div class="no-print">
                <button class="print-btn" onclick="window.print()">🖨️ طباعة الكشوف</button>
                <button class="print-btn" onclick="window.close()">❌ إغلاق</button>
            </div>
        """
        
        for i, student in enumerate(students):
            # Get grades for this student directly
            grades = Grade.objects.filter(student=student).order_by('semester', 'subject__name')
            
            # Calculate statistics
            total_grades = grades.count()
            average_score = grades.aggregate(Avg('score'))['score__avg'] or 0
            max_score = grades.aggregate(Max('score'))['score__max'] or 0
            min_score = grades.aggregate(Min('score'))['score__min'] or 0
            
            # Group grades by semester
            semesters = {}
            for grade in grades:
                if grade.semester not in semesters:
                    semesters[grade.semester] = []
                semesters[grade.semester].append(grade)
            
            html_content += f"""
            <div class="student-report">
                <div class="header">
                    <div class="school-name">تراست أكاديمي</div>
                    <div class="report-title">كشف الدرجات المدرسية</div>
                </div>
                
                <div class="student-info">
                    <div class="info-item">
                        <span class="info-label">الاسم واللقب:</span>
                        <span class="info-value">
                            {student.first_name_arabic or student.first_name} {student.last_name_arabic or student.last_name}
                        </span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">الاسم باللاتينية:</span>
                        <span class="info-value">
                            <div class="latin-name">{student.last_name} {student.first_name}</div>
                        </span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">رقم التسجيل:</span>
                        <span class="info-value">{student.student_id}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">المستوى:</span>
                        <span class="info-value">{student.grade_level}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">القسم:</span>
                        <span class="info-value">{student.class_room or 'غير محدد'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">السنة الدراسية:</span>
                        <span class="info-value">{timezone.now().year}-{timezone.now().year + 1}</span>
                    </div>
                </div>
                
                <div class="summary-card">
                    <div class="summary-stats">
                        <div class="stat-item">
                            <h3>{average_score:.1f}</h3>
                            <p>المعدل العام</p>
                        </div>
                        <div class="stat-item">
                            <h3>{max_score}</h3>
                            <p>أعلى درجة</p>
                        </div>
                        <div class="stat-item">
                            <h3>{min_score}</h3>
                            <p>أقل درجة</p>
                        </div>
                    </div>
                </div>
            """
            
            # Add grades tables for each semester
            for semester, semester_grades in semesters.items():
                html_content += f"""
                <div class="semester-title">
                    الفصل الدراسي {semester}
                </div>
                <table class="grades-table">
                    <thead>
                        <tr>
                            <th>المادة</th>
                            <th>الدرجة</th>
                            <th>التقدير</th>
                            <th>السنة</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                
                for grade in semester_grades:
                    # CORRECTED: Proper grade appreciation logic for 10-point system
                    if grade.score >= 9:
                        grade_class = "grade-excellent"
                        appreciation = "ممتاز"
                    elif grade.score >= 8:
                        grade_class = "grade-excellent"
                        appreciation = "جيد جداً"
                    elif grade.score >= 7:
                        grade_class = "grade-good"
                        appreciation = "جيد"
                    elif grade.score >= 6:
                        grade_class = "grade-average"
                        appreciation = "مقبول"
                    elif grade.score >= 5:
                        grade_class = "grade-poor"
                        appreciation = "ضعيف"
                    else:
                        grade_class = "grade-poor"
                        appreciation = "راسب"
                    
                    html_content += f"""
                        <tr>
                            <td>{grade.subject.name}</td>
                            <td class="{grade_class}">{grade.score}</td>
                            <td class="{grade_class}">{appreciation}</td>
                            <td>{grade.year}</td>
                        </tr>
                    """
                
                html_content += """
                    </tbody>
                </table>
                """
            
            # Add footer with signature area
            html_content += """
                <div style="margin-top: 40px; border-top: 1px solid #ddd; padding-top: 20px;">
                    <div style="display: flex; justify-content: space-between;">
                        <div style="text-align: center;">
                            <div style="border-top: 1px solid #000; width: 200px; margin-bottom: 5px;"></div>
                            <div>المدير</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="border-top: 1px solid #000; width: 200px; margin-bottom: 5px;"></div>
                            <div>الأستاذ الرئيسي</div>
                        </div>
                    </div>
                </div>
            </div>
            """
            
            # Add page break except for the last student
            if i < len(students) - 1:
                html_content += '<div style="page-break-before: always;"></div>'
        
        html_content += """
        </body>
        </html>
        """
        
        response = HttpResponse(html_content, content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="كشف_الدرجات_العربية.html"'
        return response
    
    print_grades_report_arabic.short_description = _("📊 طباعة كشوف الدرجات (العربية)")

    def get_letter_grade(self, score):
        """Convert numerical score to letter grade"""
        if score >= 9:
            return "A+"
        elif score >= 8:
            return "A"
        elif score >= 7:
            return "B+"
        elif score >= 6:
            return "B"
        elif score >= 5:
            return "C"
        else:
            return "F" 


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'quantity', 'location', 'is_available']
    list_filter = ['category']
    search_fields = ['name']
    list_editable = ['quantity']
    
    class Meta:
        verbose_name = _("Inventory Item")
        verbose_name_plural = _("Inventory Items")
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['name'].label = _('Name')
        form.base_fields['category'].label = _('Category')
        form.base_fields['quantity'].label = _('Quantity')
        form.base_fields['location'].label = _('Location')
        form.base_fields['is_available'].label = _('Is available')
        return form

@admin.register(SchoolConfig)
class SchoolConfigAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SchoolConfig.objects.exists()
    
    class Meta:
        verbose_name = _("School Configuration")
        verbose_name_plural = _("School Configuration")
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['name'].label = _('School name')
        form.base_fields['address'].label = _('Address')
        form.base_fields['phone'].label = _('Phone')
        form.base_fields['email'].label = _('Email')
        form.base_fields['website'].label = _('Website')
        form.base_fields['academic_year'].label = _('Academic year')
        form.base_fields['currency'].label = _('Currency')
        return form

@admin.register(StudentCertificate)
class StudentCertificateAdmin(admin.ModelAdmin):
    list_display = ['certificate_number', 'student_name', 'academic_year', 'level', 'issue_date', 'is_issued']
    list_filter = ['academic_year', 'level', 'is_issued', 'issue_date']
    search_fields = ['student__last_name', 'student__first_name', 'registration_number']
    actions = ['generate_certificates_arabic_simple']
    
    class Meta:
        verbose_name = _("Student Certificate")
        verbose_name_plural = _("Student Certificates")
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['student'].label = _('Student')
        form.base_fields['academic_year'].label = _('Academic year')
        form.base_fields['level'].label = _('Level')
        form.base_fields['registration_number'].label = _('Registration number')
        form.base_fields['institution_name'].label = _('Institution name')
        form.base_fields['license_number'].label = _('License number')
        form.base_fields['director_name'].label = _('Director name')
        form.base_fields['issue_city'].label = _('Issue city')
        form.base_fields['issue_date'].label = _('Issue date')
        form.base_fields['is_issued'].label = _('Is issued')
        form.base_fields['certificate_number'].label = _('Certificate number')
        return form

    def student_name(self, obj):
        return f"{obj.student.last_name} {obj.student.first_name}"
    student_name.short_description = _("Student Name")

    def generate_certificates_arabic_simple(self, request, queryset):
        """Generate Arabic certificates using simple HTML"""
        from django.http import HttpResponse
        from datetime import datetime
        
        html_content = """
        <!DOCTYPE html>
        <html dir="rtl" lang="ar">
        <head>
            <meta charset="UTF-8">
            <title>الشهادات المدرسية</title>
            <style>
                @media print {
                    @page {
                        size: A4;
                        margin: 0;
                    }
                    body {
                        margin: 0 !important;
                        padding: 0 !important;
                        background: white !important;
                    }
                    .no-print {
                        display: none !important;
                    }
                    .certificate {
                        margin: 0 auto !important;
                        box-shadow: none !important;
                        /* page-break-after: always; ? REMOVED */
                    }
                }
                body {
                    font-family: 'Arial', Tahoma, sans-serif;
                    margin: 0;
                    padding: 0;
                    direction: rtl;
                    text-align: right;
                    background: #f5f5f5;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                }
                .certificate {
                    padding: 30px;
                    background: white;
                    position: relative;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    width: 210mm;
                    height: 297mm;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                }
                .certificate-content {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    justify-content: space-between;
                }
                .header {
                    text-align: center;
                    border-bottom: 2px solid #1a237e;
                    padding-bottom: 15px;
                    margin-bottom: 20px;
                }
                .republic {
                    font-size: 22px; /* Increased from 20px */
                    font-weight: bold;
                    color: #1a237e;
                    margin-bottom: 8px;
                }
                .year-directorate {
                    font-size: 16px; /* Increased from 14px */
                    color: #5f6368;
                    margin-bottom: 10px;
                }
                .institution {
                    font-size: 18px; /* Increased from 16px */
                    font-weight: bold;
                    color: #d32f2f;
                    margin: 15px 0;
                    padding: 10px; /* Increased padding */
                    background: #ffebee;
                    border-right: 3px solid #d32f2f;
                    text-align: center;
                }
                .student-section {
                    background: #e3f2fd;
                    padding: 20px;
                    margin: 20px 0;
                    border-right: 3px solid #1976d2;
                }
                .certification-text {
                    font-size: 18px; /* Increased from 16px */
                    font-weight: bold;
                    color: #1976d2;
                    margin-bottom: 15px;
                    text-align: center;
                }
                .student-info {
                    margin: 15px 0;
                }
                .info-row {
                    display: flex;
                    margin-bottom: 8px;
                    padding: 5px;
                }
                .info-label {
                    font-weight: bold;
                    color: #1a237e;
                    width: 120px;
                    min-width: 120px;
                    font-size: 15px; /* Increased font size */
                }
                .info-value {
                    flex: 1;
                    font-size: 15px; /* Increased font size */
                }
                .study-info {
                    background: #f3e5f5;
                    padding: 15px;
                    margin: 15px 0;
                    border-right: 3px solid #7b1fa2;
                }
                .issue-info {
                    text-align: center;
                    margin: 5px 0; /* Reduced margin to move up */
                    padding: 12px;
                    background: #e8f5e8;
                    border: 1px solid #4caf50;
                    font-weight: bold;
                    font-size: 17px; /* Increased from default */
                }
                .latin-name {
                    text-align: center;
                    margin: 0px 0; /* Reduced margin to move up */
                    padding: 12px;
                    background: #fff3e0;
                    border: 1px solid #ff9800;
                    font-size: 17px; /* Increased from default */
                }
                .latin-text {
                    font-family: 'Arial', sans-serif;
                    font-size: 18px; /* Increased from 16px */
                    font-weight: bold;
                    color: black;
                }
                .stamp-area {
                    text-align: left;
                    margin-top: 120px; /* Increased space for stamp */
                    height: 80px; /* Increased height for stamp */
                }
                .stamp {
                    display: inline-block;
                    padding: 10px 20px;
                    border: 2px solid transparent;
                    border-radius: 5px;
                    color: transparent;
                    font-weight: bold;
                    background: transparent;
                }
                .separator {
                    border-top: 1px dashed #1a237e;
                    margin: 20px 0;
                }
                .print-btn {
                    background: #1a237e;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                    margin: 10px;
                }
                .footer-section {
                    margin-top: auto;
                    padding-bottom: 20px; /* Added padding at bottom */
                }
            </style>
        </head>
        <body>
            <div class="no-print" style="text-align: center; margin: 20px; position: fixed; top: 0; left: 0; right: 0; background: white; padding: 10px; z-index: 1000;">
                <button class="print-btn" onclick="window.print()">🖨️ طباعة الشهادات</button>
                <button class="print-btn" onclick="window.close()">❌ إغلاق</button>
            </div>
        """
        
        for i, certificate in enumerate(queryset):
            # Generate Latin name from the original name fields (English/French)
            latin_name = f"{certificate.student.last_name.upper()} {certificate.student.first_name.upper()}"
            # Use YYYY/MM/DD format
            current_date = datetime.now().strftime('%Y/%m/%d')
            
            html_content += f"""
            <div class="certificate">
                <div class="certificate-content">
                    <div>
                        <div class="header">
                            <div class="republic">الجمهورية الجزائرية الديمقراطية الشعبية</div>
                            <div class="year-directorate">
                                السنة الدراسية {certificate.academic_year}<br>
                                مديرية النشاط الاجتماعي والتضامن
                            </div>
                        </div>
                        
                        <div class="separator"></div>
                        
                        <div class="institution">
                            مؤسسة {certificate.institution_name} المعتمدة من طرف الدولة تحت رقم ترخيص {certificate.license_number}
                        </div>
                        
                        <div class="student-section">
                            <div class="certification-text">
                                تشهد السيدة {certificate.director_name} أن التلميذ(ة)
                            </div>
                            
                            <div class="student-info">
                                <div class="info-row">
                                    <div class="info-label">اللقب:</div>
                                    <div class="info-value">{certificate.student.last_name_arabic or certificate.student.last_name}</div>
                                </div>
                                <div class="info-row">
                                    <div class="info-label">الاسم:</div>
                                    <div class="info-value">{certificate.student.first_name_arabic or certificate.student.first_name}</div>
                                </div>
                                <div class="info-row">
                                    <div class="info-label">تاريخ الميلاد:</div>
                                    <div class="info-value">{certificate.student.date_of_birth.strftime('%Y/%m/%d') if certificate.student.date_of_birth else 'غير محدد'}</div>
                                </div>
                                <div class="info-row">
                                    <div class="info-label">مكان الميلاد:</div>
                                    <div class="info-value">{certificate.issue_city}</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="study-info">
                            <div class="certification-text">تابع دراسته</div>
                            <div class="student-info">
                                <div class="info-row">
                                    <div class="info-label">السنة الدراسية:</div>
                                    <div class="info-value">{certificate.academic_year}</div>
                                </div>
                                <div class="info-row">
                                    <div class="info-label">المستوى:</div>
                                    <div class="info-value">{certificate.level}</div>
                                </div>
                                <div class="info-row">
                                    <div class="info-label">رقم التسجيل:</div>
                                    <div class="info-value">{certificate.registration_number}</div>
                                </div>
                                <div class="info-row">
                                    <div class="info-label">رقم الشهادة:</div>
                                    <div class="info-value">{certificate.certificate_number}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="footer-section">
                        <!-- Green and orange boxes moved up by reducing margins -->
                        <div class="issue-info">
                            <strong>حرر ب{certificate.issue_city} في {current_date}</strong>
                        </div>
                        
                        <div class="latin-name">
                            <div style="font-weight: bold; margin-bottom: 8px;">الكتابة بالحروف اللاتينية</div>
                            <div class="latin-text">{latin_name}</div>
                        </div>
                        
                        <!-- More space for stamp area -->
                        <div class="stamp-area">
                            <div class="stamp">&nbsp;</div>
                        </div>
                    </div>
                </div>
            </div>
            """
            
            # Add page break for multiple certificates
            if i < len(queryset) - 1:
                html_content += '<div style="page-break-before: always;"></div>'
        
        html_content += """
        </body>
        </html>
        """
        
        response = HttpResponse(html_content, content_type='text/html; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="certificates_arabic.html"'
        return response
    
    generate_certificates_arabic_simple.short_description = _("إنشاء شهادات بالعربية")



@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['grade_level', 'day_display', 'start_time', 'end_time', 'subject', 'teacher', 'room']
    list_filter = ['grade_level', 'day']
    search_fields = ['grade_level', 'subject', 'teacher', 'room']
    ordering = ['grade_level', 'day', 'start_time']

    fieldsets = (
        ("Lesson Information", {
            'fields': (
                'grade_level',
                'day',
                ('start_time', 'end_time'),
                ('subject', 'teacher'),
                'room',
                'notes',
            )
        }),
    )

    # ——— SMART DROPDOWNS (COMBOBOXES) FOR ALL TEXT FIELDS ———
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "grade_level":
            levels = Student.objects.values_list('grade_level', flat=True).distinct().order_by('grade_level')
            choices = [('', '--- Select Level ---')] + [(l, l) for l in levels]
            kwargs['widget'] = forms.Select(choices=choices)

        elif db_field.name == "subject":
            subjects = Subject.objects.values_list('name', flat=True).distinct().order_by('name')
            choices = [('', '--- Select Subject ---')] + [(s, s) for s in subjects]
            kwargs['widget'] = forms.Select(choices=choices)

        elif db_field.name == "teacher":
            staff = Staff.objects.filter(is_active=True).values_list('first_name', 'last_name').order_by('last_name')
            teacher_names = [f"{first} {last}".strip() for first, last in staff if first or last]
            choices = [('', '--- Select Teacher ---')] + [(name, name) for name in teacher_names]
            kwargs['widget'] = forms.Select(choices=choices)

        elif db_field.name == "room":
            rooms = ClassRoom.objects.values_list('name', flat=True).distinct().order_by('name')
            choices = [('', '--- Select Room ---')] + [(r, r) for r in rooms]
            kwargs['widget'] = forms.Select(choices=choices)

        return super().formfield_for_dbfield(db_field, request, **kwargs)

    # English Day Name
    def day_display(self, obj):
        days = {
            'sunday': 'Sunday', 'monday': 'Monday', 'tuesday': 'Tuesday',
            'wednesday': 'Wednesday', 'thursday': 'Thursday'
        }
        return days.get(obj.day.lower() if obj.day else '', obj.day.title())
    day_display.short_description = "Day"

    # ——— FINAL BEAUTIFUL & PROFESSIONAL PDF EXPORT ———
    actions = ['export_schedule_pdf']

    def export_schedule_pdf(self, request, queryset):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4),
                                rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = ParagraphStyle('BigTitle', parent=styles['Heading1'], fontSize=26, spaceAfter=20,
                                     alignment=TA_CENTER, textColor=colors.HexColor('#0d47a1'))
        subtitle_style = ParagraphStyle('Subtitle', fontSize=14, alignment=TA_CENTER, textColor=colors.darkblue)
        footer_style = ParagraphStyle('Footer', fontSize=10, alignment=TA_CENTER, textColor=colors.grey)

        # Optional: Add your school logo (uncomment if you have logo.png in static or media)
        # logo_path = os.path.join('static', 'images', 'logo.png')  # adjust path
        # if os.path.exists(logo_path):
        #     logo = Image(logo_path, width=80, height=80)
        #     logo.hAlign = 'CENTER'
        #     elements.append(logo)
        #     elements.append(Spacer(1, 10))

        elements.append(Paragraph("TRUST ACADEMY", title_style))
        elements.append(Paragraph("Weekly Class Schedule 2025-2026", subtitle_style))
        elements.append(Spacer(1, 20))

        levels = sorted({s.grade_level for s in queryset if s.grade_level})

        for level in levels:
            schedules = queryset.filter(grade_level=level).order_by('day', 'start_time')
            time_slots = sorted(set((s.start_time.strftime('%H:%M'), s.end_time.strftime('%H:%M')) for s in schedules),
                                key=lambda x: x[0])

            days_order = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday']
            day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday']
            data = [['Time', *day_names]]

            for start, end in time_slots:
                row = [Paragraph(f"<b>{start}</b><br/>→<br/><b>{end}</b>", styles["Normal"])]
                for day in days_order:
                    lesson = schedules.filter(day=day,
                                              start_time__hour=int(start[:2]),
                                              start_time__minute=int(start[3:])).first()

                    if lesson and lesson.end_time.strftime('%H:%M') == end:
                        subject = lesson.subject or "—"
                        teacher = lesson.teacher or ""
                        room = lesson.room or ""
                        cell = Paragraph(
                            f"<font size=11><b>{subject}</b></font><br/>"
                            f"{teacher}<br/>"
                            f"<font size=9 color=gray>{room}</font>", styles["Normal"]
                        )
                    else:
                        cell = Paragraph("—", styles["Normal"])
                    row.append(cell)
                data.append(row)

            # Table per level
            elements.append(Paragraph(f"Grade Level: <b>{level}</b>", ParagraphStyle('Level', fontSize=16, spaceAfter=15, textColor=colors.HexColor('#1a237e'))))
            table = Table(data, colWidths=[70] + [105]*5)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0d47a1')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 12),
                ('FONTSIZE', (0,1), (-1,-1), 10),
                ('GRID', (0,0), (-1,-1), 1.2, colors.grey),
                ('BACKGROUND', (0,1), (0,-1), colors.HexColor('#e8f4fd')),
                ('BACKGROUND', (1,1), (-1,-1), colors.white),
                ('LEFTPADDING', (0,0), (-1,-1), 8),
                ('RIGHTPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 40))

        # Final Footer
        elements.append(Paragraph(
            f"Generated on {timezone.now().strftime('%d %B %Y at %H:%M')} • Trust Academy • Official Document",
            footer_style
        ))

        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="TrustAcademy_Schedule_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response

    export_schedule_pdf.short_description = "Export Schedule as PDF (Professional & Printable)"


from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db import models
from django import forms
from decimal import Decimal
from .models import Payroll


# Custom Form for Payroll Admin - MUST BE DEFINED BEFORE PayrollAdmin
class PayrollAdminForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add calculation preview for social contributions
        if self.instance and self.instance.pk and self.instance.base_salary:
            base = self.instance.base_salary
            
            # Add calculation info to help text
            self.fields['cotisation_cnas'].help_text = f"9% du salaire base = {base * Decimal('0.09'):.2f} DZD"
            self.fields['cotisation_retraite'].help_text = f"7.5% du salaire base = {base * Decimal('0.075'):.2f} DZD"
            self.fields['mutuelle_mgen'].help_text = f"1.5% du salaire base = {base * Decimal('0.015'):.2f} DZD"
            
            # Show IRG calculation info
            if self.instance.total_brut:
                irg_info = f"IRG approximatif sur {self.instance.total_brut:.2f} DZD"
                self.fields['irg'].help_text = irg_info
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate that total brut > total retenues
        total_brut = cleaned_data.get('total_brut') or 0
        total_retenues = cleaned_data.get('total_retenues') or 0
        
        if total_brut < total_retenues:
            self.add_error('total_retenues', 
                "Le total des retenues ne peut pas dépasser le total brut.")
        
        return cleaned_data


from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db import models
from django import forms
from decimal import Decimal
from .models import Payroll


# Custom Form for Payroll Admin - MUST BE DEFINED BEFORE PayrollAdmin
class PayrollAdminForm(forms.ModelForm):
    class Meta:
        model = Payroll
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Calculate and set social contributions based on base salary
        if self.instance and self.instance.base_salary:
            base = self.instance.base_salary
            
            # Calculate social contributions
            cnas_amount = base * Decimal('0.09')  # 9%
            retraite_amount = base * Decimal('0.075')  # 7.5%
            mgen_amount = base * Decimal('0.015')  # 1.5%
            
            # Set initial values for social contributions
            self.fields['cotisation_cnas'].initial = cnas_amount
            self.fields['cotisation_retraite'].initial = retraite_amount
            self.fields['mutuelle_mgen'].initial = mgen_amount
            
            # Add calculation info to help text
            self.fields['cotisation_cnas'].help_text = f"9% du salaire base = {cnas_amount:.2f} DZD"
            self.fields['cotisation_retraite'].help_text = f"7.5% du salaire base = {retraite_amount:.2f} DZD"
            self.fields['mutuelle_mgen'].help_text = f"1.5% du salaire base = {mgen_amount:.2f} DZD"
            
            # Show IRG calculation info
            if self.instance.total_brut:
                # Simple IRG calculation (Algerian progressive tax)
                total_brut = self.instance.total_brut
                
                # Algerian IRG brackets (simplified)
                if total_brut <= Decimal('20000'):
                    irg_amount = total_brut * Decimal('0.00')
                elif total_brut <= Decimal('40000'):
                    irg_amount = (total_brut - Decimal('20000')) * Decimal('0.10')
                elif total_brut <= Decimal('80000'):
                    irg_amount = (total_brut - Decimal('40000')) * Decimal('0.20') + Decimal('2000')
                else:
                    irg_amount = (total_brut - Decimal('80000')) * Decimal('0.35') + Decimal('10000')
                
                self.fields['irg'].initial = irg_amount
                irg_info = f"IRG approximatif sur {total_brut:.2f} DZD = {irg_amount:.2f} DZD"
                self.fields['irg'].help_text = irg_info
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Get base salary from cleaned data
        base_salary = cleaned_data.get('base_salary') or Decimal('0')
        
        # Recalculate social contributions if base salary is provided
        if base_salary:
            # Auto-calculate social contributions if not manually set
            if 'cotisation_cnas' not in self.errors and not cleaned_data.get('cotisation_cnas'):
                cleaned_data['cotisation_cnas'] = base_salary * Decimal('0.09')
            
            if 'cotisation_retraite' not in self.errors and not cleaned_data.get('cotisation_retraite'):
                cleaned_data['cotisation_retraite'] = base_salary * Decimal('0.075')
            
            if 'mutuelle_mgen' not in self.errors and not cleaned_data.get('mutuelle_mgen'):
                cleaned_data['mutuelle_mgen'] = base_salary * Decimal('0.015')
        
        # Calculate total brut for IRG calculation
        base_salary = cleaned_data.get('base_salary') or Decimal('0')
        indemnite_residence = cleaned_data.get('indemnite_residence') or Decimal('0')
        indemnite_zone = cleaned_data.get('indemnite_zone') or Decimal('0')
        indemnite_pedagogique = cleaned_data.get('indemnite_pedagogique') or Decimal('0')
        indemnite_documentation = cleaned_data.get('indemnite_documentation') or Decimal('0')
        overtime_amount = cleaned_data.get('overtime_amount') or Decimal('0')
        prime_anciennete = cleaned_data.get('prime_anciennete') or Decimal('0')
        autres_indemnites = cleaned_data.get('autres_indemnites') or Decimal('0')
        autres_primes = cleaned_data.get('autres_primes') or Decimal('0')
        
        total_brut = (base_salary + indemnite_residence + indemnite_zone + 
                     indemnite_pedagogique + indemnite_documentation + overtime_amount +
                     prime_anciennete + autres_indemnites + autres_primes)
        
        # Auto-calculate IRG if not manually set
        if total_brut > 0 and 'irg' not in self.errors and not cleaned_data.get('irg'):
            # Algerian IRG progressive tax calculation
            if total_brut <= Decimal('20000'):
                irg_amount = Decimal('0')
            elif total_brut <= Decimal('40000'):
                irg_amount = (total_brut - Decimal('20000')) * Decimal('0.10')
            elif total_brut <= Decimal('80000'):
                irg_amount = (total_brut - Decimal('40000')) * Decimal('0.20') + Decimal('2000')
            else:
                irg_amount = (total_brut - Decimal('80000')) * Decimal('0.35') + Decimal('10000')
            
            cleaned_data['irg'] = irg_amount
        
        # Validate that total brut > total retenues
        total_brut = cleaned_data.get('total_brut') or 0
        total_retenues = cleaned_data.get('total_retenues') or 0
        
        if total_brut < total_retenues:
            self.add_error('total_retenues', 
                "Le total des retenues ne peut pas dépasser le total brut.")
        
        return cleaned_data


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    """Modern payroll administration interface with automatic calculations"""
    
    list_display = [
        'staff', 'get_period', 'echelon', 'base_salary', 'total_brut', 
        'total_retenues', 'net_a_payer', 'is_paid', 'payment_status'
    ]
    
    list_filter = [
        'month', 'year', 'is_paid', 'echelon', 'payment_method',
        'staff__position', 'staff__department'
    ]
    
    search_fields = [
        'staff__first_name', 'staff__last_name', 'staff__staff_id',
        'staff__social_security_number'
    ]
    
    list_editable = ['is_paid']
    
    actions = [
        'generate_payslips_pdf', 'mark_as_paid', 'mark_as_unpaid',
        'calculate_social_security', 'export_payroll_excel',
        'calculate_all_fields', 'auto_fill_indemnites'
    ]
    
    # Modern field organization
    fieldsets = (
        ('Informations de Base', {
            'fields': (
                'staff', 
                ('month', 'year'),
                'echelon',
                ('payment_date', 'is_paid'),
                'payment_method'
            ),
            'classes': ('collapse',)
        }),
        
        ('GAINS ET REVENUS', {
            'fields': (
                ('base_salary', 'indemnite_residence'),
                ('indemnite_zone', 'indemnite_pedagogique'),
                ('indemnite_documentation', 'prime_anciennete'),
            ),
            'classes': ('section-gains',),
            'description': 'Saisir les montants ou utiliser le bouton "Remplir automatiquement"'
        }),
        
        ('HEURES SUPPLÉMENTAIRES', {
            'fields': (
                ('overtime_hours', 'overtime_rate', 'overtime_amount'),
            ),
            'classes': ('section-overtime',)
        }),
        
        ('AUTRES GAINS', {
            'fields': (
                ('autres_indemnites', 'autres_primes'),
            ),
            'classes': ('section-other-earnings',)
        }),
        
        ('COTISATIONS SOCIALES (Calculées Auto)', {
            'fields': (
                ('cotisation_cnas', 'cotisation_retraite'),
                ('mutuelle_mgen', 'irg'),
            ),
            'classes': ('section-social', 'calculated-section'),
            'description': 'Ces champs sont calculés automatiquement. Modifier uniquement si nécessaire.'
        }),
        
        ('AUTRES RETENUES', {
            'fields': (
                ('avance_salaire', 'cotisation_syndicale'),
                'autres_retenues',
            ),
            'classes': ('section-other-deductions',)
        }),
        
        ('TOTAUX CALCULÉS (AUTO)', {
            'fields': (
                ('total_brut', 'total_retenues'),
                'net_a_payer',
            ),
            'classes': ('section-totals', 'readonly-section')
        }),
        
        ('Notes Administratives', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = [
        'overtime_amount', 'total_brut', 'total_retenues', 'net_a_payer'
    ]
    
    # Add custom form with calculation preview - NOW IT'S DEFINED
    form = PayrollAdminForm
    
    # Add CSS and JS for better UX
    class Media:
        css = {
            'all': (
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
                'admin/css/payroll.css',
            )
        }
        js = (
            'admin/js/payroll_calculations.js',
        )
    
    def get_period(self, obj):
        return f"{obj.get_month_display()}/{obj.year}"
    get_period.short_description = 'Période'
    get_period.admin_order_field = ['year', 'month']
    
    def payment_status(self, obj):
        if obj.is_paid:
            return format_html(
                '<span style="color: #2e7d32; font-weight: bold;">'
                '<i class="fas fa-check-circle"></i> PAYÉ</span>'
            )
        else:
            return format_html(
                '<span style="color: #c62828; font-weight: bold;">'
                '<i class="fas fa-clock"></i> EN ATTENTE</span>'
            )
    payment_status.short_description = 'Statut'
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Set French labels and help texts with calculation info
        field_config = {
            'staff': {
                'label': 'Employé', 
                'help_text': 'Sélectionner le membre du personnel'
            },
            'month': {
                'label': 'Mois', 
                'help_text': 'Mois de paie'
            },
            'year': {
                'label': 'Année', 
                'help_text': 'Année de paie'
            },
            'echelon': {
                'label': 'Échelon', 
                'help_text': 'Échelon salarial (1-12). Influence le salaire de base.'
            },
            'base_salary': {
                'label': 'Salaire de Base', 
                'help_text': 'Salaire fondamental en DZD. Base pour les calculs sociaux.'
            },
            'indemnite_residence': {
                'label': 'Ind. Résidence', 
                'help_text': 'Indemnité de résidence (10-15% du salaire base)'
            },
            'indemnite_zone': {
                'label': 'Ind. Zone', 
                'help_text': 'Indemnité de zone géographique (varie selon région)'
            },
            'indemnite_pedagogique': {
                'label': 'Ind. Pédagogique (IP)', 
                'help_text': 'Indemnité pédagogique pour enseignants'
            },
            'indemnite_documentation': {
                'label': 'Ind. Documentation', 
                'help_text': 'Indemnité de documentation'
            },
            'overtime_hours': {
                'label': 'Heures Supp.', 
                'help_text': 'Nombre d\'heures supplémentaires'
            },
            'overtime_rate': {
                'label': 'Taux H.Sup.', 
                'help_text': 'Taux horaire des heures supplémentaires'
            },
            'overtime_amount': {
                'label': 'Montant H.Sup.', 
                'help_text': 'Calcul automatique: Heures × Taux'
            },
            'prime_anciennete': {
                'label': 'Prime Ancienneté', 
                'help_text': 'Prime basée sur les années de service'
            },
            'autres_indemnites': {
                'label': 'Autres Indemnités', 
                'help_text': 'Autres indemnités diverses'
            },
            'autres_primes': {
                'label': 'Autres Primes', 
                'help_text': 'Autres primes exceptionnelles'
            },
            'cotisation_cnas': {
                'label': 'CNAS (9%)', 
                'help_text': 'Cotisation sécurité sociale - 9% du salaire base'
            },
            'cotisation_retraite': {
                'label': 'Retraite CNR (7.5%)', 
                'help_text': 'Cotisation retraite - 7.5% du salaire base'
            },
            'irg': {
                'label': 'IRG', 
                'help_text': 'Impôt sur le revenu global - Calcul progressif'
            },
            'mutuelle_mgen': {
                'label': 'Mutuelle MGEN (1.5%)', 
                'help_text': 'Cotisation mutuelle - 1.5% du salaire base'
            },
            'avance_salaire': {
                'label': 'Avance Salaire', 
                'help_text': 'Avance sur salaire à déduire'
            },
            'cotisation_syndicale': {
                'label': 'Cot. Syndicale', 
                'help_text': 'Cotisation syndicale'
            },
            'autres_retenues': {
                'label': 'Autres Retenues', 
                'help_text': 'Autres retenues diverses'
            },
            'total_brut': {
                'label': 'Total Brut', 
                'help_text': 'Salaire brut total (calcul automatique)'
            },
            'total_retenues': {
                'label': 'Total Retenues', 
                'help_text': 'Total des retenues (calcul automatique)'
            },
            'net_a_payer': {
                'label': 'Net à Payer', 
                'help_text': 'Salaire net après retenues (calcul automatique)'
            },
            'payment_date': {
                'label': 'Date de Paiement', 
                'help_text': 'Date prévue de paiement'
            },
            'is_paid': {
                'label': 'Payé', 
                'help_text': 'Cocher si le paiement est effectué'
            },
            'payment_method': {
                'label': 'Mode de Paiement', 
                'help_text': 'Méthode de paiement'
            },
            'notes': {
                'label': 'Notes', 
                'help_text': 'Notes administratives'
            },
        }
        
        # Add calculation preview for social contributions
        if obj and obj.base_salary:
            base = obj.base_salary
            cnas_amount = base * Decimal('0.09')
            retraite_amount = base * Decimal('0.075')
            mgen_amount = base * Decimal('0.015')
            
            field_config['cotisation_cnas']['help_text'] += f" (≈ {cnas_amount:.2f} DZD)"
            field_config['cotisation_retraite']['help_text'] += f" (≈ {retraite_amount:.2f} DZD)"
            field_config['mutuelle_mgen']['help_text'] += f" (≈ {mgen_amount:.2f} DZD)"
        
        for field_name, config in field_config.items():
            if field_name in form.base_fields:
                form.base_fields[field_name].label = config['label']
                form.base_fields[field_name].help_text = config.get('help_text', '')
        
        return form
    
    # Custom change list template
    change_list_template = 'admin/school_management/payroll/change_list.html'

    def changelist_view(self, request, extra_context=None):
        # Add summary statistics to context
        extra_context = extra_context or {}
        
        # Get filter parameters from request
        selected_month = request.GET.get('month', '')
        selected_year = request.GET.get('year', '')
        selected_paid = request.GET.get('is_paid__exact', '')
        
        # Build filter query for statistics
        filter_kwargs = {}
        if selected_month:
            filter_kwargs['month'] = selected_month
        if selected_year:
            filter_kwargs['year'] = selected_year
        if selected_paid:
            filter_kwargs['is_paid'] = bool(int(selected_paid))
        
        # Calculate payroll statistics with filters
        total_payroll = Payroll.objects.filter(**filter_kwargs).aggregate(
            total_net=models.Sum('net_a_payer'),
            total_brut=models.Sum('total_brut'),
            count=models.Count('id'),
            paid_count=models.Count('id', filter=models.Q(is_paid=True))
        )
        
        # Available months and years for filter
        months = [
            ('01', 'Janvier'), ('02', 'Février'), ('03', 'Mars'),
            ('04', 'Avril'), ('05', 'Mai'), ('06', 'Juin'),
            ('07', 'Juillet'), ('08', 'Août'), ('09', 'Septembre'),
            ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre')
        ]
        
        # Get distinct years from payroll data
        years = Payroll.objects.dates('payment_date', 'year').distinct()
        years = [year.year for year in years]
        
        # If no years found, use current and previous year
        if not years:
            current_year = timezone.now().year
            years = [current_year, current_year - 1]
        
        extra_context.update({
            'total_net': total_payroll['total_net'] or 0,
            'total_brut': total_payroll['total_brut'] or 0,
            'payroll_count': total_payroll['count'] or 0,
            'paid_count': total_payroll['paid_count'] or 0,
            'months': months,
            'years': years,
        })
        
        response = super().changelist_view(request, extra_context=extra_context)
        return response
    
    # Custom save method to trigger calculations
    def save_model(self, request, obj, form, change):
        # Calculate prime ancienneté if not set
        if not obj.prime_anciennete or obj.prime_anciennete == 0:
            obj.prime_anciennete = obj.calculate_prime_anciennete()
        
        # Auto-calculate indemnités based on base salary
        if not obj.indemnite_residence or obj.indemnite_residence == 0:
            obj.indemnite_residence = obj.base_salary * Decimal('0.10')  # 10%
        
        if not obj.indemnite_zone or obj.indemnite_zone == 0:
            obj.indemnite_zone = obj.base_salary * Decimal('0.05')  # 5%
        
        if not obj.indemnite_pedagogique or obj.indemnite_pedagogique == 0:
            obj.indemnite_pedagogique = obj.base_salary * Decimal('0.08')  # 8%
        
        # Auto-calculate social contributions
        if obj.base_salary:
            if not obj.cotisation_cnas or obj.cotisation_cnas == 0:
                obj.cotisation_cnas = obj.base_salary * Decimal('0.09')
            
            if not obj.cotisation_retraite or obj.cotisation_retraite == 0:
                obj.cotisation_retraite = obj.base_salary * Decimal('0.075')
            
            if not obj.mutuelle_mgen or obj.mutuelle_mgen == 0:
                obj.mutuelle_mgen = obj.base_salary * Decimal('0.015')
        
        # Auto-calculate IRG if not set
        if not obj.irg or obj.irg == 0:
            total_brut = obj.total_brut or obj.calculate_total_brut()
            if total_brut:
                # Algerian IRG progressive tax calculation
                if total_brut <= Decimal('20000'):
                    obj.irg = Decimal('0')
                elif total_brut <= Decimal('40000'):
                    obj.irg = (total_brut - Decimal('20000')) * Decimal('0.10')
                elif total_brut <= Decimal('80000'):
                    obj.irg = (total_brut - Decimal('40000')) * Decimal('0.20') + Decimal('2000')
                else:
                    obj.irg = (total_brut - Decimal('80000')) * Decimal('0.35') + Decimal('10000')
        
        # Save will trigger all calculations via model's save method
        super().save_model(request, obj, form, change)
    
    # ACTIONS
    def mark_as_paid(self, request, queryset):
        updated = queryset.update(is_paid=True, payment_date=timezone.now())
        self.message_user(
            request, 
            f"{updated} fiche(s) de paie marquée(s) comme payée(s).", 
            level='success'
        )
    mark_as_paid.short_description = "💰 Marquer comme payé"
    
    def mark_as_unpaid(self, request, queryset):
        updated = queryset.update(is_paid=False)
        self.message_user(
            request, 
            f"{updated} fiche(s) de paie marquée(s) comme non payée(s).", 
            level='warning'
        )
    mark_as_unpaid.short_description = "⏳ Marquer comme non payé"
    
    def calculate_social_security(self, request, queryset):
        """Auto-calculate social security contributions"""
        updated = 0
        for payroll in queryset:
            if payroll.base_salary:
                # Calculate social contributions
                payroll.cotisation_cnas = payroll.base_salary * Decimal('0.09')
                payroll.cotisation_retraite = payroll.base_salary * Decimal('0.075')
                payroll.mutuelle_mgen = payroll.base_salary * Decimal('0.015')
                
                # Calculate IRG
                total_brut = payroll.total_brut or payroll.calculate_total_brut()
                if total_brut:
                    if total_brut <= Decimal('20000'):
                        payroll.irg = Decimal('0')
                    elif total_brut <= Decimal('40000'):
                        payroll.irg = (total_brut - Decimal('20000')) * Decimal('0.10')
                    elif total_brut <= Decimal('80000'):
                        payroll.irg = (total_brut - Decimal('40000')) * Decimal('0.20') + Decimal('2000')
                    else:
                        payroll.irg = (total_brut - Decimal('80000')) * Decimal('0.35') + Decimal('10000')
            
            payroll.save()
            updated += 1
        
        self.message_user(
            request, 
            f"Calculs sociaux mis à jour pour {updated} fiche(s) de paie.", 
            level='success'
        )
    calculate_social_security.short_description = "📊 Recalculer les cotisations"
    
    def calculate_all_fields(self, request, queryset):
        """Calculate all payroll fields including social contributions"""
        updated = 0
        for payroll in queryset:
            # Force recalculation of everything
            payroll.recalculate_all()
            updated += 1
        
        self.message_user(
            request, 
            f"Calculs complets effectués pour {updated} fiche(s) de paie.", 
            level='success'
        )
    calculate_all_fields.short_description = "🧮 Calculer tous les champs"
    
    def auto_fill_indemnites(self, request, queryset):
        """Auto-fill indemnités based on base salary"""
        updated = 0
        for payroll in queryset:
            # Auto-calculate indemnités
            payroll.indemnite_residence = payroll.base_salary * Decimal('0.10')  # 10%
            payroll.indemnite_zone = payroll.base_salary * Decimal('0.05')      # 5%
            payroll.indemnite_pedagogique = payroll.base_salary * Decimal('0.08')  # 8%
            payroll.indemnite_documentation = Decimal('2000.00')  # Fixed amount
            payroll.prime_anciennete = payroll.calculate_prime_anciennete()
            
            # Auto-calculate social contributions
            if payroll.base_salary:
                payroll.cotisation_cnas = payroll.base_salary * Decimal('0.09')
                payroll.cotisation_retraite = payroll.base_salary * Decimal('0.075')
                payroll.mutuelle_mgen = payroll.base_salary * Decimal('0.015')
            
            payroll.save()
            updated += 1
        
        self.message_user(
            request, 
            f"Indemnités automatiquement remplies pour {updated} fiche(s) de paie.", 
            level='success'
        )
    auto_fill_indemnites.short_description = "⚡ Remplir automatiquement les indemnités"
    
    def export_payroll_excel(self, request, queryset):
        """Export payroll data to Excel with detailed breakdown"""
        #import pandas as pd
        from django.http import HttpResponse
        
        # Create detailed DataFrame
        data = []
        for payroll in queryset:
            data.append({
                'Matricule': payroll.staff.staff_id,
                'Nom': payroll.staff.last_name,
                'Prénom': payroll.staff.first_name,
                'Période': f"{payroll.get_month_display()}/{payroll.year}",
                'Échelon': payroll.echelon,
                'Salaire Base': float(payroll.base_salary),
                'Ind. Résidence': float(payroll.indemnite_residence),
                'Ind. Zone': float(payroll.indemnite_zone),
                'Ind. Pédagogique': float(payroll.indemnite_pedagogique),
                'Ind. Documentation': float(payroll.indemnite_documentation),
                'Heures Supp': float(payroll.overtime_hours),
                'Montant H.Sup': float(payroll.overtime_amount),
                'Prime Ancienneté': float(payroll.prime_anciennete),
                'Autres Gains': float(payroll.autres_indemnites + payroll.autres_primes),
                'Total Brut': float(payroll.total_brut),
                'CNAS (9%)': float(payroll.cotisation_cnas),
                'CNR (7.5%)': float(payroll.cotisation_retraite),
                'IRG': float(payroll.irg),
                'Mutuelle MGEN': float(payroll.mutuelle_mgen),
                'Avance Salaire': float(payroll.avance_salaire),
                'Cot. Syndicale': float(payroll.cotisation_syndicale),
                'Autres Retenues': float(payroll.autres_retenues),
                'Total Retenues': float(payroll.total_retenues),
                'Net à Payer': float(payroll.net_a_payer),
                'Statut': 'Payé' if payroll.is_paid else 'En attente',
                'Date Paiement': payroll.payment_date.strftime('%d/%m/%Y'),
            })
        
        df = pd.DataFrame(data)
        
        # Create HTTP response with Excel file
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = f'attachment; filename="export_paie_{timezone.now().strftime("%Y%m%d_%H%M")}.xlsx"'
        
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Paie', index=False)
            
            # Auto-adjust column widths
            worksheet = writer.sheets['Paie']
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
    export_payroll_excel.short_description = "📈 Exporter vers Excel"
    
    # ... [The generate_payslips_pdf method and other methods remain the same] ...
    
    def generate_payslips_pdf(self, request, queryset):
        """Generate Algerian payslips - Compact version without HTML"""
        from django.http import HttpResponse
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch, mm
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle, SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        import io
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=10*mm, bottomMargin=10*mm)
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles - COMPACT
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=10,
            spaceAfter=2,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a237e'),
            fontName='Helvetica-Bold'
        )

        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=4,
            alignment=TA_CENTER,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        )
        
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Normal'],
            fontSize=8,
            spaceAfter=1,
            alignment=TA_LEFT,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'Normal',
            parent=styles['Normal'],
            fontSize=8,
            spaceAfter=1,
            alignment=TA_LEFT,
            textColor=colors.black,
            fontName='Helvetica'
        )
        
        small_style = ParagraphStyle(
            'Small',
            parent=styles['Normal'],
            fontSize=7,
            spaceAfter=0,
            alignment=TA_LEFT,
            textColor=colors.black,
            fontName='Helvetica'
        )
        
        for payroll in queryset:
            # Header section
            elements.append(Paragraph("RÉPUBLIQUE ALGÉRIENNE DÉMOCRATIQUE ET POPULAIRE", title_style))
            elements.append(Paragraph("TRUST ACADEMY SCHOOL", subtitle_style))
            elements.append(Paragraph("BULLETIN DE PAIE - FICHE DE SALAIRE", subtitle_style))
            elements.append(Spacer(1, 0.1*inch))
            
            # Employer and Employee Information
            employer_info = [
                ["Établissement:", "Trust Academy", "Nom & Prénom:", f"{payroll.staff.last_name.upper()} {payroll.staff.first_name}"],
                ["Adresse:", "Boumerdes, Algérie", "Matricule:", payroll.staff.staff_id],
                ["Période:", f"{payroll.get_month_display()} {payroll.year}", "Fonction:", payroll.staff.position],
                ["Date paiement:", payroll.payment_date.strftime('%d/%m/%Y'), "N° Affiliation:", "2491/21"],
            ]
            
            employer_table = Table(employer_info, colWidths=[1.2*inch, 1.8*inch, 1.2*inch, 1.8*inch])
            employer_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(employer_table)
            elements.append(Spacer(1, 0.15*inch))
            
            # Earnings Section
            earnings_data = [
                ["GAINS ET REVENUS", "Montant (DZD)"],
                [f"Salaire de base (Éch.{payroll.echelon})", f"{payroll.base_salary:,.2f}"],
                ["Ind. Résidence", f"{payroll.indemnite_residence:,.2f}"],
                ["Ind. Zone", f"{payroll.indemnite_zone:,.2f}"],
                ["Ind. Pédagogique", f"{payroll.indemnite_pedagogique:,.2f}"],
                ["Ind. Documentation", f"{payroll.indemnite_documentation:,.2f}"],
            ]
            
            if payroll.overtime_amount > 0:
                earnings_data.append([f"H.Sup ({payroll.overtime_hours}h)", f"{payroll.overtime_amount:,.2f}"])
            
            if payroll.prime_anciennete > 0:
                earnings_data.append(["Prime ancienneté", f"{payroll.prime_anciennete:,.2f}"])
            
            if payroll.autres_indemnites > 0:
                earnings_data.append(["Autres indemnités", f"{payroll.autres_indemnites:,.2f}"])
            
            if payroll.autres_primes > 0:
                earnings_data.append(["Autres primes", f"{payroll.autres_primes:,.2f}"])
            
            earnings_table = Table(earnings_data, colWidths=[3*inch, 1.2*inch])
            earnings_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2e7d32')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(earnings_table)
            
            elements.append(Spacer(1, 0.05*inch))
            total_gross_data = [["TOTAL BRUT", f"{payroll.total_brut:,.2f} DZD"]]
            total_gross_table = Table(total_gross_data, colWidths=[3*inch, 1.2*inch])
            total_gross_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('BOX', (0, 0), (-1, 0), 1, colors.black),
            ]))
            elements.append(total_gross_table)
            elements.append(Spacer(1, 0.1*inch))
            
            # Deductions Section
            deductions_data = [
                ["COTISATIONS ET DÉDUCTIONS", "Montant (DZD)"],
                ["CNAS (9%)", f"{payroll.cotisation_cnas:,.2f}"],
                ["Retraite (7.5%)", f"{payroll.cotisation_retraite:,.2f}"],
            ]
            
            if payroll.irg > 0:
                deductions_data.append(["IRG", f"{payroll.irg:,.2f}"])
            
            if payroll.mutuelle_mgen > 0:
                deductions_data.append(["Mutuelle MGEN", f"{payroll.mutuelle_mgen:,.2f}"])
            
            if payroll.avance_salaire > 0:
                deductions_data.append(["Avance salaire", f"{payroll.avance_salaire:,.2f}"])
            
            if payroll.cotisation_syndicale > 0:
                deductions_data.append(["Cot. syndicale", f"{payroll.cotisation_syndicale:,.2f}"])
            
            if payroll.autres_retenues > 0:
                deductions_data.append(["Autres retenues", f"{payroll.autres_retenues:,.2f}"])
            
            deductions_table = Table(deductions_data, colWidths=[3*inch, 1.2*inch])
            deductions_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c62828')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(deductions_table)
            
            elements.append(Spacer(1, 0.05*inch))
            total_deductions_data = [["TOTAL DÉDUCTIONS", f"{payroll.total_retenues:,.2f} DZD"]]
            total_deductions_table = Table(total_deductions_data, colWidths=[3*inch, 1.2*inch])
            total_deductions_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                ('BOX', (0, 0), (-1, 0), 1, colors.black),
            ]))
            elements.append(total_deductions_table)
            elements.append(Spacer(1, 0.1*inch))
            
            # Net Salary Section
            net_salary_data = [
                ["SALAIRE BRUT", f"{payroll.total_brut:,.2f} DZD"],
                ["MOINS: DÉDUCTIONS", f"{payroll.total_retenues:,.2f} DZD"],
                ["SALAIRE NET À PAYER", f"{payroll.net_a_payer:,.2f} DZD"],
            ]
            
            net_salary_table = Table(net_salary_data, colWidths=[2.5*inch, 1.7*inch])
            net_salary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#1a237e')),
                ('TEXTCOLOR', (0, 2), (-1, 2), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 2), 10),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#1a237e')),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(net_salary_table)
            elements.append(Spacer(1, 0.15*inch))
            
            # Payment Status and Signatures
            payment_status = "PAYÉ" if payroll.is_paid else "EN ATTENTE"
            
            # FIX: Instead of trying to convert colors, use the hex strings directly
            if payroll.is_paid:
                status_color_hex = '#2e7d32'  # Green
            else:
                status_color_hex = '#c62828'  # Red
                
            status_data = [
                #["STATUT DU PAIEMENT:", f"<font color='{status_color_hex}'>{payment_status}</font>"],
                ["MODE DE PAIEMENT:", payroll.get_payment_method_display()],
            ]
            
            status_table = Table(status_data, colWidths=[2*inch, 2.2*inch])
            status_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(status_table)
            elements.append(Spacer(1, 0.1*inch))
            
            # Signatures section
            signature_data = [
                ["COMPTABLE"],
                ["", ""],
                ["", ""],
                ["Signature & Cachet"],
            ]
            
            signature_table = Table(signature_data, colWidths=[1.2*inch, 0.3*inch, 1.2*inch, 0.3*inch, 1.2*inch])
            signature_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 7),
                ('FONTSIZE', (0, 3), (-1, 3), 6),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LINEBELOW', (0, 1), (0, 2), 1, colors.black),
                ('LINEBELOW', (2, 1), (2, 2), 1, colors.black),
                ('LINEBELOW', (4, 1), (4, 2), 1, colors.black),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            elements.append(signature_table)
            elements.append(Spacer(1, 0.05*inch))
            
            # Footer notes
            if payroll.notes:
                notes_data = [[f"Notes: {payroll.notes}"]]
                notes_table = Table(notes_data, colWidths=[4.2*inch])
                notes_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Oblique'),
                    ('FONTSIZE', (0, 0), (-1, -1), 6),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#666666')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#eeeeee')),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9f9f9')),
                    ('LEFTPADDING', (0, 0), (-1, -1), 4),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 2),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ]))
                elements.append(notes_table)
            
            # Footer with company info
            #footer_data = [[
                #Paragraph(
                    #"<i>Trust Academy School - Bordj Menaiel, Boumerdes, Algérie<br/>"
                    #"Tél: +213 552 44 33 22 - Email: contact@trustacademy.dz<br/>"
                    #"Bulletin généré le: " + timezone.now().strftime('%d/%m/%Y %H:%M') + "</i>",
                    #small_style
                #)
            #]]
            #footer_table = Table(footer_data, colWidths=[4.2*inch])
           # footer_table.setStyle(TableStyle([
                #('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                #('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#777777')),
                #('TOPPADDING', (0, 0), (-1, -1), 4),
           # ]))
           # elements.append(footer_table)
            
            # Page break for next payslip
            if payroll != queryset.last():
                elements.append(Spacer(1, 0.5*inch))
        
        # Build PDF
        doc.build(elements)
        
        # Prepare response
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        filename = f"bulletins_paie_{timezone.now().strftime('%Y%m%d_%H%M')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    generate_payslips_pdf.short_description = "📄 Générer les bulletins de paie (PDF)"

    def get_actions(self, request):
        actions = super().get_actions(request)
        
        # Custom action ordering
        custom_order = [
            'generate_payslips_pdf',
            'export_payroll_excel',
            'mark_as_paid',
            'mark_as_unpaid',
            'auto_fill_indemnites',
            'calculate_social_security',
            'calculate_all_fields',
        ]
        
        # Reorder actions
        ordered_actions = {}
        for action_name in custom_order:
            if action_name in actions:
                ordered_actions[action_name] = actions[action_name]
        
        # Add any remaining actions
        for action_name, action_func in actions.items():
            if action_name not in ordered_actions:
                ordered_actions[action_name] = action_func
        
        return ordered_actions
    
    def get_list_display_links(self, request, list_display):
        # Make staff name clickable for details
        return ['staff']

    def get_queryset(self, request):
        # Prefetch related staff data for performance
        qs = super().get_queryset(request)
        return qs.select_related('staff').order_by('-year', '-month', 'staff__last_name')

    def get_changeform_initial_data(self, request):
        # Set default values for new payroll entries
        initial = super().get_changeform_initial_data(request)
        initial.update({
            'month': timezone.now().month,
            'year': timezone.now().year,
            'echelon': 1,
            'payment_date': timezone.now(),
            'overtime_rate': Decimal('150.00'),  # Default overtime rate
        })
        return initial

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Limit staff choices to active employees only
        if db_field.name == "staff":
            from school_management.models import Staff  # Import here to avoid circular imports
            kwargs["queryset"] = Staff.objects.filter(is_active=True).order_by('last_name', 'first_name')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        # Only allow deletion for superusers
        if request.user.is_superuser:
            return True
        return False

    def get_readonly_fields(self, request, obj=None):
        # Make certain fields read-only for non-superusers
        readonly_fields = list(self.readonly_fields)
        if not request.user.is_superuser:
            readonly_fields.extend(['staff', 'month', 'year', 'echelon'])
        return readonly_fields

    # Add custom permission checks
    def has_module_permission(self, request):
        return request.user.has_perm('school_management.view_payroll')

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm('school_management.view_payroll')

    def has_add_permission(self, request):
        return request.user.has_perm('school_management.add_payroll')

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm('school_management.change_payroll')

    def has_export_permission(self, request):
        return request.user.has_perm('school_management.export_payroll')
