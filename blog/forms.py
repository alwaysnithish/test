from django import forms
from .models import BlogPost, Category, Tag

# Add to blog/forms.py

from .models import AuthorProfile

class AuthorProfileForm(forms.ModelForm):
    class Meta:
        model = AuthorProfile
        fields = ['bio', 'profile_picture', 'job_title', 'location', 
                  'website', 'twitter', 'facebook', 'linkedin', 'instagram']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Tell readers about yourself...'
            }),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
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
class BlogPostForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter tags separated by commas'
        }),
        help_text='Separate tags with commas'
    )
    
    class Meta:
        model = BlogPost
        fields = ['title', 'content', 'excerpt', 'thumbnail', 'category']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter post title'}),
            'excerpt': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Short description (auto-generated if left empty)'}),
            'thumbnail': forms.FileInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Populate tags_input with existing tags
            self.fields['tags_input'].initial = ', '.join([tag.name for tag in self.instance.tags.all()])
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # ✅ MUST save the instance first to get an ID
        if commit:
            instance.save()
            
            # ✅ NOW we can set many-to-many relationships
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
