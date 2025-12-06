from urllib.parse import quote
import random
from django.utils import timezone

def clean_phone_number(phone_number):
    """
    Clean phone number and ensure correct Algeria format
    """
    phone_clean = ''.join(filter(str.isdigit, str(phone_number)))
    
    # Remove any existing country code
    if phone_clean.startswith('213'):
        phone_clean = phone_clean[3:]  # Remove Algeria code
    elif phone_clean.startswith('212'):
        phone_clean = phone_clean[3:]  # Remove Morocco code
    
    # Remove leading zero if present
    phone_clean = phone_clean.lstrip('0')
    
    # Ensure it's 9 digits
    if len(phone_clean) == 9:
        return phone_clean
    else:
        # If not 9 digits, take last 9 digits
        return phone_clean[-9:]

def generate_whatsapp_link(phone_number, message):
    """
    Generate WhatsApp link with proper Algeria number
    """
    try:
        cleaned_number = clean_phone_number(phone_number)
        encoded_message = quote(message)
        whatsapp_url = f"https://wa.me/213{cleaned_number}?text={encoded_message}"
        return whatsapp_url
    except Exception as e:
        print(f"WhatsApp link error: {e}")
        return "#"

def get_staff_role_display(position):
    """
    Get display name for staff position
    """
    position_display = {
        'teacher': 'Teacher',
        'admin': 'Administrator',
        'principal': 'Principal',
        'accountant': 'Accountant',
        'secretary': 'Secretary',
        'librarian': 'Librarian',
    }
    return position_display.get(position, position)

def calculate_attendance_percentage(student, start_date, end_date):
    """
    Calculate attendance percentage for a student in date range
    """
    from .models import Attendance
    
    attendance_records = Attendance.objects.filter(
        student=student,
        date__range=[start_date, end_date]
    )
    
    total_days = attendance_records.count()
    if total_days == 0:
        return 0
    
    present_days = attendance_records.filter(status='present').count()
    return round((present_days / total_days) * 100, 1)

def generate_receipt_number():
    """
    Generate unique receipt number for payments
    """
    timestamp = timezone.now().strftime('%y%m%d')
    random_num = random.randint(1000, 9999)
    return f"RCP{timestamp}{random_num}"
