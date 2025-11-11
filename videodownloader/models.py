from django.db import models
from django.utils import timezone

class DownloadLog(models.Model):
    DOWNLOAD_STATUS = (
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('pending', 'Pending')
    )

    url = models.URLField(max_length=500)
    platform = models.CharField(max_length=20)
    status = models.CharField(max_length=10, choices=DOWNLOAD_STATUS)
    file_path = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    error_message = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['platform']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.platform} - {self.status}"

# Create your models here.