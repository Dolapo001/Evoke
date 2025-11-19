# apps/core/house_assignment.py
import random
import uuid
from django.db.models import Count
from django.utils import timezone
from .models import Student
from apps.houses.models import House


class HouseRandomizer:
    """Fair house randomization system"""

    # House WhatsApp links
    HOUSE_LINKS = {
        "stark": "https://chat.whatsapp.com/CCbJxRObbPE9W4IREn6YBY",
        "baratheon": "https://chat.whatsapp.com/DhvLw6Za0hKJLlCYkxz70b",
        "greyjoy": "https://chat.whatsapp.com/GLApCfuhlEoEnN7WHsL2gP",
        "lannister": "https://chat.whatsapp.com/LeIXiKaJwJGCYyzZoNEq11",
        "targaryen": "https://chat.whatsapp.com/I7b2jBIKNKAAzuWPAGDs90",
    }

    HOUSE_DISPLAY_NAMES = {
        "stark": "House Stark of Winterfell",
        "baratheon": "House Baratheon of Storm's End",
        "greyjoy": "House Greyjoy of Pyke",
        "lannister": "House Lannister of Casterly Rock",
        "targaryen": "House Targaryen of Dragonstone",
    }

    HOUSE_DESCRIPTIONS = {
        "stark": "Winter is Coming - House of Honor and Winter",
        "baratheon": "Ours is the Fury - House of Strength and Leadership",
        "greyjoy": "We Do Not Sow - House of the Sea and Ambition",
        "lannister": "Hear Me Roar - House of Wealth and Power",
        "targaryen": "Fire and Blood - House of Dragons and Legacy",
    }

    HOUSE_COLORS = {
        "stark": "bg-gray-800 text-white",
        "baratheon": "bg-yellow-600 text-black",
        "greyjoy": "bg-gray-600 text-white",
        "lannister": "bg-red-700 text-white",
        "targaryen": "bg-red-900 text-white",
    }

    @classmethod
    def extract_house_key(cls, house_name):
        """Extract the house key from full house name"""
        if not house_name:
            return ""

        house_name_lower = house_name.lower()

        # Map full names to keys
        house_mapping = {
            "house stark of winterfell": "stark",
            "house baratheon of storm's end": "baratheon",
            "house baratheon of storm’s end": "baratheon",  # handle different apostrophe
            "house greyjoy of pyke": "greyjoy",
            "house lannister of casterly rock": "lannister",
            "house targaryen of dragonstone": "targaryen",
        }

        # Try exact match first
        if house_name_lower in house_mapping:
            return house_mapping[house_name_lower]

        # Fallback: extract by common patterns
        if "stark" in house_name_lower:
            return "stark"
        elif "baratheon" in house_name_lower:
            return "baratheon"
        elif "greyjoy" in house_name_lower:
            return "greyjoy"
        elif "lannister" in house_name_lower:
            return "lannister"
        elif "targaryen" in house_name_lower:
            return "targaryen"

        return house_name_lower

    @classmethod
    def assign_house(cls, student):
        """Assign a house to student using fair randomization"""
        # ... keep your existing assign_house method unchanged ...
        if student.house and student.randomization_complete:
            return student.house

        house_counts = House.objects.annotate(
            student_count=Count('students')
        ).order_by('student_count')

        min_count = house_counts.first().student_count
        smallest_houses = [h for h in house_counts if h.student_count == min_count]
        chosen_house = random.choice(smallest_houses)

        student.house = chosen_house
        student.randomized_at = timezone.now()
        student.randomization_complete = True
        student.save()

        return chosen_house

    @classmethod
    def get_house_stats(cls):
        """Get statistics for all houses"""
        return House.objects.annotate(
            student_count=Count('students')
        ).order_by('student_count')

    @classmethod
    def get_house_info(cls, house_name):
        """Get complete house information from house name"""
        house_key = cls.extract_house_key(house_name)

        return {
            'name': cls.HOUSE_DISPLAY_NAMES.get(house_key, house_name),
            'description': cls.HOUSE_DESCRIPTIONS.get(house_key, ''),
            'whatsapp_link': cls.HOUSE_LINKS.get(house_key, '#'),
            'color_class': cls.HOUSE_COLORS.get(house_key, 'bg-gray-500'),
            'code': house_key
        }

    @classmethod
    def check_existing_assignment(cls, name, level, department, matric_number=None):
        """Check if student is already assigned to a house"""
        # ... keep your existing check_existing_assignment method unchanged ...
        try:
            if matric_number:
                student = Student.objects.get(
                    matric_number=matric_number.upper().strip(),
                    randomization_complete=True
                )
                return student

            student = Student.objects.get(
                name__iexact=name.strip(),
                level=level,
                department__iexact=department,
                randomization_complete=True
            )
            return student
        except Student.DoesNotExist:
            pass
        except Student.MultipleObjectsReturned:
            students = Student.objects.filter(
                name__iexact=name.strip(),
                level=level,
                department__iexact=department,
                randomization_complete=True
            )
            return students.first() if students.exists() else None

        return None

    @classmethod
    def generate_matric_number(cls):
        """Generate a unique matric number for students without one"""
        return f"RND{uuid.uuid4().hex[:6].upper()}"