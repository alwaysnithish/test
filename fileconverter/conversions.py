import os
import subprocess
import uuid
from pathlib import Path
from PIL import Image
import pandas as pd

# Conversion mapping: from_format -> [available_to_formats]
# Based on comprehensive mapping reference
CONVERSION_MAP = {
    # Documents
    'pdf': ['docx', 'odt', 'txt', 'jpg', 'png'],
    'docx': ['pdf', 'odt', 'txt'],
    'doc': ['pdf', 'docx', 'odt', 'txt'],
    'odt': ['pdf', 'docx', 'txt'],
    'txt': ['pdf', 'docx'],
    'rtf': ['pdf', 'docx', 'txt'],
    'md': ['pdf', 'docx', 'txt', 'html'],
    'epub': ['pdf', 'txt'],
    
    # Images
    'jpg': ['png', 'webp', 'tiff', 'pdf', 'bmp'],
    'jpeg': ['png', 'webp', 'tiff', 'pdf', 'bmp'],
    'png': ['jpg', 'webp', 'tiff', 'pdf', 'bmp'],
    'webp': ['jpg', 'png', 'tiff', 'pdf'],
    'tiff': ['jpg', 'png', 'webp', 'pdf'],
    'bmp': ['jpg', 'png', 'webp', 'pdf'],
    'gif': ['jpg', 'png', 'webp', 'pdf'],
    'heic': ['jpg', 'png', 'webp'],
    'heif': ['jpg', 'png', 'webp'],
    'svg': ['png', 'jpg', 'pdf'],
    
    # Spreadsheets
    'xlsx': ['csv', 'xls', 'pdf', 'txt'],
    'xls': ['csv', 'xlsx', 'pdf', 'txt'],
    'ods': ['csv', 'xlsx', 'pdf'],
    'csv': ['xlsx', 'xls', 'txt', 'json'],
    
    # Presentations
    'ppt': ['pdf', 'pptx'],
    'pptx': ['pdf', 'ppt'],
    'odp': ['pdf', 'pptx'],
    
    # Audio (limited conversions)
    'mp3': ['wav', 'aac', 'ogg'],
    'wav': ['mp3', 'aac', 'ogg'],
    'flac': ['mp3', 'wav', 'ogg'],
    'aac': ['mp3', 'wav'],
    'm4a': ['mp3', 'wav'],
    'ogg': ['mp3', 'wav'],
    
    # Video
    'mp4': ['mp3', 'gif', 'webm', 'avi'],
    'mkv': ['mp3', 'mp4', 'webm'],
    'mov': ['mp3', 'mp4', 'gif', 'webm'],
    'avi': ['mp3', 'mp4', 'webm'],
    'webm': ['mp4', 'mp3'],
    'flv': ['mp4', 'mp3'],
    
    # Archives
    'zip': ['tar', '7z'],
    'rar': ['zip'],
    '7z': ['zip', 'tar'],
    'tar': ['zip', '7z'],
    
    # Code & Data
    'json': ['csv', 'xml', 'yaml', 'txt'],
    'xml': ['json', 'txt'],
    'yaml': ['json', 'txt'],
    'yml': ['json', 'txt'],
    'html': ['pdf', 'txt'],
}


