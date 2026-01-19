"""
QR Tools App URLs Configuration
This file defines all URL patterns for the QR code generator and scanner app.
"""

from django.urls import path
from . import views

# Namespace for this app's URLs
app_name = 'qrtools'

urlpatterns = [
    # Main page with both generator and scanner
    path('', views.qr_main_view, name='qr_main'),
    
    # API endpoint for generating QR codes
    path('api/generate-qr/', views.generate_qr_code, name='generate_qr'),
    
    # API endpoint for uploading files to Cloudinary
    path('api/upload-file/', views.upload_file_to_cloudinary, name='upload_file'),
]
