import os
import io
import json
import base64
from datetime import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse, Http404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import PyPDF2
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import Color
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import zipfile
import tempfile


def index(request):
    """Main PDF tools page"""
    return render(request, 'pdftools.html')


def extract_text(request):
    """Extract text from PDF"""
    if request.method == 'POST':
        try:
            pdf_file = request.FILES.get('pdf_file')
            if not pdf_file:
                return JsonResponse({'error': 'No PDF file provided'}, status=400)
            
            # Read PDF and extract text
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            extracted_text = ""
            
            for page_num, page in enumerate(pdf_reader.pages, 1):
                text = page.extract_text()
                extracted_text += f"--- Page {page_num} ---\n{text}\n\n"
            
            # Create text file
            text_filename = f"extracted_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            # Return as JSON with preview
            return JsonResponse({
                'success': True,
                'filename': text_filename,
                'content_type': 'text/plain',
                'preview': extracted_text[:2000] + ('...' if len(extracted_text) > 2000 else ''),
                'full_content': extracted_text,
                'operation': 'text_extraction'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error extracting text: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def split_pdf(request):
    """Split PDF into pages or ranges"""
    if request.method == 'POST':
        try:
            pdf_file = request.FILES.get('pdf_file')
            split_type = request.POST.get('split_type', 'pages')
            page_ranges = request.POST.get('page_ranges', '')
            
            if not pdf_file:
                return JsonResponse({'error': 'No PDF file provided'}, status=400)
            
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(pdf_reader.pages)
            
            # Create ZIP file for multiple PDFs
            zip_buffer = io.BytesIO()
            files_info = []
            
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                if split_type == 'pages':
                    # Split into individual pages
                    for page_num in range(total_pages):
                        pdf_writer = PyPDF2.PdfWriter()
                        pdf_writer.add_page(pdf_reader.pages[page_num])
                        
                        page_buffer = io.BytesIO()
                        pdf_writer.write(page_buffer)
                        page_buffer.seek(0)
                        
                        filename = f"page_{page_num + 1}.pdf"
                        zip_file.writestr(filename, page_buffer.getvalue())
                        files_info.append({
                            'name': filename,
                            'size': len(page_buffer.getvalue()),
                            'pages': 1
                        })
                
                else:  # split by ranges
                    ranges = page_ranges.split(',')
                    for i, range_str in enumerate(ranges):
                        range_str = range_str.strip()
                        if '-' in range_str:
                            start, end = map(int, range_str.split('-'))
                        else:
                            start = end = int(range_str)
                        
                        pdf_writer = PyPDF2.PdfWriter()
                        for page_num in range(start - 1, min(end, total_pages)):
                            pdf_writer.add_page(pdf_reader.pages[page_num])
                        
                        range_buffer = io.BytesIO()
                        pdf_writer.write(range_buffer)
                        range_buffer.seek(0)
                        
                        filename = f"pages_{start}_to_{end}.pdf"
                        zip_file.writestr(filename, range_buffer.getvalue())
                        files_info.append({
                            'name': filename,
                            'size': len(range_buffer.getvalue()),
                            'pages': end - start + 1
                        })
            
            zip_buffer.seek(0)
            zip_data = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
            
            return JsonResponse({
                'success': True,
                'filename': 'split_pdfs.zip',
                'content_type': 'application/zip',
                'data': zip_data,
                'files_info': files_info,
                'total_files': len(files_info),
                'operation': 'pdf_split'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error splitting PDF: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def merge_pdfs(request):
    """Merge multiple PDFs into one"""
    if request.method == 'POST':
        try:
            main_pdf = request.FILES.get('pdf_file')
            additional_pdfs = request.FILES.getlist('additional_files')
            
            # Combine all PDFs
            all_pdfs = [main_pdf] if main_pdf else []
            all_pdfs.extend(additional_pdfs)
            
            if len(all_pdfs) < 2:
                return JsonResponse({'error': 'At least 2 PDF files required for merging'}, status=400)
            
            pdf_writer = PyPDF2.PdfWriter()
            merge_info = []
            
            for pdf_file in all_pdfs:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                page_count = len(pdf_reader.pages)
                merge_info.append({
                    'name': pdf_file.name,
                    'pages': page_count,
                    'size': pdf_file.size
                })
                
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
            
            output_buffer = io.BytesIO()
            pdf_writer.write(output_buffer)
            output_buffer.seek(0)
            
            pdf_data = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
            
            # Generate preview image of first page
            preview_image = generate_pdf_preview(output_buffer.getvalue())
            
            return JsonResponse({
                'success': True,
                'filename': 'merged_document.pdf',
                'content_type': 'application/pdf',
                'data': pdf_data,
                'preview_image': preview_image,
                'merge_info': merge_info,
                'total_pages': sum(info['pages'] for info in merge_info),
                'operation': 'pdf_merge'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error merging PDFs: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def compress_pdf(request):
    """Compress PDF to reduce file size"""
    if request.method == 'POST':
        try:
            pdf_file = request.FILES.get('pdf_file')
            quality = int(request.POST.get('quality', 75))
            
            if not pdf_file:
                return JsonResponse({'error': 'No PDF file provided'}, status=400)
            
            original_size = pdf_file.size
            pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
            
            # Compress images and reduce quality
            for page_num in range(len(pdf_document)):
                page = pdf_document.load_page(page_num)
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    pix = fitz.Pixmap(pdf_document, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        img_data = pix.tobytes("png")
                        pil_img = Image.open(io.BytesIO(img_data))
                        
                        # Compress image
                        compressed_buffer = io.BytesIO()
                        pil_img.save(compressed_buffer, format='JPEG', quality=quality, optimize=True)
                        compressed_buffer.seek(0)
                        
                        # Replace image in PDF
                        pdf_document.update_stream(xref, compressed_buffer.getvalue())
                    
                    pix = None
            
            # Save compressed PDF
            output_buffer = io.BytesIO()
            pdf_document.save(output_buffer, garbage=4, deflate=True, clean=True)
            output_buffer.seek(0)
            pdf_document.close()
            
            compressed_data = output_buffer.getvalue()
            compressed_size = len(compressed_data)
            compression_ratio = ((original_size - compressed_size) / original_size) * 100
            
            pdf_data = base64.b64encode(compressed_data).decode('utf-8')
            preview_image = generate_pdf_preview(compressed_data)
            
            return JsonResponse({
                'success': True,
                'filename': 'compressed_document.pdf',
                'content_type': 'application/pdf',
                'data': pdf_data,
                'preview_image': preview_image,
                'original_size': original_size,
                'compressed_size': compressed_size,
                'compression_ratio': round(compression_ratio, 2),
                'operation': 'pdf_compression'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error compressing PDF: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def add_watermark(request):
    """Add watermark to PDF"""
    if request.method == 'POST':
        try:
            pdf_file = request.FILES.get('pdf_file')
            watermark_text = request.POST.get('watermark_text', 'WATERMARK')
            opacity = float(request.POST.get('opacity', 0.3))
            position = request.POST.get('position', 'center')
            font_size = int(request.POST.get('font_size', 50))
            color = request.POST.get('color', 'gray')
            
            if not pdf_file:
                return JsonResponse({'error': 'No PDF file provided'}, status=400)
            
            # Create watermark PDF
            watermark_buffer = io.BytesIO()
            c = canvas.Canvas(watermark_buffer, pagesize=letter)
            
            # Set color based on selection
            color_map = {
                'gray': (0.5, 0.5, 0.5),
                'red': (1, 0, 0),
                'blue': (0, 0, 1),
                'green': (0, 1, 0),
                'black': (0, 0, 0)
            }
            
            rgb = color_map.get(color, (0.5, 0.5, 0.5))
            c.setFillColorRGB(*rgb, opacity)
            c.setFont("Helvetica-Bold", font_size)
            
            # Position watermark
            width, height = letter
            positions = {
                'center': (width/2, height/2),
                'top-left': (100, height - 100),
                'top-right': (width - 200, height - 100),
                'bottom-left': (100, 100),
                'bottom-right': (width - 200, 100)
            }
            
            x, y = positions.get(position, (width/2, height/2))
            
            # Draw watermark
            c.saveState()
            c.translate(x, y)
            if position == 'center':
                c.rotate(45)  # Diagonal for center
            c.drawCentredString(0, 0, watermark_text)
            c.restoreState()
            c.save()
            
            # Apply watermark to PDF
            watermark_buffer.seek(0)
            watermark_pdf = PyPDF2.PdfReader(watermark_buffer)
            watermark_page = watermark_pdf.pages[0]
            
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            pdf_writer = PyPDF2.PdfWriter()
            
            for page in pdf_reader.pages:
                page.merge_page(watermark_page)
                pdf_writer.add_page(page)
            
            output_buffer = io.BytesIO()
            pdf_writer.write(output_buffer)
            output_buffer.seek(0)
            
            pdf_data = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
            preview_image = generate_pdf_preview(output_buffer.getvalue())
            
            return JsonResponse({
                'success': True,
                'filename': 'watermarked_document.pdf',
                'content_type': 'application/pdf',
                'data': pdf_data,
                'preview_image': preview_image,
                'watermark_info': {
                    'text': watermark_text,
                    'position': position,
                    'opacity': opacity,
                    'color': color,
                    'font_size': font_size
                },
                'operation': 'watermark'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error adding watermark: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def rotate_pages(request):
    """Rotate PDF pages"""
    if request.method == 'POST':
        try:
            pdf_file = request.FILES.get('pdf_file')
            rotation = int(request.POST.get('rotation', 90))
            pages_to_rotate = request.POST.get('pages', '')
            
            if not pdf_file:
                return JsonResponse({'error': 'No PDF file provided'}, status=400)
            
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            pdf_writer = PyPDF2.PdfWriter()
            
            total_pages = len(pdf_reader.pages)
            
            if not pages_to_rotate or pages_to_rotate.lower() == 'all':
                pages_list = list(range(total_pages))
            else:
                pages_list = []
                for page_range in pages_to_rotate.split(','):
                    page_range = page_range.strip()
                    if '-' in page_range:
                        start, end = map(int, page_range.split('-'))
                        pages_list.extend(range(start - 1, min(end, total_pages)))
                    else:
                        pages_list.append(int(page_range) - 1)
            
            rotated_pages = []
            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                if page_num in pages_list:
                    page = page.rotate(rotation)
                    rotated_pages.append(page_num + 1)
                pdf_writer.add_page(page)
            
            output_buffer = io.BytesIO()
            pdf_writer.write(output_buffer)
            output_buffer.seek(0)
            
            pdf_data = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
            preview_image = generate_pdf_preview(output_buffer.getvalue())
            
            return JsonResponse({
                'success': True,
                'filename': 'rotated_document.pdf',
                'content_type': 'application/pdf',
                'data': pdf_data,
                'preview_image': preview_image,
                'rotation_info': {
                    'rotation': rotation,
                    'rotated_pages': rotated_pages,
                    'total_pages': total_pages
                },
                'operation': 'rotation'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error rotating pages: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def view_metadata(request):
    """View PDF metadata"""
    if request.method == 'POST':
        try:
            pdf_file = request.FILES.get('pdf_file')
            
            if not pdf_file:
                return JsonResponse({'error': 'No PDF file provided'}, status=400)
            
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            metadata = {
                'file_name': pdf_file.name,
                'total_pages': len(pdf_reader.pages),
                'file_size': f"{pdf_file.size / (1024*1024):.2f} MB",
                'encrypted': pdf_reader.is_encrypted,
            }
            
            # Get document info
            if pdf_reader.metadata:
                doc_info = pdf_reader.metadata
                metadata.update({
                    'title': doc_info.get('/Title', 'N/A'),
                    'author': doc_info.get('/Author', 'N/A'),
                    'subject': doc_info.get('/Subject', 'N/A'),
                    'creator': doc_info.get('/Creator', 'N/A'),
                    'producer': doc_info.get('/Producer', 'N/A'),
                    'creation_date': str(doc_info.get('/CreationDate', 'N/A')),
                    'modification_date': str(doc_info.get('/ModDate', 'N/A')),
                })
            
            # Generate preview
            preview_image = generate_pdf_preview(pdf_file.read())
            
            return JsonResponse({
                'success': True,
                'metadata': metadata,
                'preview_image': preview_image,
                'operation': 'metadata'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error reading metadata: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def convert_to_images(request):
    """Convert PDF pages to images"""
    if request.method == 'POST':
        try:
            pdf_file = request.FILES.get('pdf_file')
            image_format = request.POST.get('format', 'PNG')
            dpi = int(request.POST.get('dpi', 150))
            
            if not pdf_file:
                return JsonResponse({'error': 'No PDF file provided'}, status=400)
            
            pdf_document = fitz.open(stream=pdf_file.read(), filetype="pdf")
            
            zip_buffer = io.BytesIO()
            images_info = []
            preview_images = []
            
            with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
                for page_num in range(len(pdf_document)):
                    page = pdf_document.load_page(page_num)
                    
                    # Render page to image
                    mat = fitz.Matrix(dpi/72, dpi/72)
                    pix = page.get_pixmap(matrix=mat)
                    
                    img_data = pix.tobytes(image_format.lower())
                    filename = f"page_{page_num + 1}.{image_format.lower()}"
                    zip_file.writestr(filename, img_data)
                    
                    images_info.append({
                        'name': filename,
                        'size': len(img_data),
                        'page': page_num + 1
                    })
                    
                    # Create preview for first few pages
                    if page_num < 3:
                        preview_images.append({
                            'page': page_num + 1,
                            'data': base64.b64encode(img_data).decode('utf-8'),
                            'format': image_format.lower()
                        })
            
            pdf_document.close()
            zip_buffer.seek(0)
            zip_data = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
            
            return JsonResponse({
                'success': True,
                'filename': f'pdf_images_{image_format.lower()}.zip',
                'content_type': 'application/zip',
                'data': zip_data,
                'images_info': images_info,
                'preview_images': preview_images,
                'total_images': len(images_info),
                'format': image_format,
                'dpi': dpi,
                'operation': 'image_conversion'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error converting to images: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


def generate_pdf_preview(pdf_data, page_num=0):
    """Generate preview image of PDF page"""
    try:
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        if page_num >= len(pdf_document):
            page_num = 0
        
        page = pdf_document.load_page(page_num)
        mat = fitz.Matrix(1.5, 1.5)  # Zoom factor
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        pdf_document.close()
        
        return base64.b64encode(img_data).decode('utf-8')
    except:
        return None


def download_file(request):
    """Handle file downloads"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            file_data = data.get('data')
            filename = data.get('filename', 'download')
            content_type = data.get('content_type', 'application/octet-stream')
            
            if file_data:
                if content_type == 'text/plain':
                    file_content = data.get('full_content', '')
                    response = HttpResponse(file_content, content_type=content_type)
                else:
                    file_content = base64.b64decode(file_data)
                    response = HttpResponse(file_content, content_type=content_type)
                
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                return response
            
            return JsonResponse({'error': 'No file data provided'}, status=400)
            
        except Exception as e:
            return JsonResponse({'error': f'Error downloading file: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)


# Additional utility views for enhanced features
def pdf_info(request):
    """Get detailed PDF information"""
    if request.method == 'POST':
        try:
            pdf_file = request.FILES.get('pdf_file')
            if not pdf_file:
                return JsonResponse({'error': 'No PDF file provided'}, status=400)
            
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            pages_info = []
            for i, page in enumerate(pdf_reader.pages):
                pages_info.append({
                    'page': i + 1,
                    'rotation': page.rotation if hasattr(page, 'rotation') else 0,
                    'mediabox': str(page.mediabox) if hasattr(page, 'mediabox') else 'Unknown'
                })
            
            return JsonResponse({
                'success': True,
                'pages_info': pages_info,
                'total_pages': len(pdf_reader.pages),
                'is_encrypted': pdf_reader.is_encrypted
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Error getting PDF info: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)
