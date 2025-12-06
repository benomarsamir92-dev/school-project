from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
import uuid
from decimal import Decimal
from decimal import Decimal, ROUND_HALF_UP
from django.contrib.auth.models import User

# REMOVED: GRADE_LEVEL_CHOICES - No longer needed for free text input

class SchoolConfig(models.Model):
    """School configuration and settings"""
    name = models.CharField(_('school name'), max_length=200, default="Trust Academy School")
    address = models.TextField(_('address'), blank=True)
    phone = models.CharField(_('phone'), max_length=20, blank=True)
    email = models.EmailField(_('email'), blank=True)
    website = models.URLField(_('website'), blank=True)
    logo = models.ImageField(_('logo'), upload_to='school/logo/', blank=True, null=True)
    academic_year = models.CharField(_('academic year'), max_length=20, default="2024-2025")
    currency = models.CharField(_('currency'), max_length=10, default="DZD")

    class Meta:
        verbose_name = _("School Configuration")
        verbose_name_plural = _("School Configuration")

    def __str__(self):
        return self.name

class Staff(models.Model):
    """Staff members (teachers, admin, etc.) with complete payroll information"""
    
    POSITION_CHOICES = [
        ('teacher', _('Teacher')),
        ('admin', _('Administrator')),
        ('principal', _('Principal')),
        ('accountant', _('Accountant')),
        ('secretary', _('Secretary')),
        ('librarian', _('Librarian')),
        ('supervisor', _('Supervisor')),
        ('technician', _('Technician')),
        ('other', _('Other')),
    ]
    
    GENDER_CHOICES = [
        ('M', _('Male')),
        ('F', _('Female')),
    ]
    
    FAMILY_SITUATION_CHOICES = [
        ('single', _('Célibataire')),
        ('married', _('Marié(e)')),
        ('divorced', _('Divorcé(e)')),
        ('widowed', _('Veuf/Veuve')),
    ]

    # Make user field optional
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        verbose_name=_('user'),
        blank=True, 
        null=True,  # Add this to make it optional
        help_text="Lier à un compte utilisateur (optionnel)"
    )
    
    staff_id = models.CharField(_('staff ID'), max_length=20, unique=True)
    first_name = models.CharField(_('first name'), max_length=100)
    last_name = models.CharField(_('last name'), max_length=100)
    first_name_arabic = models.CharField(_('first name (Arabic)'), max_length=100, blank=True)
    last_name_arabic = models.CharField(_('last name (Arabic)'), max_length=100, blank=True)
    
    # Personal Information
    position = models.CharField(_('position'), max_length=20, choices=POSITION_CHOICES, default='teacher')
    gender = models.CharField(_('gender'), max_length=1, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(_('date of birth'), blank=True, null=True)
    place_of_birth = models.CharField(_('place of birth'), max_length=100, blank=True)
    nationality = models.CharField(_('nationality'), max_length=50, default='Algérienne', blank=True)
    cin_number = models.CharField(_('CIN number'), max_length=20, blank=True, help_text="Numéro de carte d'identité nationale")
    family_situation = models.CharField(
        _('family situation'), 
        max_length=20, 
        choices=FAMILY_SITUATION_CHOICES, 
        default='single',
        blank=True
    )
    number_of_children = models.PositiveIntegerField(_('number of children'), default=0)
    
    # Contact Information
    phone = models.CharField(_('phone'), max_length=20, blank=True)
    emergency_phone = models.CharField(_('emergency phone'), max_length=20, blank=True)
    email = models.EmailField(_('email'), blank=True)
    address = models.TextField(_('address'), blank=True)
    city = models.CharField(_('city'), max_length=50, blank=True, default='Boumerdes')
    
    # Professional Information
    hire_date = models.DateField(_('hire date'), default=timezone.now)
    department = models.CharField(_('department'), max_length=100, blank=True)
    qualification = models.CharField(_('qualification'), max_length=100, blank=True)
    
    # Salary and Payroll Information
    salary = models.DecimalField(_('base salary'), max_digits=10, decimal_places=2, default=0, help_text="Salaire de base en DZD")
    social_security_number = models.CharField(
        _('social security number'), 
        max_length=20, 
        blank=True, 
        help_text="Numéro de sécurité sociale"
    )
    
    # Banking Information
    bank_name = models.CharField(_('bank name'), max_length=100, blank=True)
    bank_account_number = models.CharField(_('bank account number'), max_length=50, blank=True)
    
    # Administrative Information
    is_active = models.BooleanField(_('is active'), default=True)
    notes = models.TextField(_('notes'), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _("Staff")
        verbose_name_plural = _("Staff")
        ordering = ['position', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.get_position_display()})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name_arabic(self):
        """Get the full name in Arabic"""
        if self.first_name_arabic and self.last_name_arabic:
            return f"{self.first_name_arabic} {self.last_name_arabic}"
        return ""
    
    def get_age(self):
        """Calculate age from date of birth"""
        if self.date_of_birth:
            today = timezone.now().date()
            return today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        return None
    
    def get_years_of_service(self):
        """Calculate years of service"""
        today = timezone.now().date()
        return today.year - self.hire_date.year - (
            (today.month, today.day) < (self.hire_date.month, self.hire_date.day)
        )
    
    def save(self, *args, **kwargs):
        # Auto-populate email from user if available and email is empty
        if not self.email and self.user and self.user.email:
            self.email = self.user.email
        
        super().save(*args, **kwargs)


class ClassRoom(models.Model):
    """Class rooms/grades"""
    name = models.CharField(_('name'), max_length=50)
    grade_level = models.CharField(_('grade level'), max_length=50, default='Grade 1')  # CHANGED: Free text field
    section = models.CharField(_('section'), max_length=10, blank=True)
    teacher = models.ForeignKey(Staff, verbose_name=_('teacher'), on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'position': 'teacher'})
    room_number = models.CharField(_('room number'), max_length=10, blank=True)
    capacity = models.IntegerField(_('capacity'), default=30)
    is_active = models.BooleanField(_('is active'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _("Class Room")
        verbose_name_plural = _("Class Rooms")
        ordering = ['grade_level', 'section']
        unique_together = ['grade_level', 'section']

    def __str__(self):
        return f"{self.grade_level} - Section {self.section}"  # CHANGED: Direct display

class Student(models.Model):
    """Student information"""
    GENDER_CHOICES = [
        ('M', _('Male')),
        ('F', _('Female')),
    ]

    student_id = models.CharField(_('student ID'), max_length=20, unique=True)
    first_name = models.CharField(_('first name'), max_length=100)
    last_name = models.CharField(_('last name'), max_length=100)
    first_name_arabic = models.CharField(_('first name (Arabic)'), max_length=100, blank=True)
    last_name_arabic = models.CharField(_('last name (Arabic)'), max_length=100, blank=True)
    gender = models.CharField(_('gender'), max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(_('date of birth'))
    class_room = models.ForeignKey('ClassRoom', verbose_name=_('class room'), on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    grade_level = models.CharField(_('grade level'), max_length=50, default='Grade 1')  # CHANGED: Free text field

    parent_name = models.CharField(_('parent name'), max_length=200)
    parent_phone = models.CharField(_('parent phone'), max_length=20)
    parent_email = models.EmailField(_('parent email'), blank=True)
    parent_address = models.TextField(_('parent address'), blank=True)

    emergency_contact_name = models.CharField(_('emergency contact name'), max_length=200, blank=True)
    emergency_contact_phone = models.CharField(_('emergency contact phone'), max_length=20, blank=True)

    medical_conditions = models.TextField(_('medical conditions'), blank=True)
    allergies = models.TextField(_('allergies'), blank=True)

    enrollment_date = models.DateField(_('enrollment date'), default=timezone.now)
    is_active = models.BooleanField(_('is active'), default=True)
    photo = models.ImageField(_('photo'), upload_to='students/photos/', blank=True, null=True)
    notes = models.TextField(_('notes'), blank=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _("Student")
        verbose_name_plural = _("Students")
        ordering = ['grade_level', 'first_name', 'last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_id})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def get_full_name_arabic(self):
        """Get the full name in Arabic"""
        if self.first_name_arabic and self.last_name_arabic:
            return f"{self.first_name_arabic} {self.last_name_arabic}"
        return _("Arabic name not available")

    def get_display_name(self):
        """Get display name - prefers Arabic if available, otherwise English"""
        if self.first_name_arabic and self.last_name_arabic:
            return f"{self.first_name_arabic} {self.last_name_arabic}"
        return f"{self.first_name} {self.last_name}"


class Subject(models.Model):
    """Academic subjects"""
    name = models.CharField(_('name'), max_length=100)
    code = models.CharField(_('code'), max_length=10, unique=True)
    description = models.TextField(_('description'), blank=True)
    grade_level = models.CharField(_('grade level'), max_length=50, default='Grade 1')
    
    # CHANGED: Remove null=True and blank=True to make it required
    teacher = models.ForeignKey(
        User, 
        verbose_name=_('teacher'), 
        on_delete=models.SET_NULL, 
        null=True,  # KEEP THIS
        blank=True,  # KEEP THIS
        help_text=_("Select a teacher from the Users system")
    )
    
    credits = models.IntegerField(_('credits'), default=1)
    is_active = models.BooleanField(_('is active'), default=True)

    class Meta:
        verbose_name = _("Subject")
        verbose_name_plural = _("Subjects")
        ordering = ['grade_level', 'name']

    def __str__(self):
        return f"{self.name} ({self.grade_level})"

class Attendance(models.Model):
    """Student attendance records"""
    ATTENDANCE_STATUS = [
        ('present', _('Present')),
        ('absent', _('Absent')),
        ('late', _('Late')),
        ('excused', _('Excused')),
    ]

    student = models.ForeignKey(Student, verbose_name=_('student'), on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(_('date'), default=timezone.now)
    status = models.CharField(_('status'), max_length=10, choices=ATTENDANCE_STATUS, default='present')
    notes = models.TextField(_('notes'), blank=True)
    recorded_by = models.ForeignKey(Staff, verbose_name=_('recorded by'), on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(_('recorded at'), default=timezone.now)

    class Meta:
        verbose_name = _("Attendance")
        verbose_name_plural = _("Attendance")
        ordering = ['-date', 'student']
        unique_together = ['student', 'date']

    def __str__(self):
        return f"{self.student} - {self.date} - {self.status}"

class Grade(models.Model):
    """Student grades and marks"""
    SEMESTER_CHOICES = [
        (1, _('Semester 1')),
        (2, _('Semester 2')),
    ]

    student = models.ForeignKey(Student, verbose_name=_('student'), on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, verbose_name=_('subject'), on_delete=models.CASCADE)
    semester = models.IntegerField(_('semester'), choices=SEMESTER_CHOICES, default=1)
    year = models.IntegerField(_('year'), default=2024)
    score = models.DecimalField(_('score'), max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(20)], default=0)
    comments = models.TextField(_('comments'), blank=True)
    graded_by = models.ForeignKey(Staff, verbose_name=_('graded by'), on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _("Grade")
        verbose_name_plural = _("Grades")
        ordering = ['-year', '-semester', 'student']
        unique_together = ['student', 'subject', 'semester', 'year']

    def __str__(self):
        return f"{self.student} - {self.subject} - {self.score}"

class Payment(models.Model):
    """Fee payments"""
    PAYMENT_STATUS = [
        ('pending', _('Pending')),
        ('paid', _('Paid')),
        ('overdue', _('Overdue')),
        ('cancelled', _('Cancelled')),
    ]

    PAYMENT_TYPES = [
        ('tuition', _('Tuition Fee')),
        ('transport', _('Transport Fee')),
        ('lunch', _('Lunch Fee')),
        ('uniform', _('Uniform Fee')),
        ('books', _('Books Fee')),
        ('other', _('Other')),
    ]

    student = models.ForeignKey(Student, verbose_name=_('student'), on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(_('payment type'), max_length=20, choices=PAYMENT_TYPES, default='tuition')
    amount = models.DecimalField(_('amount'), max_digits=10, decimal_places=2)
    due_date = models.DateField(_('due date'))
    paid_date = models.DateField(_('paid date'), blank=True, null=True)
    status = models.CharField(_('status'), max_length=10, choices=PAYMENT_STATUS, default='pending')
    notes = models.TextField(_('notes'), blank=True)
    receipt_number = models.CharField(_('receipt number'), max_length=50, unique=True, blank=True)
    created_by = models.ForeignKey(Staff, verbose_name=_('created by'), on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ['-due_date', 'student']

    def __str__(self):
        return f"{self.student} - {self.payment_type} - {self.amount}"

class InventoryItem(models.Model):
    """School inventory items"""
    CATEGORY_CHOICES = [
        ('furniture', _('Furniture')),
        ('electronics', _('Electronics')),
        ('books', _('Books')),
        ('sports', _('Sports Equipment')),
        ('lab', _('Lab Equipment')),
        ('office', _('Office Supplies')),
        ('other', _('Other')),
    ]

    name = models.CharField(_('name'), max_length=200)
    category = models.CharField(_('category'), max_length=20, choices=CATEGORY_CHOICES, default='other')
    description = models.TextField(_('description'), blank=True)
    quantity = models.IntegerField(_('quantity'), default=1)
    location = models.CharField(_('location'), max_length=100, blank=True)
    supplier = models.CharField(_('supplier'), max_length=200, blank=True)
    purchase_date = models.DateField(_('purchase date'), blank=True, null=True)
    purchase_price = models.DecimalField(_('purchase price'), max_digits=10, decimal_places=2, blank=True, null=True)
    condition = models.CharField(_('condition'), max_length=50, blank=True)
    notes = models.TextField(_('notes'), blank=True)
    is_available = models.BooleanField(_('is available'), default=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _("Inventory Item")
        verbose_name_plural = _("Inventory Items")
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.quantity})"


class StudentCertificate(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name=_("Student"))
    academic_year = models.CharField(max_length=20, verbose_name=_("Academic Year"))
    level = models.CharField(max_length=50, verbose_name=_("Level"))
    registration_number = models.CharField(max_length=50, verbose_name=_("Registration Number"))
    
    # New fields from the certificate template
    institution_name = models.CharField(max_length=200, default="Trust Academy", verbose_name=_("Institution Name"))
    license_number = models.CharField(max_length=50, default="2491/21", verbose_name=_("License Number"))
    director_name = models.CharField(max_length=100, default="مديرة Trust Academy", verbose_name=_("Director Name"))
    issue_city = models.CharField(max_length=100, default="بومرداس", verbose_name=_("Issue City"))
    issue_date = models.DateField(default=timezone.now, verbose_name=_("Issue Date"))
    
    # Additional fields
    certificate_number = models.CharField(max_length=50, unique=True, verbose_name=_("Certificate Number"))
    is_issued = models.BooleanField(default=False, verbose_name=_("Is Issued"))
    
    class Meta:
        verbose_name = _("Student Certificate")
        verbose_name_plural = _("Student Certificates")
    
    def __str__(self):
        return f"{self.student} - {self.academic_year}"


# school_management/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _


class Schedule(models.Model):
    DAYS = [
        ('sunday', _('Sunday')),
        ('monday', _('Monday')),
        ('tuesday', _('Tuesday')),
        ('wednesday', _('Wednesday')),
        ('thursday', _('Thursday')),
    ]

    grade_level = models.CharField(_("Grade Level"), max_length=50)
    day = models.CharField(_("Day"), max_length=10, choices=DAYS)
    start_time = models.TimeField(_("Start Time"))
    end_time = models.TimeField(_("End Time"))
    subject = models.CharField(_("Subject"), max_length=100, blank=True)
    teacher = models.CharField(_("Teacher"), max_length=100, blank=True)
    room = models.CharField(_("Classroom"), max_length=50, blank=True)
    notes = models.TextField(_("Notes"), blank=True, null=True)

    class Meta:
        verbose_name = _("Schedule")           # English by default
        verbose_name_plural = _("Schedules")   # English in sidebar & breadcrumbs
        ordering = ['grade_level', 'day', 'start_time']

    def __str__(self):
        return f"{self.grade_level} - {self.get_day_display()} {self.start_time.strftime('%H:%M')}"



class Payroll(models.Model):
    """Payroll model for Algerian staff payslips with all necessary components"""
    
    MONTH_CHOICES = [
        ('01', 'Janvier'), ('02', 'Février'), ('03', 'Mars'), ('04', 'Avril'),
        ('05', 'Mai'), ('06', 'Juin'), ('07', 'Juillet'), ('08', 'Août'),
        ('09', 'Septembre'), ('10', 'Octobre'), ('11', 'Novembre'), ('12', 'Décembre')
    ]
    
    ECHELON_CHOICES = [(str(i), f'Échelon {i}') for i in range(1, 13)]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('bank', 'Virement bancaire'),
        ('check', 'Chèque'),
        ('transfer', 'Virement'),
        ('other', 'Autre')
    ]
    
    staff = models.ForeignKey(
        'Staff', 
        on_delete=models.CASCADE, 
        verbose_name=_('staff member'),
        related_name='payrolls'
    )
    month = models.CharField(_('month'), max_length=2, choices=MONTH_CHOICES)
    year = models.IntegerField(_('year'), default=timezone.now().year)
    
    # Échelon and basic information
    echelon = models.CharField(_('échelon'), max_length=2, choices=ECHELON_CHOICES, default='1')
    
    # EARNINGS (GAINS)
    base_salary = models.DecimalField(_('salaire de base'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    indemnite_residence = models.DecimalField(_('indemnité de résidence'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    indemnite_zone = models.DecimalField(_('indemnité de zone'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    indemnite_pedagogique = models.DecimalField(_('indemnité pédagogique (IP)'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    indemnite_documentation = models.DecimalField(_('indemnité de documentation'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Overtime
    overtime_hours = models.DecimalField(_('heures supplémentaires'), max_digits=5, decimal_places=2, default=Decimal('0.00'))
    overtime_rate = models.DecimalField(_('taux heures supp.'), max_digits=8, decimal_places=2, default=Decimal('0.00'))
    overtime_amount = models.DecimalField(_('montant heures supp.'), max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)
    
    # Other earnings
    prime_anciennete = models.DecimalField(_('prime d\'ancienneté'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    autres_indemnites = models.DecimalField(_('autres indemnités'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    autres_primes = models.DecimalField(_('autres primes'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # DEDUCTIONS (RETENUES)
    # Social security (standard Algerian rates)
    cotisation_cnas = models.DecimalField(_('cotisation CNAS (9%)'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    cotisation_retraite = models.DecimalField(_('cotisation retraite CNR (7.5%)'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    irg = models.DecimalField(_('impôt sur le revenu (IRG)'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    mutuelle_mgen = models.DecimalField(_('mutuelle MGEN (1.5%)'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Other deductions
    avance_salaire = models.DecimalField(_('avance sur salaire'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    cotisation_syndicale = models.DecimalField(_('cotisation syndicale'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    autres_retenues = models.DecimalField(_('autres retenues'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Calculated fields
    total_brut = models.DecimalField(_('total brut'), max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)
    total_retenues = models.DecimalField(_('total des retenues'), max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)
    net_a_payer = models.DecimalField(_('net à payer'), max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)
    
    # Payment information
    payment_date = models.DateField(_('payment date'), default=timezone.now)
    is_paid = models.BooleanField(_('is paid'), default=False)
    payment_method = models.CharField(
        _('payment method'), 
        max_length=20, 
        choices=PAYMENT_METHOD_CHOICES, 
        default='bank'
    )
    
    notes = models.TextField(_('notes'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Payroll")
        verbose_name_plural = _("Payrolls")
        unique_together = ['staff', 'month', 'year']
        ordering = ['-year', '-month', 'staff__last_name']
    
    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.get_month_display()}/{self.year}"
    
    def clean(self):
        """Validate payroll data"""
        from django.core.exceptions import ValidationError
        
        # Check if payroll already exists for this staff and period
        if Payroll.objects.filter(
            staff=self.staff, 
            month=self.month, 
            year=self.year
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                f"Une fiche de paie existe déjà pour {self.staff.get_full_name()} "
                f"pour la période {self.get_month_display()}/{self.year}"
            )
    
    def save(self, *args, **kwargs):
        """Override save to auto-calculate all amounts"""
        self.calculate_all_amounts()
        super().save(*args, **kwargs)
    
    def calculate_all_amounts(self):
        """Calculate all automatic amounts including social contributions"""
        # 1. Calculate overtime amount
        self.overtime_amount = (self.overtime_hours * self.overtime_rate).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        # 2. Calculate total gross salary
        self.total_brut = (
            self.base_salary +
            self.indemnite_residence +
            self.indemnite_zone +
            self.indemnite_pedagogique +
            self.indemnite_documentation +
            self.overtime_amount +
            self.prime_anciennete +
            self.autres_indemnites +
            self.autres_primes
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # 3. AUTO-CALCULATE SOCIAL CONTRIBUTIONS
        self.calculate_social_contributions()
        
        # 4. Calculate total deductions
        self.total_retenues = (
            self.cotisation_cnas +
            self.cotisation_retraite +
            self.irg +
            self.mutuelle_mgen +
            self.avance_salaire +
            self.cotisation_syndicale +
            self.autres_retenues
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        # 5. Calculate net salary
        self.net_a_payer = (self.total_brut - self.total_retenues).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        
        # Ensure net salary is not negative
        if self.net_a_payer < Decimal('0.00'):
            self.net_a_payer = Decimal('0.00')
    
    def calculate_social_contributions(self):
        """Calculate social contributions based on Algerian regulations"""
        
        # Calculate taxable base (base salary + indemnities - some exempt amounts)
        taxable_base = (
            self.base_salary +
            self.indemnite_residence +
            self.indemnite_zone +
            self.indemnite_pedagogique +
            self.indemnite_documentation
        )
        
        # For Algerian calculations:
        # Base for CNAS/CNR = taxable base (capped at 300,000 DZD annual)
        max_monthly_base = Decimal('25000.00')  # 300,000 / 12
        
        if taxable_base > max_monthly_base:
            calculation_base = max_monthly_base
        else:
            calculation_base = taxable_base
        
        # 1. CNAS (Caisse Nationale des Assurances Sociales) - 9%
        # Only calculate if not manually set or if value is 0
        if self.cotisation_cnas == Decimal('0.00'):
            # CNAS = 9% of calculation base
            self.cotisation_cnas = (calculation_base * Decimal('0.09')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        
        # 2. CNR (Caisse Nationale de Retraite) - 7.5%
        # Only calculate if not manually set or if value is 0
        if self.cotisation_retraite == Decimal('0.00'):
            # CNR = 7.5% of calculation base
            self.cotisation_retraite = (calculation_base * Decimal('0.075')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        
        # 3. IRG (Impôt sur le Revenu Global) - Algerian Income Tax
        # Only calculate if not manually set or if value is 0
        if self.irg == Decimal('0.00'):
            # For IRG, use total_brut as base (all earnings)
            self.irg = self.calculate_irg(self.total_brut)
        
        # 4. MGEN (Mutuelle Générale de l'Éducation Nationale) - Usually 1.5%
        # Only calculate if not manually set or if value is 0
        if self.mutuelle_mgen == Decimal('0.00'):
            # MGEN = 1.5% of base salary (capped)
            mgen_base = min(self.base_salary, Decimal('60000.00'))  # Cap at 60,000
            self.mutuelle_mgen = (mgen_base * Decimal('0.015')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
    
    def calculate_irg(self, monthly_salary):
        """Calculate IRG based on Algerian tax brackets (2024 regulations)"""
        # Algerian IRG brackets for 2024 (monthly)
        # Convert annual brackets to monthly for easier calculation
        brackets = [
            (Decimal('0.00'), Decimal('25000.00'), Decimal('0.00')),        # 0% - up to 25,000
            (Decimal('25000.01'), Decimal('41666.67'), Decimal('0.20')),    # 20% - 25,001 to 41,667
            (Decimal('41666.68'), Decimal('58333.33'), Decimal('0.30')),    # 30% - 41,668 to 58,333
            (Decimal('58333.34'), Decimal('150000.00'), Decimal('0.35')),   # 35% - 58,334 to 150,000
            (Decimal('150000.01'), Decimal('1000000.00'), Decimal('0.40')), # 40% - above 150,000
        ]
        
        irg = Decimal('0.00')
        remaining_salary = monthly_salary
        
        for lower, upper, rate in brackets:
            if remaining_salary > lower:
                # Calculate taxable amount in this bracket
                bracket_amount = min(remaining_salary, upper) - lower
                if bracket_amount > Decimal('0.00'):
                    irg += bracket_amount * rate
                
                # Stop if we've reached the salary limit
                if remaining_salary <= upper:
                    break
        
        # Apply 10% reduction for social contributions (CNAS + CNR)
        social_reduction = (self.cotisation_cnas + self.cotisation_retraite) * Decimal('0.10')
        irg = max(irg - social_reduction, Decimal('0.00'))
        
        # Apply family quotient reduction (simplified - 10% per dependent)
        # You can customize this based on staff's family situation
        if hasattr(self.staff, 'dependents_count'):
            family_reduction = irg * (Decimal('0.10') * min(self.staff.dependents_count, 3))
            irg = max(irg - family_reduction, Decimal('0.00'))
        
        return irg.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def get_social_contributions_summary(self):
        """Get a summary of all social contributions"""
        return {
            'cnas': {
                'name': 'CNAS (9%)',
                'amount': self.cotisation_cnas,
                'percentage': Decimal('9.00'),
                'base': self.base_salary,
                'calculation': f"{self.base_salary} × 9% = {self.cotisation_cnas}"
            },
            'cnr': {
                'name': 'CNR Retraite (7.5%)',
                'amount': self.cotisation_retraite,
                'percentage': Decimal('7.50'),
                'base': self.base_salary,
                'calculation': f"{self.base_salary} × 7.5% = {self.cotisation_retraite}"
            },
            'irg': {
                'name': 'IRG',
                'amount': self.irg,
                'percentage': None,  # Progressive tax
                'base': self.total_brut,
                'calculation': f"Calcul progressif sur {self.total_brut}"
            },
            'mgen': {
                'name': 'Mutuelle MGEN (1.5%)',
                'amount': self.mutuelle_mgen,
                'percentage': Decimal('1.50'),
                'base': self.base_salary,
                'calculation': f"{self.base_salary} × 1.5% = {self.mutuelle_mgen}"
            },
            'total_social': self.cotisation_cnas + self.cotisation_retraite + self.irg + self.mutuelle_mgen
        }
    
    def get_earnings_breakdown(self):
        """Get detailed earnings breakdown"""
        return {
            'base_salary': self.base_salary,
            'indemnite_residence': self.indemnite_residence,
            'indemnite_zone': self.indemnite_zone,
            'indemnite_pedagogique': self.indemnite_pedagogique,
            'indemnite_documentation': self.indemnite_documentation,
            'overtime': self.overtime_amount,
            'prime_anciennete': self.prime_anciennete,
            'autres_indemnites': self.autres_indemnites,
            'autres_primes': self.autres_primes,
            'total': self.total_brut
        }
    
    def get_deductions_breakdown(self):
        """Get detailed deductions breakdown"""
        return {
            'cnas': self.cotisation_cnas,
            'cnr': self.cotisation_retraite,
            'irg': self.irg,
            'mgen': self.mutuelle_mgen,
            'avance_salaire': self.avance_salaire,
            'cotisation_syndicale': self.cotisation_syndicale,
            'autres_retenues': self.autres_retenues,
            'total': self.total_retenues
        }
    
    def get_month_name(self):
        """Get month name in French"""
        return dict(self.MONTH_CHOICES).get(self.month, '')
    
    @property
    def period(self):
        """Get period in format: Mois/Année"""
        return f"{self.get_month_display()}/{self.year}"
    
    @property
    def payment_status(self):
        """Get payment status with color coding"""
        if self.is_paid:
            return "PAYÉ"
        else:
            return "EN ATTENTE"
    
    @property
    def years_of_service(self):
        """Calculate years of service for prime ancienneté"""
        if hasattr(self.staff, 'hire_date'):
            today = timezone.now().date()
            years = today.year - self.staff.hire_date.year
            if today.month < self.staff.hire_date.month or (
                today.month == self.staff.hire_date.month and today.day < self.staff.hire_date.day
            ):
                years -= 1
            return max(years, 0)
        return 0
    
    def calculate_prime_anciennete(self):
        """Auto-calculate prime ancienneté based on years of service"""
        years = self.years_of_service
        if years >= 2:
            # Standard calculation: 2% per year after 2 years, capped at 30%
            percentage = min((years - 2) * Decimal('0.02'), Decimal('0.30'))
            return (self.base_salary * percentage).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return Decimal('0.00')
    
    def recalculate_all(self):
        """Force recalculation of all fields"""
        self.calculate_all_amounts()
        self.save()


# ========== SIGNALS TO PREVENT INVALID REFERENCES ==========
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(pre_save, sender=Subject)
def validate_subject_teacher(sender, instance, **kwargs):
    """Validate teacher exists before saving"""
    if instance.teacher_id and not User.objects.filter(id=instance.teacher_id).exists():
        instance.teacher_id = None  # Clear invalid reference
