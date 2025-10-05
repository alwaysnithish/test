from django.db import models
from django.utils import timezone

class Conversion(models.Model):
    """Track file conversions"""
    original_filename = models.CharField(max_length=255)
    original_format = models.CharField(max_length=50)
    target_format = models.CharField(max_length=50)
    converted_filename = models.CharField(max_length=255)
    file_size = models.IntegerField(help_text="Size in bytes")
    created_at = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.original_filename} → {self.target_format}"
