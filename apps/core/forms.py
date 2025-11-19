from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError
from .models import Student
from ..houses.models import House


# apps/core/forms.py (update StudentLoginForm)
class StudentLoginForm(forms.Form):
    matric_number = forms.CharField(
        label="Matric Number or Name",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white placeholder-gray-500 focus:border-accent focus:ring-1 focus:ring-accent',
            'placeholder': 'e.g., BU24CSC1001 or John Doe or admin',
            'autocomplete': 'username'
        })
    )
    house = forms.ModelChoiceField(
        label="Select Your House",
        queryset=House.objects.all(),
        empty_label="Choose your house...",
        required=False,  # Make house optional for admin
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white focus:border-accent focus:ring-1 focus:ring-accent',
        })
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        matric_number = cleaned_data.get('matric_number')
        house = cleaned_data.get('house')

        if not matric_number:
            return cleaned_data

        # Normalize input
        matric_number = matric_number.strip().upper()

        try:
            # Try to find student by matric number first
            student = Student.objects.get(matric_number=matric_number)
        except Student.DoesNotExist:
            # If not found by matric number, try by name (case-insensitive)
            try:
                student = Student.objects.get(name__iexact=matric_number)
            except Student.DoesNotExist:
                raise forms.ValidationError(
                    "No student found with this matric number or name. "
                    "Please check your credentials or complete house randomization first."
                )
            except Student.MultipleObjectsReturned:
                raise forms.ValidationError(
                    "Multiple students found with this name. "
                    "Please use your matric number instead."
                )

        # ADMIN LOGIC: If user is admin, skip house validation
        if student.role == 'admin' or student.is_staff or student.is_superuser:
            # Admin users don't need house selection
            if not student.is_active:
                raise forms.ValidationError("This admin account is inactive.")

            self.user = student
            return cleaned_data

        # STUDENT LOGIC: Regular students need house validation
        if not house:
            raise forms.ValidationError("House selection is required for students.")

        # Check if student belongs to the selected house
        if student.house != house:
            raise forms.ValidationError(
                f"Access denied! You don't belong to {house.name}. "
                f"Your assigned house is {student.house.name if student.house else 'not assigned yet'}."
            )

        # Check if student has completed randomization
        if not student.randomization_complete:
            # Auto-complete if they have a house
            if student.house:
                student.randomization_complete = True
                student.save()
            else:
                raise forms.ValidationError(
                    "Your account has not been assigned to a house yet. "
                    "Please complete the house randomization first."
                )

        if not student.is_active:
            raise forms.ValidationError("This account is inactive. Contact an admin.")

        self.user = student
        return cleaned_data

    def get_user(self):
        return getattr(self, 'user', None)


class StudentRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white placeholder-gray-500 focus:border-accent focus:ring-1 focus:ring-accent',
            'placeholder': 'Create a strong password',
            'autocomplete': 'new-password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white placeholder-gray-500 focus:border-accent focus:ring-1 focus:ring-accent',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password'
        })
    )

    class Meta:
        model = Student
        fields = ['matric_number', 'name', 'house']
        widgets = {
            'matric_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white placeholder-gray-500 focus:border-accent focus:ring-1 focus:ring-accent',
                'placeholder': 'e.g., MAT001',
                'autocomplete': 'username'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white placeholder-gray-500 focus:border-accent focus:ring-1 focus:ring-accent',
                'placeholder': 'Enter your full name',
                'autocomplete': 'name'
            }),
            'house': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white focus:border-accent focus:ring-1 focus:ring-accent'
            }),
        }

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def clean_matric_number(self):
        matric_number = self.cleaned_data.get('matric_number')
        if Student.objects.filter(matric_number=matric_number).exists():
            raise forms.ValidationError("A student with this matric number already exists.")
        return matric_number

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


# apps/core/forms.py
from django import forms
from .models import Student
from .house_assignment import HouseRandomizer


class HouseRandomizationForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white placeholder-gray-500 focus:border-accent focus:ring-1 focus:ring-accent',
            'placeholder': 'Enter your full name',
            'autocomplete': 'name'
        })
    )
    level = forms.CharField(
        max_length=10,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white placeholder-gray-500 focus:border-accent focus:ring-1 focus:ring-accent',
            'placeholder': 'e.g., 100, 200, 300',
            'autocomplete': 'off'
        })
    )
    department = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white placeholder-gray-500 focus:border-accent focus:ring-1 focus:ring-accent',
            'placeholder': 'Enter your department',
            'autocomplete': 'off'
        })
    )
    matric_number = forms.CharField(
        max_length=20,
        required=False,  # Make this optional
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white placeholder-gray-500 focus:border-accent focus:ring-1 focus:ring-accent',
            'placeholder': 'Enter your matric number (optional)',
            'autocomplete': 'off'
        })
    )

    def clean_name(self):
        name = self.cleaned_data['name'].strip().title()
        if not name:
            raise forms.ValidationError("Name is required")
        return name

    def clean_matric_number(self):
        matric_number = self.cleaned_data.get('matric_number', '').upper().strip()
        return matric_number if matric_number else None

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        level = cleaned_data.get('level')
        department = cleaned_data.get('department')
        matric_number = cleaned_data.get('matric_number')

        if name and level and department:
            # Check if student already exists with same details
            existing_student = HouseRandomizer.check_existing_assignment(
                name, level, department, matric_number
            )

            if existing_student:
                if matric_number and existing_student.matric_number != matric_number:
                    raise forms.ValidationError(
                        f"Student with name '{name}' already exists with different matric number. "
                        f"Please use the correct matric number or leave it blank."
                    )

        return cleaned_data