# apps/core/management/commands/import_students.py
import csv
import os
import re
from django.core.management.base import BaseCommand
from apps.core.models import Student
from apps.houses.models import House
from django.utils import timezone
from datetime import datetime
from django.db import IntegrityError


class Command(BaseCommand):
    help = 'Import students from CSV file with house-based authentication'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')
        parser.add_argument('--update', action='store_true', help='Update existing students')
        parser.add_argument('--skip-duplicates', action='store_true', help='Skip duplicate matric numbers')
        parser.add_argument('--mark-randomized', action='store_true', help='Mark students with houses as randomized')

    def clean_house_name(self, house_name):
        """Remove 'House' prefix and clean house name"""
        cleaned = re.sub(r'^House\s+', '', house_name.strip(), flags=re.IGNORECASE)
        return cleaned.strip()

    def find_house(self, house_name):
        """Find house with flexible matching"""
        if not house_name:
            return None

        house_name = self.clean_house_name(house_name)

        # Try exact match first
        try:
            return House.objects.get(name__iexact=house_name)
        except House.DoesNotExist:
            pass

        # Try contains match
        try:
            return House.objects.get(name__icontains=house_name)
        except House.DoesNotExist:
            pass

        # Try house name mapping
        house_mapping = {
            'stark': 'Stark',
            'baratheon': 'Baratheon',
            'greyjoy': 'Greyjoy',
            'lannister': 'Lannister',
            'targaryen': 'Targaryen'
        }

        lower_house_name = house_name.lower()
        for key, value in house_mapping.items():
            if key in lower_house_name:
                try:
                    return House.objects.get(name__icontains=value)
                except House.DoesNotExist:
                    continue

        self.stderr.write(f'Warning: House "{house_name}" not found')
        return None

    def generate_matric_number(self, name, row_num):
        """Generate a unique matric number for students without one"""
        base_name = re.sub(r'[^a-zA-Z0-9]', '', name)[:10].upper()
        return f"TEMP{row_num:04d}_{base_name}"

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']
        update_existing = options['update']
        skip_duplicates = options['skip_duplicates']
        mark_randomized = options['mark_randomized']

        if not os.path.isfile(csv_file_path):
            self.stderr.write(self.style.ERROR(f'Error: File "{csv_file_path}" not found!'))
            return

        # If mark-randomized flag is set, update all existing students with houses
        if mark_randomized:
            self.stdout.write("Marking all students with houses as randomized...")
            students_with_houses = Student.objects.filter(house__isnull=False)
            updated_count = students_with_houses.update(randomization_complete=True)
            self.stdout.write(f"Updated {updated_count} students to mark randomization as complete")
            return

        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                csv_reader = csv.DictReader(file)

                required_columns = ['Name', 'Matric Number', 'Level', 'Department', 'House', 'Registered Date']
                if not all(col in csv_reader.fieldnames for col in required_columns):
                    self.stderr.write(f'Error: CSV must contain columns: {required_columns}')
                    self.stdout.write(f'Found columns: {list(csv_reader.fieldnames)}')
                    return

                success_count = 0
                error_count = 0
                skipped_count = 0
                update_count = 0

                existing_houses = list(House.objects.all().values_list('name', flat=True))
                self.stdout.write(f'Existing houses in DB: {existing_houses}')

                for row_num, row in enumerate(csv_reader, 2):
                    try:
                        name = row['Name'].strip()
                        matric_number = row['Matric Number'].strip()
                        level = row['Level'].strip()
                        department = row['Department'].strip()
                        house_display_name = row['House'].strip()
                        registered_date_str = row['Registered Date'].strip()

                        if not name:
                            self.stderr.write(f'Row {row_num}: Missing name')
                            skipped_count += 1
                            continue

                        if not house_display_name:
                            self.stderr.write(f'Row {row_num}: Missing house')
                            skipped_count += 1
                            continue

                        # Find house
                        house = self.find_house(house_display_name)
                        if not house:
                            self.stderr.write(f'Row {row_num}: House "{house_display_name}" not found')
                            error_count += 1
                            continue

                        # Parse registered date
                        try:
                            registered_date = datetime.strptime(registered_date_str, '%m/%d/%Y, %I:%M:%S %p')
                            registered_date = timezone.make_aware(registered_date)
                        except ValueError:
                            registered_date = timezone.now()

                        # Handle matric number - generate one if empty
                        if not matric_number:
                            matric_number = self.generate_matric_number(name, row_num)

                        # Check if student already exists
                        existing_student = None
                        try:
                            existing_student = Student.objects.get(matric_number=matric_number)
                        except Student.DoesNotExist:
                            pass

                        if existing_student:
                            if update_existing:
                                # Update existing student
                                existing_student.name = name
                                existing_student.level = level
                                existing_student.department = department
                                existing_student.house = house
                                existing_student.registered_date = registered_date
                                existing_student.randomization_complete = True  # Mark as randomized
                                existing_student.save()
                                update_count += 1
                                self.stdout.write(f'Row {row_num}: Updated - {name} - {house.name}')
                            elif skip_duplicates:
                                self.stdout.write(f'Row {row_num}: Skipped duplicate - {name}')
                                skipped_count += 1
                            else:
                                self.stderr.write(
                                    f'Row {row_num}: Error - Student with matric number {matric_number} already exists')
                                error_count += 1
                        else:
                            # Create new student - mark as randomized since they have a house
                            try:
                                student = Student.objects.create(
                                    matric_number=matric_number,
                                    name=name,
                                    level=level,
                                    department=department,
                                    house=house,
                                    registered_date=registered_date,
                                    role='student',
                                    randomization_complete=True  # Auto-complete since they have house
                                )
                                success_count += 1
                                self.stdout.write(f'Row {row_num}: Created - {name} - {house.name}')
                            except IntegrityError as e:
                                if 'UNIQUE constraint failed' in str(e):
                                    if skip_duplicates:
                                        self.stdout.write(f'Row {row_num}: Skipped duplicate - {name}')
                                        skipped_count += 1
                                    else:
                                        self.stderr.write(
                                            f'Row {row_num}: Error - UNIQUE constraint failed: {matric_number}')
                                        error_count += 1
                                else:
                                    raise e

                    except Exception as e:
                        self.stderr.write(f'Row {row_num}: Error - {str(e)}')
                        error_count += 1

                # Summary
                self.stdout.write("\n" + "=" * 50)
                self.stdout.write("IMPORT SUMMARY:")
                self.stdout.write(f"Successful creations: {success_count}")
                self.stdout.write(f"Successful updates: {update_count}")
                self.stdout.write(f"Errors: {error_count}")
                self.stdout.write(f"Skipped: {skipped_count}")
                self.stdout.write(f"Total processed: {success_count + update_count + error_count + skipped_count}")

                if success_count + update_count > 0:
                    self.stdout.write(self.style.SUCCESS(f'Import completed successfully!'))
                else:
                    self.stdout.write(
                        self.style.WARNING(f'No records were imported. Use --update or --skip-duplicates flags.'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error reading CSV file: {str(e)}'))