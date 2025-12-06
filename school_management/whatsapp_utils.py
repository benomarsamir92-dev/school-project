# your_app/whatsapp_utils.py
from urllib.parse import quote

def clean_phone_number(phone_number):
    """Clean phone number and ensure correct Algeria format"""
    phone_clean = ''.join(filter(str.isdigit, str(phone_number)))
    if phone_clean.startswith('213'):
        phone_clean = phone_clean[3:]
    elif phone_clean.startswith('212'):
        phone_clean = phone_clean[3:]
    phone_clean = phone_clean.lstrip('0')
    return phone_clean[-9:] if len(phone_clean) >= 9 else phone_clean

def generate_whatsapp_link(phone_number, message):
    """Generate WhatsApp link with proper Algeria number"""
    try:
        cleaned_number = clean_phone_number(phone_number)
        encoded_message = quote(message)
        whatsapp_url = f"https://wa.me/213{cleaned_number}?text={encoded_message}"
        return whatsapp_url
    except Exception as e:
        print(f"WhatsApp link error: {e}")
        return "#"

def send_whatsapp_to_parent(student, message):
    if student.parent_phone:
        return True
    return False

def send_welcome_message_whatsapp(student):
    message = f"""🎓 *Welcome to Our School!*

Dear Parent,

We are pleased to welcome *{student.get_full_name()}* to our school community!

*Student ID:* {student.student_id}
*Grade Level:* {student.grade_level}

Please save this number for school communications.

Best regards,
School Administration"""
    return send_whatsapp_to_parent(student, message)

def send_fee_reminder_whatsapp(payment):
    message = f"""💰 *Fee Reminder*

Dear Parent,

This is a reminder that the *{payment.get_payment_type_display()}* fee of *{payment.amount} DZD*
for *{payment.student.get_full_name()}* is due on *{payment.due_date}*.

*Current status:* {payment.get_status_display()}

Please make the payment at your earliest convenience.

Best regards,
School Administration"""
    return send_whatsapp_to_parent(payment.student, message)

def send_attendance_notification_whatsapp(attendance):
    if attendance.status in ['absent', 'late']:
        message = f"""📚 *Attendance Notice*

Dear Parent,

We would like to inform you that *{attendance.student.get_full_name()}*
was marked as *{attendance.get_status_display().upper()}* on *{attendance.date}*.

{f'*Notes:* {attendance.notes}' if attendance.notes else ''}

Please contact the school if you have any questions.

Best regards,
School Administration"""
        return send_whatsapp_to_parent(attendance.student, message)
    return False

def send_grade_notification_whatsapp(grade):
    message = f"""📊 *Grade Update*

Dear Parent,

We would like to inform you about *{grade.student.get_full_name()}*'s performance:

*Subject:* {grade.subject.name}
*Grade:* {grade.grade}
*Semester:* {grade.get_semester_display()}
*Year:* {grade.year}

{f'*Comments:* {grade.comments}' if grade.comments else ''}

Best regards,
School Administration"""
    return send_whatsapp_to_parent(grade.student, message)