from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Fix all invalid user references in the database'
    
    def handle(self, *args, **options):
        self.stdout.write("Fixing invalid user references...")
        
        tables_to_fix = [
            ('school_management_subject', 'teacher_id'),
            ('school_management_classroom', 'teacher_id'),
            ('school_management_grade', 'graded_by_id'),
            ('school_management_attendance', 'recorded_by_id'),
            ('school_management_payment', 'created_by_id'),
        ]
        
        total_fixed = 0
        
        with connection.cursor() as cursor:
            for table, field in tables_to_fix:
                sql = f"""
                    UPDATE {table} 
                    SET {field} = NULL 
                    WHERE {field} IS NOT NULL 
                    AND {field} NOT IN (SELECT id FROM auth_user)
                """
                try:
                    cursor.execute(sql)
                    fixed = cursor.rowcount
                    if fixed > 0:
                        self.stdout.write(
                            self.style.SUCCESS(f"✓ Fixed {fixed} records in {table}.{field}")
                        )
                        total_fixed += fixed
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"⚠ Could not fix {table}.{field}: {e}")
                    )
        
        if total_fixed > 0:
            self.stdout.write(
                self.style.SUCCESS(f"\n✅ Fixed {total_fixed} invalid references total!")
            )
        else:
            self.stdout.write("\n✅ No invalid references found.")
        
        self.stdout.write("\nNow restart your server and try adding subjects.")