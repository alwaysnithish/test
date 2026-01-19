"""
QR Tools Views - Enhanced Professional Implementation
High-quality views with improved security, error handling, and validation.
"""

import qrcode
import cloudinary.uploader
from io import BytesIO
import base64
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.conf import settings
import json
import logging
from functools import wraps
import time

logger = logging.getLogger(__name__)

# Rate limiting decorator (simple implementation)
def rate_limit(max_requests=10, window=60):
    """Simple rate limiting decorator"""
    requests = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            ip = get_client_ip(request)
            now = time.time()
            
            # Clean old entries
            requests[ip] = [req_time for req_time in requests.get(ip, []) 
                           if now - req_time < window]
            
            # Check rate limit
            if len(requests.get(ip, [])) >= max_requests:
                return JsonResponse({
                    'error': f'Rate limit exceeded. Max {max_requests} requests per {window} seconds.'
                }, status=429)
            
            # Add current request
            requests.setdefault(ip, []).append(now)
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@ensure_csrf_cookie
def qr_main_view(request):
    """
    Main view that renders the QR code generator and scanner page.
    SEO optimized with proper meta tags and structured content.
    """
    context = {
        'page_title': 'QR Code Generator & Scanner - Free Online QR Tools',
        'meta_description': 'Create QR codes from text, URLs, or files. Scan QR codes using your camera or upload images. Free online QR code generator and scanner with analytics.',
        'meta_keywords': 'qr code generator, qr scanner, free qr code, qr code creator, scan qr code, qr code maker, online qr generator',
    }
    return render(request, 'qrtools/qr_main.html', context)


@require_http_methods(["POST"])
@rate_limit(max_requests=20, window=60)
def generate_qr_code(request):
    """
    API endpoint to generate QR code from text or URL.
    
    Security improvements:
    - CSRF protection (removed @csrf_exempt)
    - Rate limiting
    - Input validation
    - Size limits
    """
    try:
        # Parse JSON data from request
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        
        qr_data = data.get('data', '').strip()
        size = data.get('size', 'medium')
        error_correction = data.get('error_correction', 'M')
        
        # Validation
        if not qr_data:
            return JsonResponse({'error': 'No data provided'}, status=400)
        
        # Check data length (QR codes have limits)
        if len(qr_data) > 4296:  # Max alphanumeric capacity
            return JsonResponse({
                'error': 'Data too long. Maximum 4,296 characters allowed.'
            }, status=400)
        
        # Validate size parameter
        if size not in ['small', 'medium', 'large']:
            size = 'medium'
        
        # Validate error correction parameter
        if error_correction not in ['L', 'M', 'Q', 'H']:
            error_correction = 'M'
        
        # Map size to box_size
        size_map = {
            'small': 8,
            'medium': 10,
            'large': 12
        }
        box_size = size_map[size]
        
        # Map error correction level
        error_map = {
            'L': qrcode.constants.ERROR_CORRECT_L,
            'M': qrcode.constants.ERROR_CORRECT_M,
            'Q': qrcode.constants.ERROR_CORRECT_Q,
            'H': qrcode.constants.ERROR_CORRECT_H,
        }
        error_level = error_map[error_correction]
        
        # Create QR code instance with professional settings
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_level,
            box_size=box_size,
            border=4,
        )
        
        # Add data to QR code
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create an image from the QR code with professional colors
        img = qr.make_image(fill_color="#1e3a8a", back_color="white")
        
        # Convert image to base64 string for frontend display
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        logger.info(f"QR code generated successfully for data length: {len(qr_data)}")
        
        return JsonResponse({
            'success': True,
            'qr_image': f'data:image/png;base64,{img_str}',
            'data_length': len(qr_data),
            'size': size,
            'error_correction': error_correction
        })
        
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': 'Failed to generate QR code. Please try again.'
        }, status=500)


@require_http_methods(["POST"])
@rate_limit(max_requests=5, window=60)  # Stricter rate limit for uploads
def upload_file_to_cloudinary(request):
    """
    API endpoint to upload files to Cloudinary and generate QR code from the file URL.
    
    Enhanced with:
    - Better error handling
    - File validation
    - Cloudinary timeout handling
    - CSRF protection
    """
    try:
        # Check if file is in request
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        uploaded_file = request.FILES['file']
        
        # Validate file size (10MB limit)
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 10 * 1024 * 1024)
        if uploaded_file.size > max_size:
            return JsonResponse({
                'error': f'File too large. Maximum size is {max_size / (1024 * 1024):.0f}MB'
            }, status=400)
        
        # Validate file type
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'video/mp4', 'video/mpeg', 'video/quicktime',
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]
        
        if uploaded_file.content_type not in allowed_types:
            return JsonResponse({
                'error': 'Unsupported file type. Please upload images, videos, or documents.'
            }, status=400)
        
        # Validate filename (security check)
        if not uploaded_file.name or len(uploaded_file.name) > 255:
            return JsonResponse({'error': 'Invalid filename'}, status=400)
        
        logger.info(f"Uploading file: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        # Upload file to Cloudinary with error handling
        try:
            upload_result = cloudinary.uploader.upload(
                uploaded_file,
                folder='21k_qr_files',
                resource_type='auto',
                timeout=60,
                chunk_size=6000000  # 6MB chunks for large files
            )
        except cloudinary.exceptions.Error as e:
            logger.error(f"Cloudinary upload error: {str(e)}")
            return JsonResponse({
                'error': 'File upload failed. Please try again or use a smaller file.'
            }, status=500)
        
        # Get the public URL from Cloudinary
        file_url = upload_result.get('secure_url')
        
        if not file_url:
            return JsonResponse({
                'error': 'Failed to get file URL from Cloudinary'
            }, status=500)
        
        # Get additional file info
        file_format = upload_result.get('format', 'unknown')
        file_type = upload_result.get('resource_type', 'unknown')
        cloudinary_size = upload_result.get('bytes', uploaded_file.size)
        
        # Generate QR code from the file URL
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=4,
            )
            
            qr.add_data(file_url)
            qr.make(fit=True)
            
            # Create QR code image with professional colors
            img = qr.make_image(fill_color="#1e3a8a", back_color="white")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
        
        except Exception as e:
            logger.error(f"QR generation error: {str(e)}")
            return JsonResponse({
                'error': 'Failed to generate QR code from file URL'
            }, status=500)
        
        logger.info(f"File uploaded successfully: {uploaded_file.name}")
        
        return JsonResponse({
            'success': True,
            'file_url': file_url,
            'qr_image': f'data:image/png;base64,{img_str}',
            'file_name': uploaded_file.name,
            'file_size': uploaded_file.size,
            'file_format': file_format,
            'file_type': file_type,
            'cloudinary_size': cloudinary_size
        })
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}", exc_info=True)
        return JsonResponse({
            'error': 'Upload failed. Please try again.'
        }, status=500)
