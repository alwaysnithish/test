# image_resizer/views.py

import io
import os
import tempfile
from PIL import Image, ImageEnhance, ExifTags
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.views.decorators.http import require_http_methods
import piexif
from datetime import datetime, timedelta
import threading
import time

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Temporary file storage for cleanup
temp_files = {}

def cleanup_temp_files():
    """Background thread to cleanup files older than 5 minutes"""
    while True:
        current_time = datetime.now()
        files_to_delete = []
        
        for filepath, timestamp in list(temp_files.items()):
            if current_time - timestamp > timedelta(minutes=5):
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    files_to_delete.append(filepath)
                except Exception as e:
                    print(f"Error cleaning up {filepath}: {e}")
        
        for filepath in files_to_delete:
            temp_files.pop(filepath, None)
        
        time.sleep(60)  # Check every minute

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_temp_files, daemon=True)
cleanup_thread.start()

def correct_image_orientation(img):
    """Correct image orientation based on EXIF data"""
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == 'Orientation':
                break
        
        exif = img._getexif()
        if exif is not None:
            orientation_value = exif.get(orientation)
            
            if orientation_value == 3:
                img = img.rotate(180, expand=True)
            elif orientation_value == 6:
                img = img.rotate(270, expand=True)
            elif orientation_value == 8:
                img = img.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError):
        pass
    
    return img

def enhance_image_quality(img):
    """Apply enhancement using Pillow"""
    # Convert to RGB if necessary
    if img.mode not in ['RGB', 'RGBA']:
        if img.mode == 'P':
            img = img.convert('RGBA')
        else:
            img = img.convert('RGB')
    
    # Enhance sharpness
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.5)
    
    # Enhance contrast slightly
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.1)
    
    # Enhance color
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(1.05)
    
    return img

def resize_image(img, width=None, height=None, percentage=None, maintain_aspect=True):
    """Resize image with various options - returns exact dimensions requested"""
    original_width, original_height = img.size
    
    if percentage:
        # Calculate exact dimensions based on percentage
        width = int(original_width * percentage / 100)
        height = int(original_height * percentage / 100)
    elif width and not height and maintain_aspect:
        # Calculate height to maintain aspect ratio
        height = int(original_height * (width / original_width))
    elif height and not width and maintain_aspect:
        # Calculate width to maintain aspect ratio
        width = int(original_width * (height / original_height))
    elif width and height and maintain_aspect:
        # Calculate dimensions to fit within bounds while maintaining aspect
        aspect_ratio = original_width / original_height
        target_aspect = width / height
        
        if aspect_ratio > target_aspect:
            # Width is the limiting factor
            height = int(width / aspect_ratio)
        else:
            # Height is the limiting factor
            width = int(height * aspect_ratio)
    elif not width and not height:
        return img
    
    # Ensure we have valid dimensions
    width = max(1, width)
    height = max(1, height)
    
    return img.resize((width, height), Image.LANCZOS)

def compress_for_web(img, quality=85):
    """Optimize image for web use"""
    output = io.BytesIO()
    
    if img.mode == 'RGBA':
        # For transparent images, use PNG
        img.save(output, format='PNG', optimize=True)
    else:
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(output, format='JPEG', quality=quality, optimize=True)
    
    output.seek(0)
    return Image.open(output)


    

@require_http_methods(["GET"])
def image_resizer_view(request):
    """Main image resizer page"""
    context = {
        'supported_formats': ['JPG', 'JPEG', 'PNG', 'GIF', 'BMP', 'TIFF', 'WEBP', 'HEIC']
    }
    return render(request, 'image_resizer/resizer.html', context)

