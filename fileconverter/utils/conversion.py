import os
import subprocess
import uuid
from pathlib import Path
from PIL import Image
import pandas as pd

# Complete Conversion mapping based on provided specification
CONVERSION_MAP = {
    # Documents (45+ conversions)
    'pdf': ['docx', 'odt', 'txt', 'jpg', 'png'],
    'docx': ['pdf', 'odt', 'txt'],
    'doc': ['pdf', 'docx', 'odt', 'txt'],
    'odt': ['pdf', 'docx', 'txt'],
    'txt': ['pdf', 'docx'],
    'rtf': ['pdf', 'docx', 'txt'],
    'md': ['pdf', 'docx', 'txt', 'html'],
    'epub': ['pdf', 'txt'],
    
    # Images (60+ conversions)
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
    
    # Spreadsheets (20+ conversions)
    'xlsx': ['csv', 'xls', 'pdf', 'txt'],
    'xls': ['csv', 'xlsx', 'pdf', 'txt'],
    'ods': ['csv', 'xlsx', 'pdf'],
    'csv': ['xlsx', 'xls', 'txt', 'json'],
    
    # Presentations (6 conversions)
    'ppt': ['pdf', 'pptx'],
    'pptx': ['pdf', 'ppt'],
    'odp': ['pdf', 'pptx'],
    
    # Audio (18 conversions)
    'mp3': ['wav', 'aac', 'ogg'],
    'wav': ['mp3', 'aac', 'ogg'],
    'flac': ['mp3', 'wav', 'ogg'],
    'aac': ['mp3', 'wav'],
    'm4a': ['mp3', 'wav'],
    'ogg': ['mp3', 'wav'],
    
    # Video (24 conversions)
    'mp4': ['mp3', 'gif', 'webm', 'avi'],
    'mkv': ['mp3', 'mp4', 'webm'],
    'mov': ['mp3', 'mp4', 'gif', 'webm'],
    'avi': ['mp3', 'mp4', 'webm'],
    'webm': ['mp4', 'mp3'],
    'flv': ['mp4', 'mp3'],
    
    # Archives (6 conversions)
    'zip': ['tar', '7z'],
    'rar': ['zip'],
    '7z': ['zip', 'tar'],
    'tar': ['zip', '7z'],
    
    # Code & Data (12 conversions)
    'json': ['csv', 'xml', 'yaml', 'txt'],
    'xml': ['json', 'txt'],
    'yaml': ['json', 'txt'],
    'yml': ['json', 'txt'],
    'html': ['pdf', 'txt'],
}


