import os
import logging
import pytube
import yt_dlp
from urllib.parse import urlparse
from datetime import datetime
from django.core.cache import cache
from .proxy_rotator import get_valid_proxy

logger = logging.getLogger(__name__)

class DownloadError(Exception):
    """Custom exception for download failures"""
    pass

def clean_filename(title):
    """Sanitize filenames"""
    keepchars = (' ', '.', '_', '-')
    return "".join(c for c in title if c.isalnum() or c in keepchars).strip()

def get_platform(url):
    """Detect video platform from URL"""
    domain = urlparse(url).netloc.lower()
    if any(x in domain for x in ['youtube.com', 'youtu.be']):
        return 'youtube'
    elif 'instagram.com' in domain:
        return 'instagram'
    elif 'tiktok.com' in domain:
        return 'tiktok'
    return 'generic'

def download_media(url, quality='best'):
    """
    Main download function with:
    - Proxy rotation
    - Caching
    - Error handling
    - Platform detection
    """
    cache_key = f"dl_{hash(url)}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    platform = get_platform(url)
    result = {
        'platform': platform,
        'original_url': url,
        'timestamp': datetime.now().isoformat()
    }

    try:
        if platform == 'youtube':
            result.update(_download_youtube(url, quality))
        else:
            result.update(_download_generic(url))
        
        cache.set(cache_key, result, timeout=3600)  # Cache for 1 hour
        return result

    except Exception as e:
        logger.error(f"Download failed for {url}: {str(e)}", exc_info=True)
        raise DownloadError(f"Failed to download video: {str(e)}")

def _download_youtube(url, quality):
    """YouTube-specific downloader"""
    proxy = get_valid_proxy()
    proxies = {'http': proxy, 'https': proxy} if proxy else None
    
    try:
        yt = YouTube(
            url,
            proxies=proxies,
            use_oauth=False,
            allow_oauth_cache=False
        )
        
        stream = (yt.streams.get_highest_resolution() if quality == 'best'
                 else yt.streams.filter(progressive=True, file_extension='mp4').first())
        
        if not stream:
            raise DownloadError("No suitable stream found")

        filename = f"{clean_filename(yt.title)}.mp4"
        download_path = os.path.join('media', 'youtube')
        os.makedirs(download_path, exist_ok=True)
        filepath = os.path.join(download_path, filename)
        
        stream.download(
            output_path=download_path,
            filename=filename,
            timeout=30,
            max_retries=2
        )

        return {
            'status': 'success',
            'filepath': filepath,
            'filename': filename,
            'title': yt.title,
            'duration': yt.length,
            'thumbnail': yt.thumbnail_url
        }

    except Exception as e:
        raise DownloadError(f"YouTube download failed: {str(e)}")

def _download_generic(url):
    """Generic downloader for other platforms"""
    proxy = get_valid_proxy()
    ydl_opts = {
        'format': 'best',
        'quiet': True,
        'proxy': proxy,
        'no_check_certificate': True,
        'socket_timeout': 30,
        'extract_flat': False,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': 'https://www.google.com/'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            return {
                'status': 'success',
                'filepath': filename,
                'filename': os.path.basename(filename),
                'title': info.get('title', 'video'),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', '')
            }
    except Exception as e:
        raise DownloadError(f"Generic download failed: {str(e)}")