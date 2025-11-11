
from django import forms
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

class URLForm(forms.Form):
    original_url = forms.URLField(
        label='Enter URL to shorten',
        max_length=2048,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://example.com/very-long-url',
            'required': True,
        })
    )
    
    def clean_original_url(self):
        url = self.cleaned_data['original_url']
        
        # Ensure URL has a scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Validate URL format
        validator = URLValidator()
        try:
            validator(url)
        except ValidationError:
            raise forms.ValidationError('Please enter a valid URL')
        
        return url
