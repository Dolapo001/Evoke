from django import forms
from apps.events.models import Score, Event
from apps.gallery.models import Image
from apps.houses.models import House


class ScoreForm(forms.ModelForm):
    class Meta:
        model = Score
        fields = ['event', 'house', 'points']
        widgets = {
            'event': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white focus:border-accent focus:ring-1 focus:ring-accent'
            }),
            'house': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white focus:border-accent focus:ring-1 focus:ring-accent'
            }),
            'points': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white focus:border-accent focus:ring-1 focus:ring-accent',
                'min': '0',
                'step': '1'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['event'].queryset = Event.objects.all()
        self.fields['house'].queryset = House.objects.all()

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'day', 'time', 'type', 'venue']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white focus:border-accent focus:ring-1 focus:ring-accent'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white focus:border-accent focus:ring-1 focus:ring-accent',
                'rows': 4
            }),
            'day': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white focus:border-accent focus:ring-1 focus:ring-accent',
                'type': 'date'  # This is important
            }),
            'time': forms.TimeInput(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white focus:border-accent focus:ring-1 focus:ring-accent',
                'type': 'time'
            }),
            'type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white focus:border-accent focus:ring-1 focus:ring-accent'
            }),
            'venue': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white focus:border-accent focus:ring-1 focus:ring-accent'
            }),
        }


class ImageApprovalForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ['approved']