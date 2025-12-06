from django.urls import path
from . import views

urlpatterns = [
    # Public routes
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),

    # Authentication
    path('staff/login/', views.staff_login, name='staff_login'),
    path('staff/logout/', views.staff_logout, name='staff_logout'),

    # Dashboards
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('staff/admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # Student management
    path('staff/students/', views.student_list, name='student_list'),
    path('staff/students/<int:pk>/', views.student_detail, name='student_detail'),

    # Attendance
    path('staff/attendance/<int:class_id>/', views.take_attendance, name='take_attendance'),
    path('staff/attendance/history/<int:class_id>/', views.attendance_history, name='attendance_history'),

    # Grades
    path('staff/grades/<int:subject_id>/', views.enter_grades, name='enter_grades'),

    # WhatsApp integration
    path('staff/whatsapp/<int:student_id>/', views.send_whatsapp_message, name='send_whatsapp_message'),

    # API endpoints
    path('api/student-search/', views.api_student_search, name='api_student_search'),

    # Data analysis
    path('data-analysis/', views.api_student_search, name='data-analysis'),

    #path('staff/send-bulk-grade-notifications/', views.send_bulk_grade_notifications, name='send_bulk_grade_notifications'),

    # Document Generation URLs
    #######path('staff/documents/', views.document_generator, name='document_generator'),
    ######path('staff/documents/students/<int:class_id>/<str:format_type>/<str:language>/', views.generate_student_list, name='generate_student_list'),
    #####path('staff/documents/students/all/<str:format_type>/<str:language>/', views.generate_student_list, name='generate_all_students'),
    ####path('staff/documents/meeting/<str:meeting_type>/<str:format_type>/<str:language>/', views.generate_meeting_invitation, name='generate_meeting'),
    ###path('staff/documents/staff/all/<str:format_type>/<str:language>/', views.generate_staff_list, name='generate_staff_list'),

    # Note: generate_report_card is commented out since it's not in the views yet
    # path('staff/documents/report-card/<int:student_id>/<str:format_type>/<str:language>/', views.generate_report_card, name='generate_report_card'),
]
