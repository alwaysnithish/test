from django.db import models
import uuid
import secrets

def generate_scan_id():
    """Generate a short, URL-friendly scan ID"""
    return secrets.token_urlsafe(8)

def generate_secret_code():
    """Generate a secret code for analytics"""
    return secrets.token_urlsafe(12)

class QRCodeScan(models.Model):
    # File storage
    uploaded_image = models.ImageField(upload_to='qr_uploads/', null=True, blank=True)
    image_url = models.URLField(max_length=500, null=True, blank=True)
    
    # Decoded content
    decoded_text = models.TextField()
    
    # Unique identifiers
    scan_id = models.CharField(max_length=20, unique=True, default=generate_scan_id, db_index=True)
    secret_code = models.CharField(max_length=30, unique=True, default=generate_secret_code, db_index=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    views_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Scan {self.scan_id} - {self.decoded_text[:50]}"
    
    def increment_views(self):
        """Increment the view counter"""
        self.views_count += 1
        self.save(update_fields=['views_count'])

class ScanEvent(models.Model):
    # Relationship to scan
    scan = models.ForeignKey(QRCodeScan, on_delete=models.CASCADE, related_name='events')
    
    # Event metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referrer = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Event for {self.scan.scan_id} at {self.timestamp}"