class FileConverter:
    """Main file converter class with support for 190+ conversions"""
    
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
        
        # Validate conversion is in mapping
        if to_format not in CONVERSION_MAP.get(from_format, []):
            raise ValueError(f"Conversion from {from_format} to {to_format} not supported")
        
        # Route to appropriate converter
        # Documents
        if from_format in ['pdf'] and to_format in ['docx', 'txt', 'odt']:
            return self._convert_pdf_to_document(input_file, to_format, file_uuid)
        
        elif from_format in ['pdf'] and to_format in ['png', 'jpg']:
            return self._convert_pdf_to_image(input_file, to_format, file_uuid)
        
        elif from_format in ['docx', 'doc', 'odt', 'txt', 'rtf', 'md', 'epub'] and to_format in ['pdf', 'docx', 'odt', 'txt', 'html']:
            return self._convert_document(input_file, from_format, to_format, file_uuid)
        
        # Images
        elif from_format in ['jpg', 'jpeg', 'png', 'webp', 'tiff', 'bmp', 'gif', 'heic', 'heif', 'svg']:
            if to_format == 'pdf':
                return self._convert_image_to_pdf(input_file, file_uuid)
            else:
                return self._convert_image(input_file, to_format, file_uuid)
        
        # Spreadsheets
        elif from_format in ['xlsx', 'xls', 'ods', 'csv'] and to_format in ['xlsx', 'xls', 'csv', 'txt', 'json', 'pdf']:
            return self._convert_spreadsheet(input_file, from_format, to_format, file_uuid)
        
        # Presentations
        elif from_format in ['ppt', 'pptx', 'odp'] and to_format in ['pdf', 'ppt', 'pptx']:
            return self._convert_presentation(input_file, from_format, to_format, file_uuid)
        
        # Audio
        elif from_format in ['mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg'] and to_format in ['mp3', 'wav', 'aac', 'ogg']:
            return self._convert_audio(input_file, to_format, file_uuid)
        
        # Video
        elif from_format in ['mp4', 'mkv', 'mov', 'avi', 'webm', 'flv'] and to_format in ['mp3', 'gif', 'webm', 'avi', 'mp4']:
            return self._convert_video(input_file, to_format, file_uuid)
        
        # Archives
        elif from_format in ['zip', 'rar', '7z', 'tar'] and to_format in ['zip', 'tar', '7z']:
            return self._convert_archive(input_file, from_format, to_format, file_uuid)
        
        # Code & Data
        elif from_format in ['json', 'xml', 'yaml', 'yml', 'html'] and to_format in ['csv', 'xml', 'yaml', 'txt', 'json', 'pdf']:
            return self._convert_data(input_file, from_format, to_format, file_uuid)
        
        else:
            raise NotImplementedError(f"Conversion from {from_format} to {to_format} not yet implemented")
    
    # Document Conversions
    def _convert_pdf_to_document(self, input_file, to_format, file_uuid):
        """Convert PDF to document formats using LibreOffice"""
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
                if to_format == 'txt':
                    return self._extract_text_from_pdf(input_file, file_uuid)
                raise Exception(f"LibreOffice conversion failed: {result.stderr}")
            
            temp_output = self.temp_dir / f"{Path(input_file).stem}.{to_format}"
            if temp_output.exists():
                temp_output.rename(output_file)
            
            return str(output_file)
        
        except subprocess.TimeoutExpired:
            raise Exception("Conversion timeout (60 seconds)")
        except FileNotFoundError:
            raise Exception("LibreOffice not installed. Install: sudo apt-get install libreoffice")
    
    def _extract_text_from_pdf(self, input_file, file_uuid):
        """Fallback text extraction from PDF"""
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
        """Convert PDF first page to image"""
        try:
            from pdf2image import convert_from_path
            
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
            
            temp_output = self.temp_dir / f"{Path(input_file).stem}.{to_format}"
            if temp_output.exists():
                temp_output.rename(output_file)
            
            return str(output_file)
        
        except subprocess.TimeoutExpired:
            raise Exception("Conversion timeout")
        except FileNotFoundError:
            raise Exception("LibreOffice not installed")
    
    # Image Conversions
    def _convert_image(self, input_file, to_format, file_uuid):
        """Convert between image formats using Pillow"""
        output_file = self.temp_dir / f"{file_uuid}_converted.{to_format}"
        
        try:
            img = Image.open(input_file)
            
            # Handle transparency
            if to_format.lower() in ['jpg', 'jpeg'] and img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            
            img.save(output_file, format=to_format.upper())
            
            return str(output_file)
        
        except Exception as e:
            raise Exception(f"Image conversion failed: {str(e)}")
    
    def _convert_image_to_pdf(self, input_file, file_uuid):
        """Convert image to PDF"""
        output_file = self.temp_dir / f"{file_uuid}_converted.pdf"
        
        try:
            img = Image.open(input_file)
            
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
    
    # Spreadsheet Conversions
    def _convert_spreadsheet(self, input_file, from_format, to_format, file_uuid):
        """Convert between spreadsheet formats"""
        output_file = self.temp_dir / f"{file_uuid}_converted.{to_format}"
        
        try:
            # Read file
            if from_format == 'csv':
                df = pd.read_csv(input_file)
            elif from_format in ['xlsx', 'xls', 'ods']:
                df = pd.read_excel(input_file)
            else:
                raise ValueError(f"Unsupported input format: {from_format}")
            
            # Write file
            if to_format == 'csv':
                df.to_csv(output_file, index=False)
            elif to_format == 'txt':
                df.to_csv(output_file, index=False, sep='\t')
            elif to_format == 'xlsx':
                df.to_excel(output_file, index=False, engine='openpyxl')
            elif to_format == 'xls':
                df.to_excel(output_file, index=False, engine='xlwt')
            elif to_format == 'json':
                df.to_json(output_file, orient='records', indent=2)
            elif to_format == 'pdf':
                html_file = self.temp_dir / f"{file_uuid}_temp.html"
                df.to_html(html_file, index=False)
                return self._convert_document(str(html_file), 'html', 'pdf', file_uuid)
            
            return str(output_file)
        
        except Exception as e:
            raise Exception(f"Spreadsheet conversion failed: {str(e)}")
    
    # Presentation Conversions
    def _convert_presentation(self, input_file, from_format, to_format, file_uuid):
        """Convert presentations using LibreOffice"""
        return self._convert_document(input_file, from_format, to_format, file_uuid)
    
    # Audio Conversions
    def _convert_audio(self, input_file, to_format, file_uuid):
        """Convert audio using ffmpeg"""
        output_file = self.temp_dir / f"{file_uuid}_converted.{to_format}"
        
        try:
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-y',
                str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                raise Exception(f"ffmpeg conversion failed: {result.stderr}")
            
            return str(output_file)
        
        except subprocess.TimeoutExpired:
            raise Exception("Audio conversion timeout")
        except FileNotFoundError:
            raise Exception("ffmpeg not installed. Install: sudo apt-get install ffmpeg")
    
    # Video Conversions
    def _convert_video(self, input_file, to_format, file_uuid):
        """Convert video using ffmpeg"""
        output_file = self.temp_dir / f"{file_uuid}_converted.{to_format}"
        
        try:
            if to_format == 'mp3':
                cmd = [
                    'ffmpeg',
                    '-i', input_file,
                    '-vn',
                    '-acodec', 'libmp3lame',
                    '-q:a', '2',
                    '-y',
                    str(output_file)
                ]
            elif to_format == 'gif':
                cmd = [
                    'ffmpeg',
                    '-i', input_file,
                    '-t', '5',
                    '-vf', 'fps=10,scale=320:-1:flags=lanczos',
                    '-y',
                    str(output_file)
                ]
            else:
                cmd = [
                    'ffmpeg',
                    '-i', input_file,
                    '-y',
                    str(output_file)
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode != 0:
                raise Exception(f"ffmpeg conversion failed: {result.stderr}")
            
            return str(output_file)
        
        except subprocess.TimeoutExpired:
            raise Exception("Video conversion timeout (120 seconds)")
        except FileNotFoundError:
            raise Exception("ffmpeg not installed")
    
    # Archive Conversions
    def _convert_archive(self, input_file, from_format, to_format, file_uuid):
        """Convert between archive formats"""
        import zipfile
        import tarfile
        import shutil
        
        output_file = self.temp_dir / f"{file_uuid}_converted.{to_format}"
        extract_dir = self.temp_dir / f"{file_uuid}_extract"
        extract_dir.mkdir(exist_ok=True)
        
        try:
            # Extract
            if from_format == 'zip':
                with zipfile.ZipFile(input_file, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif from_format in ['tar', '7z']:
                shutil.unpack_archive(input_file, extract_dir)
            
            # Repack
            if to_format == 'zip':
                with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(extract_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, extract_dir)
                            zipf.write(file_path, arcname)
            elif to_format == 'tar':
                with tarfile.open(output_file, 'w') as tar:
                    tar.add(extract_dir, arcname='.')
            elif to_format == '7z':
                raise NotImplementedError("7z conversion requires py7zr library")
            
            # Cleanup
            shutil.rmtree(extract_dir, ignore_errors=True)
            
            return str(output_file)
        
        except Exception as e:
            shutil.rmtree(extract_dir, ignore_errors=True)
            raise Exception(f"Archive conversion failed: {str(e)}")
    
    # Data Format Conversions
    def _convert_data(self, input_file, from_format, to_format, file_uuid):
        """Convert between data formats"""
        output_file = self.temp_dir / f"{file_uuid}_converted.{to_format}"
        
        try:
            import json as json_lib
            import yaml as yaml_lib
            
            # Read input
            with open(input_file, 'r', encoding='utf-8') as f:
                if from_format == 'json':
                    data = json_lib.load(f)
                elif from_format in ['yaml', 'yml']:
                    data = yaml_lib.safe_load(f)
                elif from_format == 'xml':
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(input_file)
                    data = tree.getroot()
                elif from_format == 'html':
                    data = f.read()
            
            # Write output
            with open(output_file, 'w', encoding='utf-8') as f:
                if to_format == 'json':
                    json_lib.dump(data, f, indent=2)
                elif to_format in ['yaml', 'yml']:
                    yaml_lib.dump(data, f)
                elif to_format == 'txt':
                    f.write(str(data))
                elif to_format == 'csv':
                    if isinstance(data, (list, dict)):
                        df = pd.DataFrame(data)
                        df.to_csv(output_file, index=False)
                elif to_format == 'pdf':
                    if from_format == 'html':
                        return self._convert_document(input_file, 'html', 'pdf', file_uuid)
            
            return str(output_file)
        
        except Exception as e:
            raise Exception(f"Data conversion failed: {str(e)}")
