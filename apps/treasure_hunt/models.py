from datetime import timezone

from django.db import models
from django.conf import settings


class QRCode(models.Model):
    code = models.CharField(max_length=100, unique=True)
    clue = models.TextField()
    points = models.IntegerField(default=10)
    location_name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.location_name} - {self.code}"


class QRScan(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    qr_code = models.ForeignKey(QRCode, on_delete=models.CASCADE)
    scanned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'qr_code']

    def __str__(self):
        return f"{self.student.name} scanned {self.qr_code.location_name}"


class TreasureHuntProgress(models.Model):
    student = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_scans = models.IntegerField(default=0)
    total_points = models.IntegerField(default=0)
    last_scan = models.DateTimeField(null=True, blank=True)

    def update_progress(self, qr_code):
        self.total_scans += 1
        self.total_points += qr_code.points
        self.last_scan = timezone.now()
        self.save()