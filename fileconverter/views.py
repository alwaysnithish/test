import os
import uuid
import mimetypes
from django.shortcuts import render
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.views.decorators.http import require_http_methods
from pathlib import Path
import json
from .utils.conversion import FileConverter, CONVERSION_MAP
from .utils.file_handler import FileHandler

# Ensure temp directory exists
TEMP_DIR = getattr(settings, 'MEDIA_TEMP', os.path.join(settings.MEDIA_ROOT, 'temp_conversions'))
os.makedirs(TEMP_DIR, exist_ok=True)


def index(request):
    """Render the main file converter page"""
    # Create list of all supported formats for display
    all_formats = set()
    for key, values in CONVERSION_MAP.items():
        all_formats.add(key)
        all_formats.update(values)
    
    context = {
        'conversion_map': json.dumps(CONVERSION_MAP),
        'max_file_size': 50,  # MB
        'supported_formats': sorted(list(all_formats)),
        'total_conversions': sum(len(v) for v in CONVERSION_MAP.values())
    }
    return render(request, 'index.html', context)


@require_http_methods(["POST"])
def upload_file(request):
    """Handle file upload and return available conversion options"""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file uploaded'}, status=400)
        
        uploaded_file = request.FILES['file']
        
        # Validate file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if uploaded_file.size > max_size:
            return JsonResponse({
                'error': f'File too large. Maximum size is 50MB. Your file is {uploaded_file.size / (1024*1024):.2f}MB'
            }, status=400)
        
        # Generate unique filename
        file_uuid = str(uuid.uuid4())
        original_name = uploaded_file.name
        file_extension = Path(original_name).suffix.lower()
        
        # Handle files without extension
        if not file_extension:
            return JsonResponse({
                'error': 'File must have an extension (e.g., .pdf, .jpg, .docx)'
            }, status=400)
        
        # Validate file extension
        file_handler = FileHandler()
        if not file_handler.is_valid_extension(file_extension):
            return JsonResponse({
                'error': f'Unsupported file type: {file_extension}. Please check supported formats.'
            }, status=400)
        
        # Save uploaded file
        temp_path = os.path.join(TEMP_DIR, f"{file_uuid}{file_extension}")
        with open(temp_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Validate MIME type
        mime_type = mimetypes.guess_type(temp_path)[0]
        if not file_handler.is_valid_mime(mime_type, file_extension):
            os.remove(temp_path)
            return JsonResponse({
                'error': f'Invalid file format. File content does not match extension {file_extension}'
            }, status=400)
        
        # Get detected format and available conversions
        from_format = file_extension.lstrip('.')
        available_formats = CONVERSION_MAP.get(from_format, [])
        
        # Build response message
        if len(available_formats) == 0:
            message = f'File uploaded successfully. No conversions available for {from_format.upper()} files.'
        else:
            message = f'File uploaded successfully. {len(available_formats)} conversion option{"s" if len(available_formats) != 1 else ""} available.'
        
        return JsonResponse({
            'success': True,
            'file_uuid': file_uuid,
            'original_name': original_name,
            'file_size': uploaded_file.size,
            'from_format': from_format,
            'available_formats': available_formats,
            'message': message
        })
    
    except Exception as e:
        return JsonResponse({
            'error': f'Upload failed: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def convert_file(request):
    """Handle file conversion"""
    try:
        data = json.loads(request.body)
        file_uuid = data.get('file_uuid')
        from_format = data.get('from_format')
        to_format = data.get('to_format')
        
        if not all([file_uuid, from_format, to_format]):
            return JsonResponse({'error': 'Missing required parameters'}, status=400)
        
        # Validate conversion is supported
        if to_format not in CONVERSION_MAP.get(from_format, []):
            return JsonResponse({
                'error': f'Conversion from {from_format.upper()} to {to_format.upper()} is not supported'
            }, status=400)
        
        # Find input file (try lowercase and uppercase extensions)
        input_file = None
        for ext in [f'.{from_format}', f'.{from_format.upper()}']:
            temp_path = os.path.join(TEMP_DIR, f"{file_uuid}{ext}")
            if os.path.exists(temp_path):
                input_file = temp_path
                break
        
        if not input_file:
            return JsonResponse({
                'error': 'File not found. It may have expired (files are deleted after 60 minutes).'
            }, status=404)
        
        # Perform conversion
        converter = FileConverter()
        
        try:
            output_file = converter.convert(input_file, from_format, to_format, file_uuid)
        except NotImplementedError as e:
            return JsonResponse({
                'error': f'Conversion not yet implemented: {str(e)}'
            }, status=501)
        except Exception as e:
            return JsonResponse({
                'error': f'Conversion failed: {str(e)}'
            }, status=500)
        
        if not output_file or not os.path.exists(output_file):
            return JsonResponse({
                'error': 'Conversion failed. The output file was not created.'
            }, status=500)
        
        # Get output filename
        output_filename = os.path.basename(output_file)
        
        return JsonResponse({
            'success': True,
            'output_uuid': file_uuid,
            'output_format': to_format,
            'download_url': f'/fileconverter/download/{output_filename}/',
            'message': f'Conversion completed successfully! Your {to_format.upper()} file is ready.'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Conversion failed: {str(e)}'
        }, status=500)


def download_file(request, filename):
    """Serve converted file and delete after download"""
    try:
        # Sanitize filename to prevent path traversal
        filename = os.path.basename(filename)
        file_path = os.path.join(TEMP_DIR, filename)
        
        if not os.path.exists(file_path):
            return HttpResponse('File not found or has expired. Files are automatically deleted after 60 minutes.', status=404)
        
        # Verify file is within TEMP_DIR (security check)
        real_path = os.path.realpath(file_path)
        real_temp = os.path.realpath(TEMP_DIR)
        if not real_path.startswith(real_temp):
            return HttpResponse('Invalid file path', status=403)
        
        # Determine content type
        content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        
        # Open and serve file
        try:
            file_handle = open(file_path, 'rb')
            response = FileResponse(file_handle, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = os.path.getsize(file_path)
            
            # Delete file after serving (cleanup)
            # Note: In production, consider using a signal or background task
            try:
                # Extract UUID from filename to delete related files
                file_uuid = filename.split('_')[0]
                
                # Schedule deletion after response is sent
                # For now, we'll delete immediately after download
                # In production, use a post-response signal
                import atexit
                def cleanup():
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        # Also remove original file if it exists
                        for ext in ['.pdf', '.docx', '.doc', '.txt', '.jpg', '.jpeg', '.png', 
                                   '.xlsx', '.xls', '.csv', '.mp4', '.mp3', '.zip', '.odt']:
                            orig_file = os.path.join(TEMP_DIR, f"{file_uuid}{ext}")
                            if os.path.exists(orig_file):
                                os.remove(orig_file)
                    except:
                        pass
                
                # Delete after a short delay (allows download to complete)
                import threading
                timer = threading.Timer(5.0, cleanup)
                timer.daemon = True
                timer.start()
                
            except:
                pass  # Cleanup will be handled by management command
            
            return response
            
        except Exception as e:
            return HttpResponse(f'Error serving file: {str(e)}', status=500)
    
    except Exception as e:
        return HttpResponse(f'Download failed: {str(e)}', status=500)


def get_conversion_options(request, from_format):
    """API endpoint to get available conversion options for a format"""
    from_format = from_format.lower()
    options = CONVERSION_MAP.get(from_format, [])
    
    return JsonResponse({
        'from_format': from_format,
        'available_formats': options,
        'count': len(options)
    })


def get_supported_formats(request):
    """API endpoint to get all supported input formats"""
    formats = {
        'documents': [],
        'images': [],
        'spreadsheets': [],
        'presentations': [],
        'audio': [],
        'video': [],
        'archives': [],
        'data': []
    }
    
    # Categorize formats
    doc_formats = ['pdf', 'docx', 'doc', 'odt', 'txt', 'rtf', 'md', 'epub']
    image_formats = ['jpg', 'jpeg', 'png', 'webp', 'tiff', 'bmp', 'gif', 'heic', 'heif', 'svg']
    sheet_formats = ['xlsx', 'xls', 'ods', 'csv']
    presentation_formats = ['ppt', 'pptx', 'odp']
    audio_formats = ['mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg']
    video_formats = ['mp4', 'mkv', 'mov', 'avi', 'webm', 'flv']
    archive_formats = ['zip', 'rar', '7z', 'tar']
    data_formats = ['json', 'xml', 'yaml', 'yml', 'html']
    
    for fmt in CONVERSION_MAP.keys():
        if fmt in doc_formats:
            formats['documents'].append(fmt)
        elif fmt in image_formats:
            formats['images'].append(fmt)
        elif fmt in sheet_formats:
            formats['spreadsheets'].append(fmt)
        elif fmt in presentation_formats:
            formats['presentations'].append(fmt)
        elif fmt in audio_formats:
            formats['audio'].append(fmt)
        elif fmt in video_formats:
            formats['video'].append(fmt)
        elif fmt in archive_formats:
            formats['archives'].append(fmt)
        elif fmt in data_formats:
            formats['data'].append(fmt)
    
    return JsonResponse({
        'formats': formats,
        'total_input_formats': len(CONVERSION_MAP.keys()),
        'total_conversions': sum(len(v) for v in CONVERSION_MAP.values())
    })
