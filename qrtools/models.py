"""
QR Tools Models - Professional QR Code Management System
Features: Dynamic QR, Analytics, Profile Cards, Bulk Generation
"""

from django.db import models
from django.utils import timezone
from django.urls import reverse
import uuid
import secrets
import string
from django.core.validators import URLValidator, EmailValidator


def generate_short_code(length=5):
    """Generate unique 5-character code for QR analytics"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))


class QRCode(models.Model):
    """Main QR Code model with analytics support"""
    
    QR_TYPES = [
        ('url', 'Website URL'),
        ('vcard', 'Contact Card (vCard)'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('phone', 'Phone Number'),
        ('wifi', 'WiFi Network'),
        ('upi', 'UPI Payment'),
        ('location', 'Location/Address'),
        ('text', 'Plain Text'),
        ('whatsapp', 'WhatsApp'),
        ('profile', 'Profile Card'),
    ]
    
    FRAME_STYLES = [
        ('none', 'No Frame'),
        ('square', 'Square Frame'),
        ('rounded', 'Rounded Frame'),
        ('circle', 'Circle Frame'),
        ('badge', 'Badge Frame'),
        ('scan-me', 'Scan Me Frame'),
        ('modern', 'Modern Frame'),
        ('vintage', 'Vintage Frame'),
        ('neon', 'Neon Frame'),
        ('minimal', 'Minimal Frame'),
    ]
    
    PATTERN_STYLES = [
        ('square', 'Square'),
        ('dots', 'Dots'),
        ('rounded', 'Rounded'),
        ('classy', 'Classy'),
        ('classy-rounded', 'Classy Rounded'),
        ('extra-rounded', 'Extra Rounded'),
        ('fluid', 'Fluid'),
    ]
    
    EYE_STYLES = [
        ('square', 'Square'),
        ('circle', 'Circle'),
        ('rounded', 'Rounded'),
        ('leaf', 'Leaf'),
        ('flower', 'Flower'),
    ]
    
    # Basic Information
    analytics_code = models.CharField(max_length=5, unique=True, db_index=True)
    analytics_key = models.CharField(max_length=10, unique=True, db_index=True)  # NEW: Private analytics
    qr_type = models.CharField(max_length=20, choices=QR_TYPES, default='url')
    
    # Content Data
    content_data = models.JSONField(default=dict, help_text="Structured data for QR content")
    final_url = models.URLField(max_length=2000, blank=True, help_text="Final generated URL/data")
    
    # Design Settings
    primary_color = models.CharField(max_length=7, default='#000000')
    background_color = models.CharField(max_length=7, default='#FFFFFF')
    gradient_enabled = models.BooleanField(default=False)
    gradient_color = models.CharField(max_length=7, blank=True)
    gradient_type = models.CharField(max_length=20, default='linear', choices=[
        ('linear', 'Linear'),
        ('radial', 'Radial'),
    ])
    
    # Pattern & Frame
    frame_style = models.CharField(max_length=20, choices=FRAME_STYLES, default='none')
    pattern_style = models.CharField(max_length=20, choices=PATTERN_STYLES, default='square')
    eye_style = models.CharField(max_length=20, choices=EYE_STYLES, default='square')
    
    # Logo/Image
    has_logo = models.BooleanField(default=False)
    logo_url = models.URLField(blank=True)
    logo_shape = models.CharField(max_length=10, choices=[
        ('square', 'Square'),
        ('circle', 'Circle'),
        ('rounded', 'Rounded'),  # NEW OPTION
    ],  default='square')
    logo_size = models.IntegerField(default=20, help_text="Logo size percentage")
    logo_padding = models.IntegerField(default=30, help_text="Padding around logo percentage")  # NEW
    logo_border = models.BooleanField(default=True, help_text="Add border around logo")  # NEW
    # QR Settings
    size = models.IntegerField(default=300)
    error_correction = models.CharField(max_length=1, default='M', choices=[
        ('L', 'Low (7%)'),
        ('M', 'Medium (15%)'),
        ('Q', 'Quartile (25%)'),
        ('H', 'High (30%)'),
    ])
    
    # Dynamic QR Support
    is_dynamic = models.BooleanField(default=True)
    redirect_url = models.URLField(max_length=2000, blank=True, help_text="Actual redirect URL for dynamic QR")
    
    # Image Storage
    qr_image = models.TextField(help_text="Base64 encoded QR image")
    qr_image_url = models.URLField(blank=True, help_text="Cloudinary URL if uploaded")
    
    # Organization
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    folder_name = models.CharField(max_length=100, blank=True, db_index=True)
    tags = models.JSONField(default=list, blank=True)
    
    # Analytics
    total_scans = models.IntegerField(default=0)
    last_scanned = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['analytics_code'], name='qrtools_qrc_analyti_351be0_idx'),
            models.Index(fields=['analytics_key'], name='qrtools_qrc_analyti_9dfb1c_idx'),
            models.Index(fields=['folder_name'], name='qrtools_qrc_folder__c9bb2a_idx'),
            models.Index(fields=['qr_type'], name='qrtools_qrc_qr_type_4c83fe_idx'),
            models.Index(fields=['-created_at'], name='qrtools_qrc_created_851a42_idx'),
        ]
    
    def save(self, *args, **kwargs):
        if not self.analytics_code:
        # Generate unique analytics code
            while True:
                code = generate_short_code()
                if not QRCode.objects.filter(analytics_code=code).exists():
                    self.analytics_code = code
                    break
    
        if not self.analytics_key:  # NEW
        # Generate unique private analytics key
            while True:
                key = generate_short_code(length=10)
                if not QRCode.objects.filter(analytics_key=key).exists():
                    self.analytics_key = key
                    break
    
        super().save(*args, **kwargs)
    
    def get_analytics_url(self):
        """Get analytics dashboard URL"""
        return reverse('qrtools:analytics', kwargs={'key': self.analytics_key})
    
    def get_redirect_url(self):
        """Get the redirect URL for dynamic QR"""
        return reverse('qrtools:qr_redirect', kwargs={'code': self.analytics_code})
    
    def increment_scan(self):
        """Increment scan count"""
        self.total_scans += 1
        self.last_scanned = timezone.now()
        self.save(update_fields=['total_scans', 'last_scanned'])
    
    def __str__(self):
        return f"{self.title or self.qr_type} - {self.analytics_code}"


class ProfileCard(models.Model):
    """Custom profile cards with beautiful landing pages"""
    
    qr_code = models.OneToOneField(QRCode, on_delete=models.CASCADE, related_name='profile_card')
    
    # Personal Information
    full_name = models.CharField(max_length=200)
    title = models.CharField(max_length=200, blank=True)
    company = models.CharField(max_length=200, blank=True)
    tagline = models.CharField(max_length=300, blank=True)
    
    # Contact Information
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    
    # Social Links
    website = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    github = models.URLField(blank=True)
    youtube = models.URLField(blank=True)
    
    # Additional Info
    bio = models.TextField(blank=True)
    address = models.TextField(blank=True)
    birthday = models.DateField(null=True, blank=True)
    
    # Media
    profile_photo = models.URLField(blank=True)
    cover_photo = models.URLField(blank=True)
    
    # Custom Fields (flexible additional data)
    custom_fields = models.JSONField(default=list, blank=True, help_text="[{label, value, icon}]")
    
    # Page Settings
    theme_color = models.CharField(max_length=7, default='#667eea')
    layout_style = models.CharField(max_length=20, default='modern', choices=[
        ('modern', 'Modern'),
        ('minimal', 'Minimal'),
        ('creative', 'Creative'),
        ('professional', 'Professional'),
        ('gradient', 'Gradient'),
    ])
    
    # Analytics
    page_views = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def get_absolute_url(self):
        """Get profile card landing page URL"""
        return reverse('profile_card', kwargs={'code': self.qr_code.analytics_code})
    
    def increment_view(self):
        """Increment page view count"""
        self.page_views += 1
        self.save(update_fields=['page_views'])
    
    def __str__(self):
        return f"Profile: {self.full_name}"


class QRScan(models.Model):
    qr_code = models.ForeignKey(QRCode, on_delete=models.CASCADE, related_name='scans')
    scanned_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_type = models.CharField(max_length=20, default='desktop')
    browser = models.CharField(max_length=50, default='unknown')
    user_agent = models.TextField(blank=True, null=True)
    country = models.CharField(max_length=100, default='Unknown')
    region = models.CharField(max_length=100, default='Unknown')
    city = models.CharField(max_length=100, default='Unknown')
    latitude = models.CharField(max_length=20, default='0')
    longitude = models.CharField(max_length=20, default='0')
    referrer = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-scanned_at']
    
    def __str__(self):
        return f"Scan at {self.scanned_at} - {self.device_type}"


class BulkQRBatch(models.Model):
    """Batch generation of multiple QR codes"""
    
    batch_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Batch Settings
    total_codes = models.IntegerField(default=0)
    generated_codes = models.IntegerField(default=0)
    
    # Shared Design Settings (JSON)
    design_template = models.JSONField(default=dict)
    
    # Status
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Batch: {self.title} ({self.generated_codes}/{self.total_codes})"


class QRTemplate(models.Model):
    """Pre-designed templates for different industries"""
    
    INDUSTRY_CHOICES = [
        ('restaurant', 'Restaurant & Food'),
        ('retail', 'Retail & Shopping'),
        ('events', 'Events & Entertainment'),
        ('business', 'Business & Corporate'),
        ('healthcare', 'Healthcare'),
        ('education', 'Education'),
        ('real-estate', 'Real Estate'),
        ('hospitality', 'Hospitality'),
        ('technology', 'Technology'),
        ('general', 'General Purpose'),
    ]
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField()
    industry = models.CharField(max_length=30, choices=INDUSTRY_CHOICES)
    
    # Template Design (JSON)
    design_config = models.JSONField(default=dict, help_text="Complete design configuration")
    
    # Preview
    preview_image = models.URLField(blank=True)
    
    # Metadata
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['industry', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.industry})"
