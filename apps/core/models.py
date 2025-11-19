from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
import uuid


class CustomUserManager(BaseUserManager):
    def create_user(self, matric_number, **extra_fields):
        if not matric_number:
            # Generate a unique matric number if none provided
            matric_number = f"GEN_{uuid.uuid4().hex[:12]}"

        user = self.model(matric_number=matric_number, **extra_fields)
        user.save(using=self._db)
        return user

    def create_superuser(self, matric_number, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('house', None)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(matric_number, **extra_fields)


class Student(AbstractBaseUser, PermissionsMixin):
    matric_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    name = models.CharField(max_length=100)
    level = models.CharField(max_length=10, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    house = models.ForeignKey(
        'houses.House',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students'
    )
    registered_date = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    role = models.CharField(max_length=20, choices=[
        ('student', 'Student'),
        ('admin', 'Admin')
    ], default='student')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # Randomization specific fields
    randomized_at = models.DateTimeField(null=True, blank=True)
    randomization_complete = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'matric_number'
    REQUIRED_FIELDS = ['name']

    class Meta:
        indexes = [
            models.Index(fields=['matric_number']),
            models.Index(fields=['house']),
            models.Index(fields=['randomization_complete']),
        ]

    def clean(self):
        super().clean()

        # Only enforce house validation for students who have completed randomization
        if (self.role == 'student' and
                self.randomization_complete and
                not self.house):
            raise ValidationError("Students must belong to a house after randomization.")

        if self.role == 'admin' and self.house is not None:
            raise ValidationError("Admin users must not have a house.")

    def save(self, *args, **kwargs):
        # Generate matric number if not provided
        if not self.matric_number:
            self.matric_number = f"GEN_{uuid.uuid4().hex[:12]}"

        # Skip validation if only updating last_login
        update_fields = kwargs.get('update_fields')
        if update_fields and set(update_fields) == {'last_login'}:
            super().save(*args, **kwargs)
        else:
            self.clean()
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.matric_number}) - {self.role}"