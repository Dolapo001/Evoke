from django import forms
from .models import Image


class ImageUploadForm(forms.ModelForm):
    class Meta:
        model = Image
        fields = ['file', 'description', 'tags']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'hidden',
                'accept': 'image/*',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white placeholder-gray-500 focus:border-accent focus:ring-1 focus:ring-accent',
                'placeholder': 'Describe this memory... (optional)',
                'rows': 4
            }),
            'tags': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-black/30 border border-red-800/50 rounded-lg text-white placeholder-gray-500 focus:border-accent focus:ring-1 focus:ring-accent',
                'placeholder': 'football, team, celebration, etc. (optional)'
            }),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Validate file size (10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be less than 10MB.")

            # Validate file type
            valid_extensions = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']
            extension = file.name.split('.')[-1].lower()
            if extension not in valid_extensions:
                raise forms.ValidationError(
                    "Unsupported file format. Please upload an image file (JPG, PNG, GIF, WEBP, BMP).")

            # Validate image dimensions (optional)
            # You can add dimension validation here if needed

        return file

    def clean_description(self):
        description = self.cleaned_data.get('description', '').strip()
        if description and len(description) > 500:
            raise forms.ValidationError("Description must be 500 characters or less.")
        return description

    def clean_tags(self):
        tags = self.cleaned_data.get('tags', '').strip()
        if tags:
            # Clean up tags - remove extra spaces and validate format
            tags = ', '.join([tag.strip() for tag in tags.split(',') if tag.strip()])
            if len(tags) > 200:
                raise forms.ValidationError("Tags must be 200 characters or less.")
        return tags