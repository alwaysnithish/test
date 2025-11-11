import mimetypes
from pathlib import Path

# Allowed extensions and their MIME types
ALLOWED_MIMES = {
    # Documents
    '.pdf': ['application/pdf'],
    '.docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    '.doc': ['application/msword'],
    '.odt': ['application/vnd.oasis.opendocument.text'],
    '.txt': ['text/plain'],
    '.rtf': ['application/rtf', 'text/rtf'],
    '.md': ['text/markdown', 'text/plain'],
    '.epub': ['application/epub+zip'],
    
    # Images
    '.jpg': ['image/jpeg'],
    '.jpeg': ['image/jpeg'],
    '.png': ['image/png'],
    '.webp': ['image/webp'],
    '.tiff': ['image/tiff'],
    '.bmp': ['image/bmp', 'image/x-ms-bmp'],
    '.gif': ['image/gif'],
    '.heic': ['image/heic', 'image/heif'],
    '.heif': ['image/heif'],
    '.svg': ['image/svg+xml'],
    
    # Spreadsheets
    '.xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
    '.xls': ['application/vnd.ms-excel'],
    '.ods': ['application/vnd.oasis.opendocument.spreadsheet'],
    '.csv': ['text/csv', 'text/plain'],
    
    # Presentations
    '.ppt': ['application/vnd.ms-powerpoint'],
    '.pptx': ['application/vnd.openxmlformats-officedocument.presentationml.presentation'],
    '.odp': ['application/vnd.oasis.opendocument.presentation'],
    
    # Audio
    '.mp3': ['audio/mpeg'],
    '.wav': ['audio/wav', 'audio/x-wav'],
    '.flac': ['audio/flac'],
    '.aac': ['audio/aac', 'audio/x-aac'],
    '.m4a': ['audio/mp4', 'audio/x-m4a'],
    '.ogg': ['audio/ogg'],
    
    # Video
    '.mp4': ['video/mp4'],
    '.avi': ['video/x-msvideo'],
    '.mov': ['video/quicktime'],
    '.mkv': ['video/x-matroska'],
    '.webm': ['video/webm'],
    '.flv': ['video/x-flv'],
    
    # Archives
    '.zip': ['application/zip'],
    '.rar': ['application/x-rar-compressed'],
    '.7z': ['application/x-7z-compressed'],
    '.tar': ['application/x-tar'],
    '.gz': ['application/gzip'],
    
    # Code & Data
    '.json': ['application/json'],
    '.xml': ['application/xml', 'text/xml'],
    '.yaml': ['text/yaml', 'application/x-yaml'],
    '.yml': ['text/yaml', 'application/x-yaml'],
    '.html': ['text/html'],
}


class FileHandler:
    """Handle file validation and security checks"""
    
    def __init__(self):
        self.allowed_extensions = set(ALLOWED_MIMES.keys())
    
    def is_valid_extension(self, extension):
        """Check if file extension is allowed"""
        return extension.lower() in self.allowed_extensions
    
    def is_valid_mime(self, mime_type, extension):
        """Validate MIME type matches extension"""
        if not mime_type:
            return False
        
        allowed_mimes = ALLOWED_MIMES.get(extension.lower(), [])
        return mime_type in allowed_mimes
    
    def sanitize_filename(self, filename):
        """Sanitize filename to prevent path traversal"""
        # Get just the filename without path
        filename = Path(filename).name
        
        # Remove any potentially dangerous characters
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        for char in dangerous_chars:
            filename = filename.replace(char, '_')
        
        return filename
    
    def get_file_info(self, filepath):
        """Get file information"""
        path = Path(filepath)
        
        return {
            'name': path.name,
            'size': path.stat().st_size,
            'extension': path.suffix,
            'mime_type': mimetypes.guess_type(filepath)[0]
        }
