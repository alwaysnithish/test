from django.shortcuts import render, redirect
from django.http import FileResponse, HttpResponse, JsonResponse
from django.conf import settings
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
import os
import uuid
from pathlib import Path
from .models import Conversion
from .converters import FileConverter

def home(request):
    """Main view for file upload and conversion"""
    context = {
        'uploaded_file': None,
        'file_type': None,
        'valid_conversions': [],
        'converted_file': None,
    }
    
    if request.method == 'POST':
        if 'file' in request.FILES:
            # Step 1: File upload
            uploaded_file = request.FILES['file']
            
            # Sanitize filename
            original_filename = FileConverter.sanitize_filename(uploaded_file.name)
            file_type = FileConverter.detect_file_type(original_filename)
            
            if not file_type:
                messages.error(request, 'Invalid file type')
                return render(request, 'fileconverter/home.html', context)
            
            # Save uploaded file
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            unique_filename = f"{uuid.uuid4()}_{original_filename}"
            file_path = os.path.join(upload_dir, unique_filename)
            
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            
            # Get valid conversions
            valid_conversions = FileConverter.get_valid_conversions(file_type)
            
            # Store in session
            request.session['uploaded_file'] = {
                'path': file_path,
                'original_name': original_filename,
                'type': file_type,
            }
            
            context['uploaded_file'] = original_filename
            context['file_type'] = file_type
            context['valid_conversions'] = valid_conversions
            
    # Check if there's a file in session
    elif 'uploaded_file' in request.session:
        file_info = request.session['uploaded_file']
        context['uploaded_file'] = file_info['original_name']
        context['file_type'] = file_info['type']
        context['valid_conversions'] = FileConverter.get_valid_conversions(file_info['type'])
    
    # Check for converted file
    if 'converted_file' in request.session:
        context['converted_file'] = request.session['converted_file']
    
    return render(request, 'fileconverter/home.html', context)

def convert_file(request):
    """Handle file conversion"""
    if request.method == 'POST' and 'uploaded_file' in request.session:
        target_format = request.POST.get('target_format')
        
        if not target_format:
            messages.error(request, 'Please select a target format')
            return redirect('fileconverter:home')
        
        file_info = request.session['uploaded_file']
        input_path = file_info['path']
        original_name = file_info['original_name']
        source_format = file_info['type']
        
        # Validate conversion
        valid_conversions = FileConverter.get_valid_conversions(source_format)
        if target_format not in valid_conversions:
            messages.error(request, 'Invalid conversion type')
            return redirect('fileconverter:home')
        
        try:
            # Generate output filename
            output_dir = os.path.join(settings.MEDIA_ROOT, 'converted')
            os.makedirs(output_dir, exist_ok=True)
            
            base_name = Path(original_name).stem
            output_filename = f"{base_name}_{uuid.uuid4().hex[:8]}.{target_format}"
            output_path = os.path.join(output_dir, output_filename)
            
            # Perform conversion
            FileConverter.convert(input_path, output_path, target_format)
            
            # Get file size
            file_size = os.path.getsize(output_path)
            
            # Save to database
            Conversion.objects.create(
                original_filename=original_name,
                original_format=source_format,
                target_format=target_format,
                converted_filename=output_filename,
                file_size=file_size,
                success=True
            )
            
            # Store in session
            request.session['converted_file'] = {
                'filename': output_filename,
                'original_name': base_name,
                'format': target_format,
            }
            
            messages.success(request, f'File converted successfully to {target_format.upper()}')
            
        except Exception as e:
            # Log error to database
            Conversion.objects.create(
                original_filename=original_name,
                original_format=source_format,
                target_format=target_format,
                converted_filename='',
                file_size=0,
                success=False,
                error_message=str(e)
            )
            messages.error(request, f'Conversion failed: {str(e)}')
        
        return redirect('fileconverter:home')
    
    return redirect('fileconverter:home')

def download_file(request, filename):
    """Handle file download"""
    file_path = os.path.join(settings.MEDIA_ROOT, 'converted', filename)
    
    if not os.path.exists(file_path):
        messages.error(request, 'File not found')
        return redirect('fileconverter:home')
    
    response = FileResponse(open(file_path, 'rb'))
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response
