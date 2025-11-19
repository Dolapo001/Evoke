# apps/core/management/commands/create_admin.py
from django.core.management.base import BaseCommand
from apps.core.models import Student
from apps.houses.models import House

class Command(BaseCommand):
    help = 'Create admin users with predetermined names'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            default='Evoke Admin',
            help='Admin display name'
        )
        parser.add_argument(
            '--matric',
            type=str,
            default='ADMIN001',
            help='Admin matric number'
        )

    def handle(self, *args, **options):
        admin_name = options['name']
        admin_matric = options['matric']

        # Check if admin already exists
        if Student.objects.filter(matric_number=admin_matric).exists():
            self.stdout.write(self.style.WARNING(f'Admin user {admin_matric} already exists'))
            return

        # Create admin user
        admin_user = Student.objects.create(
            matric_number=admin_matric,
            name=admin_name,
            role='admin',
            is_staff=True,
            is_superuser=True,
            house=None,  # Admin has no house
            randomization_complete=True  # Admin doesn't need randomization
        )

        self.stdout.write(self.style.SUCCESS(
            f'Admin user created successfully!\n'
            f'Name: {admin_name}\n'
            f'Matric: {admin_matric}\n'
            f'Login with just the name/matric (no house selection required)'
        ))