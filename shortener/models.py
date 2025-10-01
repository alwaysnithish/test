
import string
import secrets
from django.db import models
from django.utils import timezone

def generate_short_code():
    """Generate a random 6-character alphanumeric code"""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(6))

def generate_secret_code():
    """Generate a random 8-character alphanumeric code for analytics"""
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(8))

class ShortURL(models.Model):
    original_url = models.URLField(max_length=2048)
    short_code = models.CharField(max_length=6, unique=True, default=generate_short_code)
    secret_code = models.CharField(max_length=8, unique=True, default=generate_secret_code)
    created_at = models.DateTimeField(default=timezone.now)
    clicks = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.short_code} -> {self.original_url}"
    
    class Meta:
        ordering = ['-created_at']

class ClickEvent(models.Model):
    short_url = models.ForeignKey(ShortURL, on_delete=models.CASCADE, related_name='click_events')
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    referrer = models.URLField(max_length=2048, blank=True, null=True)
    
    def __str__(self):
        return f"Click on {self.short_url.short_code} at {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']
