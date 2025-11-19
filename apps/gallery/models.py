from django.db import models
from django.conf import settings
import os
from uuid import uuid4


def gallery_image_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid4().hex}.{ext}"
    return os.path.join('gallery', filename)


class Image(models.Model):
    file = models.ImageField(upload_to=gallery_image_path)
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    house = models.ForeignKey('houses.House', on_delete=models.CASCADE, null=True, blank=True)
    approved = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_images', blank=True)
    tags = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Image by {self.uploader.name} - {self.timestamp}"

    def like_count(self):
        return self.likes.count()

    def is_liked_by(self, user):
        return self.likes.filter(id=user.id).exists()


class DailyHighlight(models.Model):
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    day = models.IntegerField(choices=[(i, f'Day {i}') for i in range(1, 6)])
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-day', '-created_at']

    def __str__(self):
        return f"Day {self.day}: {self.title}"