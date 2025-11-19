# apps/houses/models.py
from django.db import models
from django.core.validators import RegexValidator
from django.db.models import Sum

from apps.events.models import Score

hex_validator = RegexValidator(
    regex=r'^#(?:[0-9a-fA-F]{3}){1,2}$',
    message='Enter a valid hex color, e.g. #1a2b3c'
)


class House(models.Model):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True, blank=True, null=True)
    motto = models.TextField(blank=True, null=True)
    crest = models.ImageField(upload_to='house_crests/', blank=True, null=True)
    color_primary = models.CharField(max_length=7, validators=[hex_validator], default='#111827')
    color_secondary = models.CharField(max_length=7, validators=[hex_validator], default='#6b7280')
    whatsapp_link = models.CharField(max_length=250, blank=True, null=True)

    def __str__(self):
        return self.name

    def total_points(self):
        return Score.objects.filter(house=self).aggregate(total=Sum('points'))['total'] or 0