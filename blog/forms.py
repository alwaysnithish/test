from django import forms
from .models import BlogPost, Category, Tag

# Add to blog/forms.py

from .models import AuthorProfile
from .models import NewsletterSubscriber

class NewsletterForm(forms.ModelForm):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your email address',
                'required': True
            })
        }
from django import forms
from .models import BlogPost, Category, Tag, AuthorProfile

from django import forms
from .models import BlogPost, Category, Tag, AuthorProfile

class AuthorProfileForm(forms.ModelForm):
    # Add a file input for profile picture (not a model field)
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label='Profile Picture'
    )
    
    class Meta:
        model = AuthorProfile
        # IMPORTANT: Don't include profile_picture_data, profile_picture_name, or profile_picture_type
        # These are handled programmatically
        fields = ['bio', 'job_title', 'location', 
                  'website', 'twitter', 'facebook', 'linkedin', 'instagram']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Tell readers about yourself...'
            }),
            'job_title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Content Writer, Developer'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., New York, USA'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control', 
                'placeholder': 'https://yourwebsite.com'
            }),
            'twitter': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'username (without @)'
            }),
            'facebook': forms.URLInput(attrs={
                'class': 'form-control', 
                'placeholder': 'https://facebook.com/yourprofile'
            }),
            'linkedin': forms.URLInput(attrs={
                'class': 'form-control', 
                'placeholder': 'https://linkedin.com/in/yourprofile'
            }),
            'instagram': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'username (without @)'
            }),
        }
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle profile picture upload
        profile_picture = self.cleaned_data.get('profile_picture')
        if profile_picture:
            # Read the file data
            instance.profile_picture_data = profile_picture.read()
            instance.profile_picture_name = profile_picture.name
            instance.profile_picture_type = profile_picture.content_type
        
        if commit:
            instance.save()
        
        return instance


class BlogPostForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter tags separated by commas'
        }),
        help_text='Separate tags with commas'
    )
    
    # Add a file input for thumbnail (not a model field)
    thumbnail = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label='Thumbnail Image'
    )
    
    class Meta:
        model = BlogPost
        # IMPORTANT: Don't include thumbnail_data, thumbnail_name, or thumbnail_type
        # These are handled programmatically
        fields = ['title', 'content', 'excerpt', 'category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter post title'}),
            'excerpt': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Short description (auto-generated if left empty)'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Populate tags_input with existing tags
            self.fields['tags_input'].initial = ', '.join([tag.name for tag in self.instance.tags.all()])
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Handle thumbnail upload
        thumbnail = self.cleaned_data.get('thumbnail')
        if thumbnail:
            # Read the file data
            instance.thumbnail_data = thumbnail.read()
            instance.thumbnail_name = thumbnail.name
            instance.thumbnail_type = thumbnail.content_type
        
        if commit:
            instance.save()
            
            # Handle tags
            tags_input = self.cleaned_data.get('tags_input', '')
            if tags_input:
                tag_names = [name.strip() for name in tags_input.split(',') if name.strip()]
                tags = []
                for tag_name in tag_names:
                    tag, created = Tag.objects.get_or_create(name=tag_name)
                    tags.append(tag)
                instance.tags.set(tags)
            else:
                instance.tags.clear()
        
        return instance
