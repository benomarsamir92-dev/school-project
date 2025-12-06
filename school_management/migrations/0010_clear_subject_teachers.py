from django.db import migrations

def clear_subject_teachers(apps, schema_editor):
    Subject = apps.get_model('school_management', 'Subject')
    Subject.objects.all().update(teacher=None)
    print("✓ Cleared all teacher references")

class Migration(migrations.Migration):
    dependencies = [
        ('school_management', '0009_alter_payroll_options_alter_subject_teacher'),
    ]
    
    operations = [
        migrations.RunPython(clear_subject_teachers, migrations.RunPython.noop),
    ]