@require_http_methods(["POST"])
def process_image(request):
    """Process uploaded image with various operations"""
    try:
        # Validate file upload
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No image uploaded'}, status=400)
        
        uploaded_file = request.FILES['image']
        
        # Check file size
        if uploaded_file.size > MAX_FILE_SIZE:
            return JsonResponse({'error': 'File size exceeds 10MB limit'}, status=400)
        
        # Get processing options
        operation = request.POST.get('operation', 'resize')
        width = request.POST.get('width')
        height = request.POST.get('height')
        percentage = request.POST.get('percentage')
        maintain_aspect = request.POST.get('maintain_aspect', 'true') == 'true'
        output_format = request.POST.get('output_format', 'PNG').upper()
        remove_bg = request.POST.get('remove_bg', 'false') == 'true'
        enhance = request.POST.get('enhance', 'false') == 'true'
        compress = request.POST.get('compress', 'false') == 'true'
        preserve_exif = request.POST.get('preserve_exif', 'true') == 'true'
        
        # Open image
        img = Image.open(uploaded_file)
        
        # Correct orientation
        img = correct_image_orientation(img)
        
        # Store original EXIF if needed
        exif_data = None
        if preserve_exif and img.format in ['JPEG', 'JPG']:
            try:
                exif_data = piexif.load(img.info.get('exif', b''))
            except:
                exif_data = None
        
        # Process based on operation
        if operation == 'resize':
            if width:
                width = int(width)
            if height:
                height = int(height)
            if percentage:
                percentage = float(percentage)
            
            img = resize_image(img, width, height, percentage, maintain_aspect)
        
        # Apply enhancements
        if enhance:
            img = enhance_image_quality(img)
        
        # Remove background if requested
        if remove_bg:
            img = remove_background(img)
            output_format = 'PNG'  # Force PNG for transparency
        
        # Prepare output
        output = io.BytesIO()
        
        # Handle format conversion
        save_format = output_format
        if output_format in ['JPG', 'JPEG']:
            if img.mode in ('RGBA', 'LA', 'P'):
                # Convert to RGB, handling transparency
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                else:
                    img = img.convert('RGB')
            save_format = 'JPEG'
        elif output_format == 'WEBP':
            save_format = 'WEBP'
        elif output_format == 'PNG':
            # Ensure RGBA for PNG if it has transparency
            if img.mode == 'P':
                img = img.convert('RGBA')
        
        # Save with or without EXIF
        save_kwargs = {'format': save_format}
        
        if save_format == 'JPEG':
            if compress:
                save_kwargs['quality'] = 85
            else:
                save_kwargs['quality'] = 95
            save_kwargs['optimize'] = True
            if exif_data and preserve_exif:
                try:
                    save_kwargs['exif'] = piexif.dump(exif_data)
                except:
                    pass
        elif save_format == 'PNG':
            save_kwargs['optimize'] = True
        elif save_format == 'WEBP':
            save_kwargs['quality'] = 95 if not compress else 85
            save_kwargs['method'] = 6
        
        img.save(output, **save_kwargs)
        output.seek(0)
        
        # Create response with image
        response = HttpResponse(output.getvalue(), content_type=f'image/{output_format.lower()}')
        filename = f"resized_image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{output_format.lower()}"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def preview_image(request):
    """Generate preview of processed image"""
    try:
        if 'image' not in request.FILES:
            return JsonResponse({'error': 'No image uploaded'}, status=400)
        
        uploaded_file = request.FILES['image']
        
        if uploaded_file.size > MAX_FILE_SIZE:
            return JsonResponse({'error': 'File size exceeds 10MB limit'}, status=400)
        
        # Get processing options
        width = request.POST.get('width')
        height = request.POST.get('height')
        percentage = request.POST.get('percentage')
        maintain_aspect = request.POST.get('maintain_aspect', 'true') == 'true'
        
        # Open and process image
        img = Image.open(uploaded_file)
        img = correct_image_orientation(img)
        
        # Get original dimensions
        original_width, original_height = img.size
        
        # Process resize
        if width:
            width = int(width)
        if height:
            height = int(height)
        if percentage:
            percentage = float(percentage)
        
        img = resize_image(img, width, height, percentage, maintain_aspect)
        new_width, new_height = img.size
        
        # Create thumbnail for preview (max 800px width)
        preview_img = img.copy()
        if preview_img.width > 800:
            ratio = 800 / preview_img.width
            preview_img = preview_img.resize(
                (800, int(preview_img.height * ratio)), 
                Image.LANCZOS
            )
        
        # Convert to base64
        output = io.BytesIO()
        
        # Determine format for preview
        if preview_img.mode == 'RGBA':
            preview_img.save(output, format='PNG', optimize=True)
        else:
            if preview_img.mode != 'RGB':
                preview_img = preview_img.convert('RGB')
            preview_img.save(output, format='JPEG', quality=90, optimize=True)
        
        output.seek(0)
        
        import base64
        preview_base64 = base64.b64encode(output.getvalue()).decode()
        
        # Estimate full size file size
        full_output = io.BytesIO()
        if img.mode == 'RGBA':
            img.save(full_output, format='PNG', optimize=True)
        else:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(full_output, format='JPEG', quality=95, optimize=True)
        
        estimated_size = len(full_output.getvalue())
        
        return JsonResponse({
            'preview': f'data:image/{"png" if preview_img.mode == "RGBA" else "jpeg"};base64,{preview_base64}',
            'original_dimensions': {'width': original_width, 'height': original_height},
            'new_dimensions': {'width': new_width, 'height': new_height},
            'file_size': estimated_size,
            'original_size': uploaded_file.size
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
