import os
import re
import random
import time
import logging
import asyncio
import threading
from urllib.parse import urlparse, parse_qs
from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache
import yt_dlp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Enhanced Helper Functions

def get_random_headers():
    """Enhanced user agents with more variety and recent versions"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0',
    ]
    
    additional_headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.9', 'en-CA,en;q=0.9']),
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }
    
    headers = additional_headers.copy()
    headers['User-Agent'] = random.choice(user_agents)
    return headers

def get_proxy_list():
    """Get rotating proxy list - implement your proxy service here"""
    # Add your proxy endpoints here
    proxies = [
        # 'http://proxy1:port',
        # 'http://proxy2:port',
        # 'socks5://proxy3:port',
    ]
    return random.choice(proxies) if proxies else None

def detect_platform(url):
    """Enhanced platform detection with more services"""
    url = url.lower().strip()
    platform_patterns = {
        'youtube': [r'youtube\.com', r'youtu\.be', r'youtube-nocookie\.com'],
        'instagram': [r'instagram\.com', r'instagr\.am'],
        'tiktok': [r'tiktok\.com', r'vm\.tiktok\.com', r'vt\.tiktok\.com'],
        'facebook': [r'facebook\.com', r'fb\.watch', r'fb\.me'],
        'twitter': [r'twitter\.com', r'x\.com', r't\.co'],
        'reddit': [r'reddit\.com', r'redd\.it'],
        'twitch': [r'twitch\.tv', r'clips\.twitch\.tv'],
        'vimeo': [r'vimeo\.com', r'player\.vimeo\.com'],
        'dailymotion': [r'dailymotion\.com', r'dai\.ly'],
        'streamable': [r'streamable\.com'],
        'imgur': [r'imgur\.com', r'i\.imgur\.com'],
        'soundcloud': [r'soundcloud\.com', r'snd\.sc'],
        'pinterest': [r'pinterest\.com', r'pin\.it'],
        'linkedin': [r'linkedin\.com'],
        'snapchat': [r'snapchat\.com'],
        'discord': [r'discord\.com', r'discordapp\.com'],
        'telegram': [r't\.me', r'telegram\.me'],
        'bitchute': [r'bitchute\.com'],
        'rumble': [r'rumble\.com'],
        'odysee': [r'odysee\.com', r'lbry\.tv'],
        'peertube': [r'peertube'],
    }
    
    for platform, patterns in platform_patterns.items():
        if any(re.search(pattern, url) for pattern in patterns):
            return platform
    return 'other'

def sanitize_filename(filename):
    """Enhanced filename sanitization"""
    # Remove or replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'[^\w\s-_\.]', '', filename)
    filename = re.sub(r'[-_\s]+', '_', filename)
    return filename.strip('_')[:200]

def get_enhanced_ydl_opts(quality='best', audio_only=False, proxy=None):
    """Get enhanced yt-dlp options with anti-blocking measures"""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'no_check_certificate': True,
        'prefer_insecure': False,
        'http_headers': get_random_headers(),
        'sleep_interval': random.uniform(1, 3),
        'max_sleep_interval': 5,
        'sleep_interval_requests': random.uniform(0.5, 1.5),
        'sleep_interval_subtitles': random.uniform(1, 2),
        'retries': 10,
        'fragment_retries': 10,
        'skip_unavailable_fragments': True,
        'keep_fragments': False,
        'concurrent_fragment_downloads': 4,
        'throttled_rate': '100K',  # Rate limiting to avoid detection
        'extract_flat': False,
        'writethumbnail': False,
        'writeinfojson': False,
        'geo_bypass': True,
        'geo_bypass_country': random.choice(['US', 'GB', 'CA', 'AU', 'DE']),
    }
    
    # Quality settings
    if audio_only:
        opts['format'] = 'bestaudio/best'
    else:
        quality_formats = {
            'best': 'best[height<=1080]/best',
            'high': 'best[height<=720]/best',
            'medium': 'best[height<=480]/best',
            'low': 'worst[height>=240]/worst',
        }
        opts['format'] = quality_formats.get(quality, 'best[height<=1080]/best')
    
    # Proxy configuration
    if proxy:
        opts['proxy'] = proxy
    
    # Platform-specific optimizations
    opts['extractor_args'] = {
        'youtube': {
            'skip': ['hls', 'dash'],
            'player_skip': ['js'],
        },
        'tiktok': {
            'api_hostname': 'api16-normal-c-useast1a.tiktokv.com',
        },
        'instagram': {
            'api_hostname': 'i.instagram.com',
        }
    }
    
    return opts

# Core Functions

def get_video_info(url, use_cache=True):
    """Enhanced video info extraction with caching and retry logic"""
    try:
        # Check cache first
        cache_key = f"video_info_{hash(url)}"
        if use_cache:
            cached_info = cache.get(cache_key)
            if cached_info:
                return cached_info
        
        # Add random delay to avoid rate limiting
        time.sleep(random.uniform(0.5, 2.0))
        
        # Try with different configurations
        configs = [
            {'proxy': None, 'geo_bypass_country': 'US'},
            {'proxy': get_proxy_list(), 'geo_bypass_country': 'GB'},
            {'proxy': None, 'geo_bypass_country': 'CA'},
        ]
        
        for config in configs:
            try:
                ydl_opts = get_enhanced_ydl_opts()
                if config['proxy']:
                    ydl_opts['proxy'] = config['proxy']
                ydl_opts['geo_bypass_country'] = config['geo_bypass_country']
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    result = {
                        'status': 'success',
                        'title': info.get('title', 'Untitled'),
                        'thumbnail': info.get('thumbnail', ''),
                        'duration': info.get('duration', 0),
                        'uploader': info.get('uploader', 'Unknown'),
                        'platform': detect_platform(url),
                        'view_count': info.get('view_count', 0),
                        'upload_date': info.get('upload_date', ''),
                        'description': info.get('description', '')[:500] if info.get('description') else '',
                        'formats_available': len(info.get('formats', [])),
                        'has_audio': any(f.get('acodec', 'none') != 'none' for f in info.get('formats', [])),
                        'has_video': any(f.get('vcodec', 'none') != 'none' for f in info.get('formats', [])),
                    }
                    
                    # Cache successful result
                    if use_cache:
                        cache.set(cache_key, result, timeout=3600)  # Cache for 1 hour
                    
                    return result
                    
            except Exception as e:
                logger.warning(f"Config failed: {config}, Error: {str(e)}")
                continue
        
        return {'status': 'error', 'message': 'All extraction methods failed'}
        
    except Exception as e:
        logger.error(f"Info extraction error: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def download_video_file(url, quality='best', audio_only=False):
    """Enhanced download with multiple retry strategies"""
    try:
        download_path = os.path.join(settings.MEDIA_ROOT, 'downloads')
        os.makedirs(download_path, exist_ok=True)
        
        # Clean old files periodically
        cleanup_old_files(download_path)
        
        # Add random delay
        time.sleep(random.uniform(1.0, 3.0))
        
        # Try multiple download strategies
        strategies = [
            {'proxy': None, 'concurrent_downloads': 1},
            {'proxy': get_proxy_list(), 'concurrent_downloads': 1},
            {'proxy': None, 'concurrent_downloads': 4},
        ]
        
        for strategy in strategies:
            try:
                ydl_opts = get_enhanced_ydl_opts(quality=quality, audio_only=audio_only, proxy=strategy['proxy'])
                ydl_opts['outtmpl'] = os.path.join(download_path, '%(title)s.%(ext)s')
                ydl_opts['concurrent_fragment_downloads'] = strategy['concurrent_downloads']
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # Get info first
                    info = ydl.extract_info(url, download=False)
                    expected_filename = sanitize_filename(info['title'])
                    
                    # Download the video
                    ydl.download([url])
                    
                    # Find the downloaded file
                    for file in os.listdir(download_path):
                        if expected_filename in sanitize_filename(file):
                            file_path = os.path.join(download_path, file)
                            file_size = os.path.getsize(file_path)
                            
                            return {
                                'status': 'success',
                                'filename': file,
                                'file_size': format_file_size(file_size),
                                'download_url': f"/media/downloads/{file}",
                                'title': info.get('title', 'Untitled'),
                                'duration': info.get('duration', 0),
                                'platform': detect_platform(url),
                            }
                
            except Exception as e:
                logger.warning(f"Download strategy failed: {strategy}, Error: {str(e)}")
                continue
        
        return {'status': 'error', 'message': 'All download strategies failed'}
        
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return {'status': 'error', 'message': str(e)}

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes >= 1024*1024*1024:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"
    elif size_bytes >= 1024*1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes/1024:.1f} KB"
    else:
        return f"{size_bytes} B"

def cleanup_old_files(download_path, max_age_hours=24):
    """Clean up old downloaded files"""
    try:
        current_time = time.time()
        for filename in os.listdir(download_path):
            file_path = os.path.join(download_path, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_hours * 3600:
                    os.remove(file_path)
                    logger.info(f"Cleaned up old file: {filename}")
    except Exception as e:
        logger.warning(f"Cleanup error: {str(e)}")

# Views

def video_downloader(request):
    """Main downloader page"""
    return render(request, 'videodownloader/index.html')

@csrf_exempt
def get_video_info_api(request):
    """Enhanced video info API with better error handling"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)

    url = request.POST.get('url', '').strip()
    if not url:
        return JsonResponse({'status': 'error', 'message': 'URL is required'}, status=400)
    
    # Validate URL format
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return JsonResponse({'status': 'error', 'message': 'Invalid URL format'}, status=400)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid URL'}, status=400)
    
    # Add random delay to avoid detection
    time.sleep(random.uniform(0.5, 2.0))
    
    result = get_video_info(url)
    return JsonResponse(result)

