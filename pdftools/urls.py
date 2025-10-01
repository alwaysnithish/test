"""
URL configuration for pdftools project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.views.decorators.csrf import csrf_exempt

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

# Main project URLs
urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # Main PDF Tools page
    path('', views.index, name='index'),
    
    # Core PDF Operations
    path('extract-text/', csrf_exempt(views.extract_text), name='extract_text'),
    path('split-pdf/', csrf_exempt(views.split_pdf), name='split_pdf'),
    path('merge-pdfs/', csrf_exempt(views.merge_pdfs), name='merge_pdfs'),
    path('compress-pdf/', csrf_exempt(views.compress_pdf), name='compress_pdf'),
    path('add-watermark/', csrf_exempt(views.add_watermark), name='add_watermark'),
    path('rotate-pages/', csrf_exempt(views.rotate_pages), name='rotate_pages'),
    path('view-metadata/', csrf_exempt(views.view_metadata), name='view_metadata'),
    path('convert-to-images/', csrf_exempt(views.convert_to_images), name='convert_to_images'),

    # Utility endpoints
    path('download-file/', csrf_exempt(views.download_file), name='download_file'),
    path('pdf-info/', views.pdf_info, name='pdf_info'),
]
 #media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# URL Pattern Examples for reference:
# 
# Main page: /
# Extract text: /extract-text/
# Split PDF: /split-pdf/
# Merge PDFs: /merge-pdfs/
# Compress PDF: /compress-pdf/
# Add watermark: /add-watermark/
# Rotate pages: /rotate-pages/
# View metadata: /view-metadata/
# Convert to images: /convert-to-images/
# Download file: /download-file/
# PDF info: /pdf-info/