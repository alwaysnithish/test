from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, HttpResponse
from django.contrib import messages
from django.urls import reverse
from .models import ShortURL, ClickEvent
from .forms import URLForm
from .utils import get_client_ip
import qrcode
import io
import base64

def home(request):
    """Home view with URL shortening form"""
    short_url = None
    qr_code_data = None
    
    if request.method == 'POST':
        form = URLForm(request.POST)
        if form.is_valid():
            # Create new ShortURL object
            short_url = ShortURL.objects.create(
                original_url=form.cleaned_data['original_url']
            )
            
            # Generate QR code for the new short URL
            qr_code_data = generate_qr_code(request, short_url.short_code)
            
            messages.success(request, 'URL shortened successfully!')
    else:
        form = URLForm()
    
    return render(request, 'shortener/home.html', {
        'form': form,
        'short_url': short_url,
        'qr_code_data': qr_code_data,
    })

def redirect_url(request, short_code):
    """Redirect to original URL and log the click"""
    try:
        short_url = get_object_or_404(ShortURL, short_code=short_code)
        
        # Log the click event
        ClickEvent.objects.create(
            short_url=short_url,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],  # Limit length
            referrer=request.META.get('HTTP_REFERER', '')
        )
        
        # Increment click count
        short_url.clicks += 1
        short_url.save(update_fields=['clicks'])
        
        # Redirect to original URL
        return redirect(short_url.original_url)
        
    except ShortURL.DoesNotExist:
        raise Http404("Short URL not found")

def analytics(request, secret_code):
    """Show analytics for a URL using secret code"""
    try:
        short_url = get_object_or_404(ShortURL, secret_code=secret_code)
        click_events = short_url.click_events.all()[:100]  # Limit to recent 100 clicks
        
        # Generate QR code for the shortened URL
        qr_code_data = generate_qr_code(request, short_url.short_code)
        
        return render(request, 'shortener/analytics.html', {
            'short_url': short_url,
            'click_events': click_events,
            'qr_code_data': qr_code_data,
        })
        
    except ShortURL.DoesNotExist:
        raise Http404("Analytics page not found")

def generate_qr_code(request, short_code):
    """Generate QR code for a shortened URL and return base64 data"""
    try:
        # Get the full shortened URL
        short_url_obj = get_object_or_404(ShortURL, short_code=short_code)
        full_short_url = request.build_absolute_uri(
            reverse('shortener:redirect', args=[short_code])
        )
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(full_short_url)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for embedding in HTML
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{qr_code_data}"
        
    except Exception as e:
        # Return None if QR code generation fails
        print(f"QR code generation error: {e}")
        return None

def download_qr_code(request, short_code):
    """Download QR code as PNG file"""
    try:
        short_url_obj = get_object_or_404(ShortURL, short_code=short_code)
        full_short_url = request.build_absolute_uri(
            reverse('shortener:redirect', args=[short_code])
        )
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(full_short_url)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Create response with QR code
        response = HttpResponse(content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="qr_code_{short_code}.png"'
        
        img.save(response, 'PNG')
        return response
        
    except Exception as e:
        messages.error(request, f"Error generating QR code: {str(e)}")
        return redirect('shortener:home')
