from django.db import models


class Event(models.Model):
    EVENT_TYPES = [
        ('major', 'Major Event'),
        ('minor', 'Minor Event'),
        ('treasure', 'Treasure Hunt'),
        ('trivia', 'Trivia'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    # use a real date
    day = models.DateField()
    time = models.TimeField()
    type = models.CharField(max_length=20, choices=EVENT_TYPES)
    venue = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['day', 'time']

    def __str__(self):
        return f"{self.day.isoformat()}: {self.title}"


class Score(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    house = models.ForeignKey('houses.House', on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['event', 'house']