# apps/core/backends.py
from django.contrib.auth.backends import ModelBackend, BaseBackend
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from gunicorn.config import User


class MatricNumberBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # Try to find user by matric_number
            user = UserModel.objects.get(
                Q(matric_number=username) |
                Q(matric_number=kwargs.get('matric_number', username))
            )
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            return None
        except Exception:
            return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None


# apps/core/backends.py
from django.contrib.auth.backends import ModelBackend
from .models import Student


class StrictStudentBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try to find by matric number first
            if username:
                student = Student.objects.get(matric_number=username.upper().strip())
                if student.check_password(password):
                    return student

            # If not found by matric, try other methods if needed
            return None

        except Student.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Student.objects.get(pk=user_id)
        except Student.DoesNotExist:
            return None


# apps/core/backends.py
from django.contrib.auth.backends import BaseBackend
from .models import Student


class HouseAuthenticationBackend(BaseBackend):
    """
    Authenticate by matric_number and optionally check house id.
    Note: If you want password checking, add it here and ensure the login form accepts password.
    """
    def authenticate(self, request, matric_number=None, house_id=None, **kwargs):
        if not matric_number:
            # sometimes Django passes username kw — accept that
            matric_number = kwargs.get('username') or kwargs.get('matric_number')

        try:
            student = Student.objects.get(matric_number=matric_number.upper().strip())

            # For admin/staff/superuser we skip house check
            if student.role == 'admin' or student.is_staff or student.is_superuser:
                return student

            # For students we can check the house if provided
            if house_id and student.house and str(student.house.id) == str(house_id):
                return student

            return None
        except Student.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Student.objects.get(pk=user_id)
        except Student.DoesNotExist:
            return None
