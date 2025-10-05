from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.urls import reverse
from ckeditor_uploader.fields import RichTextUploadingField
# Add this to your blog/models.py (after imports)

from django.db.models.signals import post_save
from django.dispatch import receiver

class AuthorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='author_profile')
    bio = models.TextField(max_length=500, blank=True, help_text="Short bio about the author")
    profile_picture = models.ImageField(upload_to='author_profiles/', blank=True, null=True)
    website = models.URLField(max_length=200, blank=True)
    twitter = models.CharField(max_length=100, blank=True, help_text="Twitter username (without @)")
    facebook = models.URLField(max_length=200, blank=True)
    linkedin = models.URLField(max_length=200, blank=True)
    instagram = models.CharField(max_length=100, blank=True, help_text="Instagram username (without @)")
    job_title = models.CharField(max_length=100, blank=True, help_text="e.g., Senior Developer, Content Writer")
    location = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Author Profile"
        verbose_name_plural = "Author Profiles"

    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_post_count(self):
        return self.user.blog_posts.filter(status='published').count()
    
    def get_latest_posts(self, limit=5):
        return self.user.blog_posts.filter(status='published').order_by('-published_at')[:limit]


# Auto-create profile when user is created
@receiver(post_save, sender=User)
def create_author_profile(sender, instance, created, **kwargs):
    if created:
        AuthorProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_author_profile(sender, instance, **kwargs):
    if hasattr(instance, 'author_profile'):
        instance.author_profile.save()

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class BlogPost(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = RichTextUploadingField()
    excerpt = models.TextField(max_length=300, blank=True, help_text="Short description for blog cards")
    thumbnail = models.ImageField(upload_to='blog_thumbnails/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while BlogPost.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Auto-generate excerpt from content if empty
        if not self.excerpt and self.content:
            # Strip HTML tags for excerpt
            import re
            text = re.sub('<[^<]+?>', '', self.content)
            self.excerpt = text[:297] + '...' if len(text) > 300 else text

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.title