class FileConverter:
    """Main file converter class"""
    
    def __init__(self):
        self.temp_dir = None
    
    def convert(self, input_file, from_format, to_format, file_uuid):
        """
        Convert file from one format to another
        
        Args:
            input_file: Path to input file
            from_format: Source format (without dot)
            to_format: Target format (without dot)
            file_uuid: UUID for output filename
        
        Returns:
            Path to converted file
        """
        self.temp_dir = Path(input_file).parent
        from_format = from_format.lower()
        to_format = to_format.lower()
        
        # Route to appropriate converter
        if from_format in ['pdf'] and to_format in ['docx', 'txt', 'odt']:
            return self._convert_pdf_to_document(input_file, to_format, file_uuid)
        
        elif from_format in ['pdf'] and to_format in ['png', 'jpg']:
            return self._convert_pdf_to_image(input_file, to_format, file_uuid)
        
        elif from_format in ['docx', 'doc', 'odt', 'txt', 'rtf'] and to_format in ['pdf', 'docx', 'odt', 'txt']:
            return self._convert_document(input_file, from_format, to_format, file_uuid)
        
        elif from_format in ['jpg', 'jpeg', 'png', 'webp', 'tiff', 'bmp', 'gif']:
            if to_format == 'pdf':
                return self._convert_image_to_pdf(input_file, file_uuid)
            else:
                return self._convert_image(input_file, to_format, file_uuid)
        
        elif from_format in ['xlsx', 'xls', 'csv'] and to_format in ['xlsx', 'xls', 'csv', 'txt', 'pdf']:
            return self._convert_spreadsheet(input_file, from_format, to_format, file_uuid)
        
        elif from_format in ['mp4', 'avi', 'mov'] and to_format in ['mp3', 'gif']:
            return self._convert_video(input_file, to_format, file_uuid)
        
        else:
            raise ValueError(f"Conversion from {from_format} to {to_format} not implemented")
    
    def _convert_pdf_to_document(self, input_file, to_format, file_uuid):
        """Convert PDF to document formats using LibreOffice"""
        output_file = self.temp_dir / f"{file_uuid}_converted.{to_format}"
        
        try:
            # Use LibreOffice for conversion
            cmd = [
                'soffice',
                '--headless',
                '--convert-to', to_format,
                '--outdir', str(self.temp_dir),
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                # Fallback: extract text from PDF for txt format
                if to_format == 'txt':
                    return self._extract_text_from_pdf(input_file, file_uuid)
                raise Exception(f"LibreOffice conversion failed: {result.stderr}")
            
            # Rename output file
            temp_output = self.temp_dir / f"{Path(input_file).stem}.{to_format}"
            if temp_output.exists():
                temp_output.rename(output_file)
            
            return str(output_file)
        
        except subprocess.TimeoutExpired:
            raise Exception("Conversion timeout (60 seconds)")
        except FileNotFoundError:
            raise Exception("LibreOffice not installed. Please install: sudo apt-get install libreoffice")
    
    def _extract_text_from_pdf(self, input_file, file_uuid):
        """Fallback text extraction from PDF using PyPDF2"""
        try:
            import PyPDF2
            output_file = self.temp_dir / f"{file_uuid}_converted.txt"
            
            with open(input_file, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text = ''
                for page in pdf_reader.pages:
                    text += page.extract_text() + '\n\n'
            
            with open(output_file, 'w', encoding='utf-8') as txt_file:
                txt_file.write(text)
            
            return str(output_file)
        except ImportError:
            raise Exception("PyPDF2 not installed. Install: pip install PyPDF2")
    
    def _convert_pdf_to_image(self, input_file, to_format, file_uuid):
        """Convert PDF to image using pdf2image"""
        try:
            from pdf2image import convert_from_path
            
            # Convert first page to image
            images = convert_from_path(input_file, first_page=1, last_page=1)
            
            if not images:
                raise Exception("No pages found in PDF")
            
            output_file = self.temp_dir / f"{file_uuid}_converted.{to_format}"
            images[0].save(output_file, format=to_format.upper())
            
            return str(output_file)
        
        except ImportError:
            raise Exception("pdf2image not installed. Install: pip install pdf2image")
    
    def _convert_document(self, input_file, from_format, to_format, file_uuid):
        """Convert between document formats using LibreOffice"""
        output_file = self.temp_dir / f"{file_uuid}_converted.{to_format}"
        
        try:
            cmd = [
                'soffice',
                '--headless',
                '--convert-to', to_format,
                '--outdir', str(self.temp_dir),
                input_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode != 0:
                raise Exception(f"Conversion failed: {result.stderr}")
            
            # Rename output
            temp_output = self.temp_dir / f"{Path(input_file).stem}.{to_format}"
            if temp_output.exists():
                temp_output.rename(output_file)
            
            return str(output_file)
        
        except subprocess.TimeoutExpired:
            raise Exception("Conversion timeout")
        except FileNotFoundError:
            raise Exception("LibreOffice not installed")
    
    def _convert_image(self, input_file, to_format, file_uuid):
        """Convert between image formats using Pillow"""
        output_file = self.temp_dir / f"{file_uuid}_converted.{to_format}"
        
        try:
            img = Image.open(input_file)
            
            # Handle transparency for formats that don't support it
            if to_format.lower() in ['jpg', 'jpeg'] and img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            # Save in new format
            img.save(output_file, format=to_format.upper())
            
            return str(output_file)
        
        except Exception as e:
            raise Exception(f"Image conversion failed: {str(e)}")
    
    def _convert_image_to_pdf(self, input_file, file_uuid):
        """Convert image to PDF"""
        output_file = self.temp_dir / f"{file_uuid}_converted.pdf"
        
        try:
            img = Image.open(input_file)
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            img.save(output_file, 'PDF')
            
            return str(output_file)
        
        except Exception as e:
            raise Exception(f"PDF conversion failed: {str(e)}")
    
    def _convert_spreadsheet(self, input_file, from_format, to_format, file_uuid):
        """Convert between spreadsheet formats using pandas"""
        output_file = self.temp_dir / f"{file_uuid}_converted.{to_format}"
        
        try:
            # Read file
            if from_format == 'csv':
                df = pd.read_csv(input_file)
            else:  # xlsx or xls
                df = pd.read_excel(input_file)
            
            # Write file
            if to_format == 'csv':
                df.to_csv(output_file, index=False)
            elif to_format == 'txt':
                df.to_csv(output_file, index=False, sep='\t')
            elif to_format == 'xlsx':
                df.to_excel(output_file, index=False, engine='openpyxl')
            elif to_format == 'xls':
                df.to_excel(output_file, index=False, engine='xlwt')
            elif to_format == 'pdf':
                # Convert to HTML then use LibreOffice
                html_file = self.temp_dir / f"{file_uuid}_temp.html"
                df.to_html(html_file, index=False)
                return self._convert_document(str(html_file), 'html', 'pdf', file_uuid)
            
            return str(output_file)
        
        except Exception as e:
            raise Exception(f"Spreadsheet conversion failed: {str(e)}")
    
    def _convert_video(self, input_file, to_format, file_uuid):
        """Convert video using ffmpeg"""
        output_file = self.temp_dir / f"{file_uuid}_converted.{to_format}"
        
        try:
            if to_format == 'mp3':
                # Extract audio
                cmd = [
                    'ffmpeg',
                    '-i', input_file,
                    '-vn',  # No video
                    '-acodec', 'libmp3lame',
                    '-q:a', '2',  # Quality
                    '-y',  # Overwrite
                    str(output_file)
                ]
            elif to_format == 'gif':
                # Convert to GIF (first 5 seconds)
                cmd = [
                    'ffmpeg',
                    '-i', input_file,
                    '-t', '5',  # Duration
                    '-vf', 'fps=10,scale=320:-1:flags=lanczos',
                    '-y',
                    str(output_file)
                ]
            else:
                raise ValueError(f"Unsupported video conversion to {to_format}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                raise Exception(f"ffmpeg conversion failed: {result.stderr}")
            
            return str(output_file)
        
        except subprocess.TimeoutExpired:
            raise Exception("Video conversion timeout (120 seconds)")
        except FileNotFoundError:
            raise Exception("ffmpeg not installed. Install: sudo apt-get install ffmpeg")
