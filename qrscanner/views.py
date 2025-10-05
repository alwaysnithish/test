from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.core.files.storage import default_storage
from .models import QRCodeScan, ScanEvent
import cv2
from pyzbar.pyzbar import decode
import numpy as np
import urllib.request
from PIL import Image
import io

def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def decode_qr_from_image(image_path=None, image_url=None, uploaded_file=None):
    """
    Decode QR code from an image file path, URL, or uploaded file
    Returns decoded text or None
    """
    try:
        if uploaded_file:
            # Read uploaded file
            image_data = uploaded_file.read()
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif image_url:
            # Download image from URL
            with urllib.request.urlopen(image_url) as url_response:
                image_data = url_response.read()
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif image_path:
            # Read from file path
            img = cv2.imread(image_path)
        else:
            return None
        
        if img is None:
            return None
        
        # Decode QR codes
        decoded_objects = decode(img)
        
        if decoded_objects:
            # Return the first decoded QR code's data
            return decoded_objects[0].data.decode('utf-8')
        
        return None
    except Exception as e:
        print(f"Error decoding QR code: {e}")
        return None

def home(request):
    """Home view with upload/paste form"""
    context = {
        'result': None,
        'error': None,
    }
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('qr_image')
        image_url = request.POST.get('image_url', '').strip()
        
        decoded_text = None
        scan = None
        
        # Process uploaded file
        if uploaded_file:
            decoded_text = decode_qr_from_image(uploaded_file=uploaded_file)
            
            if decoded_text:
                # Save the scan
                scan = QRCodeScan.objects.create(
                    uploaded_image=uploaded_file,
                    decoded_text=decoded_text
                )
        
        # Process URL if no file uploaded
        elif image_url:
            decoded_text = decode_qr_from_image(image_url=image_url)
            
            if decoded_text:
                # Save the scan
                scan = QRCodeScan.objects.create(
                    image_url=image_url,
                    decoded_text=decoded_text
                )
        
        # Handle results
        if decoded_text and scan:
            context['result'] = {
                'decoded_text': decoded_text,
                'scan_id': scan.scan_id,
                'secret_code': scan.secret_code,
                'result_url': request.build_absolute_uri(f'/r/{scan.scan_id}/'),
                'analytics_url': request.build_absolute_uri(f'/a/{scan.secret_code}/'),
            }
        else:
            context['error'] = 'Could not decode QR code from the provided image. Please ensure it contains a valid QR code.'
    
    return render(request, 'scanner/home.html', context)

def result(request, scan_id):
    """Display decoded QR code result and track analytics"""
    scan = get_object_or_404(QRCodeScan, scan_id=scan_id)
    
    # Track the view
    scan.increment_views()
    
    # Create analytics event
    ScanEvent.objects.create(
        scan=scan,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        referrer=request.META.get('HTTP_REFERER', '')
    )
    
    context = {
        'scan': scan,
        'decoded_text': scan.decoded_text,
    }
    
    return render(request, 'scanner/result.html', context)

def analytics(request, secret_code):
    """Display analytics for a scan (private, requires secret code)"""
    scan = get_object_or_404(QRCodeScan, secret_code=secret_code)
    
    # Get all events for this scan
    events = scan.events.all()
    
    context = {
        'scan': scan,
        'events': events,
        'total_views': scan.views_count,
    }
    
    return render(request, 'scanner/analytics.html', context)