@csrf_exempt
def download_video_api(request):
    """Enhanced download API with quality and format options"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'POST method required'}, status=405)

    url = request.POST.get('url', '').strip()
    quality = request.POST.get('quality', 'best')
    audio_only = request.POST.get('audio_only', 'false').lower() == 'true'
    
    if not url:
        return JsonResponse({'status': 'error', 'message': 'URL is required'}, status=400)
    
    # Validate URL format
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return JsonResponse({'status': 'error', 'message': 'Invalid URL format'}, status=400)
    except Exception:
        return JsonResponse({'status': 'error', 'message': 'Invalid URL'}, status=400)
    
    # Validate quality parameter
    valid_qualities = ['best', 'high', 'medium', 'low']
    if quality not in valid_qualities:
        quality = 'best'
    
    # Add random delay
    time.sleep(random.uniform(1.0, 3.0))
    
    result = download_video_file(url, quality=quality, audio_only=audio_only)
    return JsonResponse(result)

def serve_download(request, filename):
    """Enhanced file serving with better security"""
    # Sanitize filename to prevent path traversal
    filename = os.path.basename(filename)
    file_path = os.path.join(settings.MEDIA_ROOT, 'downloads', filename)
    
    # Security check
    if not file_path.startswith(os.path.join(settings.MEDIA_ROOT, 'downloads')):
        return JsonResponse({'status': 'error', 'message': 'Invalid file path'}, status=400)
    
    if not os.path.exists(file_path):
        return JsonResponse({'status': 'error', 'message': 'File not found'}, status=404)

    try:
        response = FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=filename
        )
        
        # Add headers for better download experience
        response['Content-Length'] = os.path.getsize(file_path)
        response['Accept-Ranges'] = 'bytes'
        
        return response
        
    except Exception as e:
        logger.error(f"File serving error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Failed to serve file'}, status=500)

@csrf_exempt
def get_supported_platforms(request):
    """API to get list of supported platforms"""
    platforms = {
        'video_platforms': [
            'YouTube', 'Instagram', 'TikTok', 'Facebook', 'Twitter/X',
            'Reddit', 'Twitch', 'Vimeo', 'Dailymotion', 'Streamable',
            'BitChute', 'Rumble', 'Odysee', 'PeerTube'
        ],
        'audio_platforms': [
            'SoundCloud', 'YouTube Music'
        ],
        'image_platforms': [
            'Imgur', 'Pinterest'
        ],
        'social_platforms': [
            'LinkedIn', 'Snapchat', 'Discord', 'Telegram'
        ]
    }
    
    return JsonResponse({
        'status': 'success',
        'platforms': platforms,
        'total_supported': sum(len(p) for p in platforms.values())
    })