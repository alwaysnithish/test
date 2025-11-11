from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.decorators import method_decorator
from django.views import View
import os
import tempfile
import mimetypes
import zipfile
import json
import uuid
from datetime import datetime, timedelta
import logging

# Third-party imports for file conversion
try:
    from PIL import Image, ImageEnhance, ImageFilter
    import cv2
    import numpy as np
    from moviepy.editor import VideoFileClip, AudioFileClip
    import librosa
    import soundfile as sf
    from pydub import AudioSegment
    import pytesseract
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter, A4
    from PyPDF2 import PdfReader, PdfWriter
    import docx
    from docx2pdf import convert as docx_to_pdf
    import pandas as pd
    import openpyxl
    from markdown import markdown
    import pdfkit
    import camelot
    from fpdf import FPDF
    import xml.etree.ElementTree as ET
    import yaml
    import csv
    import subprocess
    import magic
except ImportError as e:
    print(f"Warning: Some conversion libraries not installed: {e}")

logger = logging.getLogger(__name__)

class FileConverterView(View):
    """Main file converter view handling all conversion requests"""
    
    # Supported conversion mappings
    CONVERSION_MATRIX = {
        # Image conversions
        'image': {
            'from': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'svg', 'ico', 'raw'],
            'to': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp', 'ico', 'pdf']
        },
        # Document conversions
        'document': {
            'from': ['pdf', 'docx', 'doc', 'txt', 'rtf', 'odt', 'html', 'md', 'csv', 'xlsx', 'xls'],
            'to': ['pdf', 'docx', 'txt', 'html', 'md', 'csv', 'xlsx', 'json', 'xml']
        },
        # Audio conversions
        'audio': {
            'from': ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma', 'aiff'],
            'to': ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a']
        },
        # Video conversions
        'video': {
            'from': ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv', '3gp', 'mpg', 'mpeg'],
            'to': ['mp4', 'avi', 'mov', 'webm', 'mkv', 'gif']
        },
        # Archive conversions
        'archive': {
            'from': ['zip', 'rar', '7z', 'tar', 'gz', 'bz2'],
            'to': ['zip', 'tar', 'gz']
        },
        # Data conversions
        'data': {
            'from': ['json', 'xml', 'yaml', 'csv', 'xlsx', 'sql'],
            'to': ['json', 'xml', 'yaml', 'csv', 'xlsx', 'sql']
        }
    }
    
    def get(self, request):
        """Display the main converter interface"""
        context = {
            'supported_formats': self._get_all_supported_formats(),
            'conversion_matrix': self.CONVERSION_MATRIX
        }
        return render(request, 'file.html', context)
    
    @method_decorator(csrf_exempt)
    def post(self, request):
        """Handle file conversion requests"""
        try:
            if 'file' not in request.FILES:
                return JsonResponse({'error': 'No file uploaded'}, status=400)
            
            uploaded_file = request.FILES['file']
            target_format = request.POST.get('target_format', '').lower()
            
            if not target_format:
                return JsonResponse({'error': 'Target format not specified'}, status=400)
            
            # Generate unique filename
            file_id = str(uuid.uuid4())
            original_name = uploaded_file.name
            file_ext = os.path.splitext(original_name)[1][1:].lower()
            
            # Save uploaded file temporarily
            temp_input_path = self._save_temp_file(uploaded_file, file_id, file_ext)
            
            # Determine file type and convert
            file_type = self._get_file_type(file_ext)
            
            if not self._is_conversion_supported(file_ext, target_format):
                return JsonResponse({
                    'error': f'Conversion from {file_ext} to {target_format} not supported'
                }, status=400)
            
            # Perform conversion
            converted_file_path = self._convert_file(
                temp_input_path, file_ext, target_format, file_id
            )
            
            if converted_file_path:
                # Generate download URL
                download_url = f'/download/{file_id}.{target_format}'
                
                return JsonResponse({
                    'success': True,
                    'download_url': download_url,
                    'original_name': original_name,
                    'converted_name': f"{os.path.splitext(original_name)[0]}.{target_format}",
                    'file_id': file_id
                })
            else:
                return JsonResponse({'error': 'Conversion failed'}, status=500)
                
        except Exception as e:
            logger.error(f"Conversion error: {str(e)}")
            return JsonResponse({'error': f'Conversion failed: {str(e)}'}, status=500)
    
    def _save_temp_file(self, uploaded_file, file_id, extension):
        """Save uploaded file to temporary location"""
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_path = os.path.join(temp_dir, f"{file_id}.{extension}")
        
        with open(temp_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        return temp_path
    
    def _get_file_type(self, extension):
        """Determine file type category"""
        for category, formats in self.CONVERSION_MATRIX.items():
            if extension in formats['from']:
                return category
        return 'unknown'
    
    def _is_conversion_supported(self, from_ext, to_ext):
        """Check if conversion is supported"""
        for category, formats in self.CONVERSION_MATRIX.items():
            if from_ext in formats['from'] and to_ext in formats['to']:
                return True
        return False
    
    def _convert_file(self, input_path, from_ext, to_ext, file_id):
        """Main conversion dispatcher"""
        try:
            file_type = self._get_file_type(from_ext)
            
            if file_type == 'image':
                return self._convert_image(input_path, from_ext, to_ext, file_id)
            elif file_type == 'document':
                return self._convert_document(input_path, from_ext, to_ext, file_id)
            elif file_type == 'audio':
                return self._convert_audio(input_path, from_ext, to_ext, file_id)
            elif file_type == 'video':
                return self._convert_video(input_path, from_ext, to_ext, file_id)
            elif file_type == 'archive':
                return self._convert_archive(input_path, from_ext, to_ext, file_id)
            elif file_type == 'data':
                return self._convert_data(input_path, from_ext, to_ext, file_id)
            else:
                return None
                
        except Exception as e:
            logger.error(f"File conversion error: {str(e)}")
            return None
    
    def _convert_image(self, input_path, from_ext, to_ext, file_id):
        """Convert image files"""
        try:
            output_path = os.path.join(
                settings.MEDIA_ROOT, 'converted', f"{file_id}.{to_ext}"
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            if to_ext == 'pdf':
                # Convert image to PDF
                img = Image.open(input_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(output_path, 'PDF')
            else:
                # Standard image conversion
                img = Image.open(input_path)
                
                # Handle transparency for formats that don't support it
                if to_ext in ['jpg', 'jpeg'] and img.mode in ['RGBA', 'LA', 'P']:
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                
                # Save with appropriate format
                if to_ext == 'jpg':
                    img.save(output_path, 'JPEG', quality=95)
                else:
                    img.save(output_path, to_ext.upper())
            
            return output_path
            
        except Exception as e:
            logger.error(f"Image conversion error: {str(e)}")
            return None
    
    def _convert_document(self, input_path, from_ext, to_ext, file_id):
        """Convert document files"""
        try:
            output_path = os.path.join(
                settings.MEDIA_ROOT, 'converted', f"{file_id}.{to_ext}"
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            if from_ext == 'pdf' and to_ext == 'txt':
                # PDF to text
                with open(input_path, 'rb') as file:
                    reader = PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text()
                
                with open(output_path, 'w', encoding='utf-8') as output_file:
                    output_file.write(text)
            
            elif from_ext == 'docx' and to_ext == 'pdf':
                # DOCX to PDF
                docx_to_pdf(input_path, output_path)
            
            elif from_ext == 'md' and to_ext == 'html':
                # Markdown to HTML
                with open(input_path, 'r', encoding='utf-8') as md_file:
                    content = md_file.read()
                    html = markdown(content)
                
                with open(output_path, 'w', encoding='utf-8') as html_file:
                    html_file.write(html)
            
            elif from_ext == 'csv' and to_ext == 'xlsx':
                # CSV to Excel
                df = pd.read_csv(input_path)
                df.to_excel(output_path, index=False)
            
            elif from_ext == 'xlsx' and to_ext == 'csv':
                # Excel to CSV
                df = pd.read_excel(input_path)
                df.to_csv(output_path, index=False)
            
            elif from_ext == 'html' and to_ext == 'pdf':
                # HTML to PDF
                pdfkit.from_file(input_path, output_path)
            
            elif to_ext == 'txt':
                # Generic text extraction
                content = self._extract_text_content(input_path, from_ext)
                with open(output_path, 'w', encoding='utf-8') as output_file:
                    output_file.write(content)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Document conversion error: {str(e)}")
            return None
    
    def _convert_audio(self, input_path, from_ext, to_ext, file_id):
        """Convert audio files"""
        try:
            output_path = os.path.join(
                settings.MEDIA_ROOT, 'converted', f"{file_id}.{to_ext}"
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Use pydub for audio conversion
            audio = AudioSegment.from_file(input_path)
            
            if to_ext == 'mp3':
                audio.export(output_path, format='mp3', bitrate='192k')
            elif to_ext == 'wav':
                audio.export(output_path, format='wav')
            elif to_ext == 'flac':
                audio.export(output_path, format='flac')
            elif to_ext == 'aac':
                audio.export(output_path, format='aac')
            elif to_ext == 'ogg':
                audio.export(output_path, format='ogg')
            elif to_ext == 'm4a':
                audio.export(output_path, format='m4a')
            
            return output_path
            
        except Exception as e:
            logger.error(f"Audio conversion error: {str(e)}")
            return None
    
    def _convert_video(self, input_path, from_ext, to_ext, file_id):
        """Convert video files"""
        try:
            output_path = os.path.join(
                settings.MEDIA_ROOT, 'converted', f"{file_id}.{to_ext}"
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            if to_ext == 'gif':
                # Convert video to GIF
                clip = VideoFileClip(input_path)
                clip.write_gif(output_path, fps=15)
            else:
                # Standard video conversion
                clip = VideoFileClip(input_path)
                
                if to_ext == 'mp4':
                    clip.write_videofile(output_path, codec='libx264')
                elif to_ext == 'avi':
                    clip.write_videofile(output_path, codec='libxvid')
                elif to_ext == 'mov':
                    clip.write_videofile(output_path, codec='libx264')
                elif to_ext == 'webm':
                    clip.write_videofile(output_path, codec='libvpx')
                elif to_ext == 'mkv':
                    clip.write_videofile(output_path, codec='libx264')
            
            return output_path
            
        except Exception as e:
            logger.error(f"Video conversion error: {str(e)}")
            return None
    
    def _convert_archive(self, input_path, from_ext, to_ext, file_id):
        """Convert archive files"""
        try:
            output_path = os.path.join(
                settings.MEDIA_ROOT, 'converted', f"{file_id}.{to_ext}"
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Extract and recompress
            temp_extract_dir = os.path.join(
                settings.MEDIA_ROOT, 'temp', f"extract_{file_id}"
            )
            os.makedirs(temp_extract_dir, exist_ok=True)
            
            # Extract original archive
            if from_ext == 'zip':
                with zipfile.ZipFile(input_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract_dir)
            # Add more archive formats as needed
            
            # Create new archive
            if to_ext == 'zip':
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for root, dirs, files in os.walk(temp_extract_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_extract_dir)
                            zip_file.write(file_path, arcname)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Archive conversion error: {str(e)}")
            return None
    
    def _convert_data(self, input_path, from_ext, to_ext, file_id):
        """Convert data files"""
        try:
            output_path = os.path.join(
                settings.MEDIA_ROOT, 'converted', f"{file_id}.{to_ext}"
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Read input data
            if from_ext == 'json':
                with open(input_path, 'r') as f:
                    data = json.load(f)
            elif from_ext == 'yaml':
                with open(input_path, 'r') as f:
                    data = yaml.safe_load(f)
            elif from_ext == 'csv':
                data = pd.read_csv(input_path).to_dict('records')
            elif from_ext == 'xlsx':
                data = pd.read_excel(input_path).to_dict('records')
            
            # Write output data
            if to_ext == 'json':
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
            elif to_ext == 'yaml':
                with open(output_path, 'w') as f:
                    yaml.dump(data, f, default_flow_style=False)
            elif to_ext == 'csv':
                df = pd.DataFrame(data)
                df.to_csv(output_path, index=False)
            elif to_ext == 'xlsx':
                df = pd.DataFrame(data)
                df.to_excel(output_path, index=False)
            elif to_ext == 'xml':
                # Convert to XML
                root = ET.Element('data')
                for item in data:
                    record = ET.SubElement(root, 'record')
                    for key, value in item.items():
                        field = ET.SubElement(record, key)
                        field.text = str(value)
                
                tree = ET.ElementTree(root)
                tree.write(output_path, encoding='utf-8', xml_declaration=True)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Data conversion error: {str(e)}")
            return None
    
    def _extract_text_content(self, file_path, file_ext):
        """Extract text content from various file formats"""
        try:
            if file_ext == 'docx':
                doc = docx.Document(file_path)
                return '\n'.join([para.text for para in doc.paragraphs])
            elif file_ext == 'pdf':
                with open(file_path, 'rb') as file:
                    reader = PdfReader(file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text()
                return text
            elif file_ext in ['txt', 'md', 'html']:
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            else:
                return "Text extraction not supported for this format"
        except Exception as e:
            return f"Error extracting text: {str(e)}"
    
    def _get_all_supported_formats(self):
        """Get all supported file formats"""
        all_formats = set()
        for category, formats in self.CONVERSION_MATRIX.items():
            all_formats.update(formats['from'])
            all_formats.update(formats['to'])
        return sorted(list(all_formats))


class FileDownloadView(View):
    """Handle file downloads"""
    
    def get(self, request, file_id):
        """Download converted file"""
        try:
            file_path = os.path.join(
                settings.MEDIA_ROOT, 'converted', file_id
            )
            
            if not os.path.exists(file_path):
                raise Http404("File not found")
            
            # Get file mime type
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'
            
            # Read file content
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Create response
            response = HttpResponse(file_data, content_type=mime_type)
            response['Content-Disposition'] = f'attachment; filename="{file_id}"'
            response['Content-Length'] = len(file_data)
            
            return response
            
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            raise Http404("File not found")


class BatchConverterView(View):
    """Handle batch file conversions"""
    
    @method_decorator(csrf_exempt)
    def post(self, request):
        """Handle batch conversion requests"""
        try:
            files = request.FILES.getlist('files')
            target_format = request.POST.get('target_format', '').lower()
            
            if not files:
                return JsonResponse({'error': 'No files uploaded'}, status=400)
            
            if not target_format:
                return JsonResponse({'error': 'Target format not specified'}, status=400)
            
            results = []
            converter = FileConverterView()
            
            for uploaded_file in files:
                try:
                    file_id = str(uuid.uuid4())
                    original_name = uploaded_file.name
                    file_ext = os.path.splitext(original_name)[1][1:].lower()
                    
                    # Save and convert file
                    temp_input_path = converter._save_temp_file(uploaded_file, file_id, file_ext)
                    
                    if converter._is_conversion_supported(file_ext, target_format):
                        converted_file_path = converter._convert_file(
                            temp_input_path, file_ext, target_format, file_id
                        )
                        
                        if converted_file_path:
                            results.append({
                                'success': True,
                                'original_name': original_name,
                                'download_url': f'/download/{file_id}.{target_format}',
                                'file_id': file_id
                            })
                        else:
                            results.append({
                                'success': False,
                                'original_name': original_name,
                                'error': 'Conversion failed'
                            })
                    else:
                        results.append({
                            'success': False,
                            'original_name': original_name,
                            'error': f'Conversion from {file_ext} to {target_format} not supported'
                        })
                        
                except Exception as e:
                    results.append({
                        'success': False,
                        'original_name': uploaded_file.name,
                        'error': str(e)
                    })
            
            return JsonResponse({
                'success': True,
                'results': results,
                'total_files': len(files),
                'successful_conversions': len([r for r in results if r['success']])
            })
            
        except Exception as e:
            logger.error(f"Batch conversion error: {str(e)}")
            return JsonResponse({'error': f'Batch conversion failed: {str(e)}'}, status=500)


class ConversionHistoryView(View):
    """View conversion history"""
    
    def get(self, request):
        """Display conversion history"""
        # This would typically fetch from database
        # For now, return empty history
        return JsonResponse({
            'history': [],
            'total': 0
        })


class SupportedFormatsView(View):
    """API endpoint for supported formats"""
    
    def get(self, request):
        """Return supported formats and conversion matrix"""
        converter = FileConverterView()
        return JsonResponse({
            'conversion_matrix': converter.CONVERSION_MATRIX,
            'all_formats': converter._get_all_supported_formats()
        })


# Utility functions
def cleanup_temp_files():
    """Clean up temporary files older than 24 hours"""
    try:
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp')
        converted_dir = os.path.join(settings.MEDIA_ROOT, 'converted')
        
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for directory in [temp_dir, converted_dir]:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    if os.path.isfile(file_path):
                        file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                        if file_time < cutoff_time:
                            os.remove(file_path)
                            logger.info(f"Cleaned up old file: {file_path}")
    
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'supported_formats': len(FileConverterView()._get_all_supported_formats())
    })


@require_http_methods(["POST"])
@csrf_exempt
def quick_convert(request):
    """Quick conversion API endpoint"""
    try:
        data = json.loads(request.body)
        from_format = data.get('from_format', '').lower()
        to_format = data.get('to_format', '').lower()
        
        converter = FileConverterView()
        
        if converter._is_conversion_supported(from_format, to_format):
            return JsonResponse({
                'supported': True,
                'message': f'Conversion from {from_format} to {to_format} is supported'
            })
        else:
            return JsonResponse({
                'supported': False,
                'message': f'Conversion from {from_format} to {to_format} is not supported'
            })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)