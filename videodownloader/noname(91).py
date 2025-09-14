import os import re import random import time import logging from urllib.parse import urlparse from django.shortcuts import render from django.http import JsonResponse, FileResponse from django.views.decorators.csrf import csrf_exempt from django.conf import settings from django.core.cache import cache import yt_dlp

""" Unified, anti‑blocking, all‑in‑one video‑downloader backend ──────────────────────────────────────────────────────────── •   No artificial rate limits – sleeps are randomised only for anti‑bot evasion •   Audio‑only / video‑only / merged (video+audio) supported •   Returns the full list of available qualities & formats first so the UI can let the user choose •   Works for every platform that yt‑dlp supports; helper detects site → can be replaced by other libraries later """

logger = logging.getLogger(name)

#─ 1.  HELPER UTILITIES ───────────────────────────────────────────────────╮

def get_random_headers(): """Large rotating UA pool => helps bypass simplistic bot blocks""" user_agents = [ # Chrome / Firefox / Safari, recent versions 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36', ] base = { 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,/;q=0.8', 'Accept-Language': random.choice(['en-US,en;q=0.9', 'en-GB,en;q=0.9', 'en;q=0.8']), 'DNT': '1', 'Upgrade-Insecure-Requests': '1', 'Connection': 'keep-alive', } base['User-Agent'] = random.choice(user_agents) return base

def get_proxy(): """Return a random proxy from your pool (optional).""" proxies = [  # fill with your proxies or leave empty # 'http://user:pass@proxy1:port', # 'socks5://proxy2:port', ] return random.choice(proxies) if proxies else None

_platform_patterns = { 'youtube':   [r'youtube.com', r'youtu.be', r'youtube-nocookie.com'], 'instagram': [r'instagram.com', r'instagr.am'], 'tiktok':    [r'tiktok.com', r'vm.tiktok.com', r'vt.tiktok.com'], 'facebook':  [r'facebook.com', r'fb.watch', r'fb.me'], 'twitter':   [r'twitter.com', r'x.com', r't.co'], }

def detect_platform(url: str) -> str: url = url.lower().strip() for plat, pats in _platform_patterns.items(): if any(re.search(p, url) for p in pats): return plat return 'other'

def sanitize_filename(name: str) -> str: name = re.sub(r'[<>:"/\|?*]', '', name) name = re.sub(r'[\s-]+', '', name) return name[:200].strip('_')

def get_ydl_opts(download_type: str = 'both', fmt_id: str | None = None, proxy: str | None = None): """Central yt‑dlp options builder. download_type ∈ {'both', 'audio', 'video'} fmt_id        exact format to download (passed from UI). If None we use generic selectors so user gets best quality. """

# format selector logic --------------------------------------------------
if fmt_id:
    fmt_selector = fmt_id  # user chose a concrete format id
else:
    if download_type == 'audio':
        fmt_selector = 'bestaudio/best'
    elif download_type == 'video':
        fmt_selector = 'bestvideo/best'
    else:  # both (merged)
        fmt_selector = 'bestvideo+bestaudio/best'

opts: dict = {
    'quiet': True,
    'no_warnings': True,
    'ignoreerrors': True,
    'http_headers': get_random_headers(),
    # No hard throttling ⇒ unlimited speed; sleeps only to look human.
    'sleep_interval': random.uniform(0.5, 1.5),
    'max_sleep_interval': 3,
    'retries': 15,
    'fragment_retries': 15,
    'skip_unavailable_fragments': True,
    'concurrent_fragment_downloads': 4,
    'format': fmt_selector,
    'merge_output_format': 'mp4',
    'postprocessors': [
        {
            'key': 'FFmpegMerger',
            'preferredformat': 'mp4',
        }
    ],
    'outtmpl': os.path.join(settings.MEDIA_ROOT, 'downloads', '%(title)s.%(ext)s'),
    'geo_bypass': True,
}

if proxy:
    opts['proxy'] = proxy
return opts

#─ 2.  CORE BUSINESS LOGIC ────────────────────────────────────────────────╮

def extract_video_info(url: str) -> dict: """Return metadata + stripped‑down format list for UI selection.""" cache_key = f'info::{hash(url)}' cached = cache.get(cache_key) if cached: return cached

# attempt twice: direct + proxy
attempts = [None, get_proxy()]
for prx in attempts:
    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(download_type='both', proxy=prx)) as ydl:
            info = ydl.extract_info(url, download=False)
        break  # success
    except Exception as e:
        logger.warning(f"info extract failed via proxy={prx}: {e}")
else:
    return {'status': 'error', 'message': 'Failed to extract info'}

# Build a trimmed format list (ID + resolution + has_audio/video + size)
fmt_list = []
for f in info.get('formats', []):
    if not f.get('url'):
        continue
    fmt_list.append({
        'id': f['format_id'],
        'ext': f.get('ext', ''),
        'height': f.get('height') or 0,
        'acodec': f.get('acodec'),
        'vcodec': f.get('vcodec'),
        'filesize': f.get('filesize') or 0,
    })

result = {
    'status': 'success',
    'title': info.get('title'),
    'thumbnail': info.get('thumbnail'),
    'duration': info.get('duration'),
    'uploader': info.get('uploader'),
    'view_count': info.get('view_count'),
    'platform': detect_platform(url),
    'formats': sorted(fmt_list, key=lambda x: x['height'], reverse=True),
}

cache.set(cache_key, result, 3600)
return result

def perform_download(url: str, download_type: str, fmt_id: str | None = None): """Download & return metadata for serving.""" download_path = os.path.join(settings.MEDIA_ROOT, 'downloads') os.makedirs(download_path, exist_ok=True)

# simple cleanup of >24h files
now = time.time()
for f in os.listdir(download_path):
    fp = os.path.join(download_path, f)
    if os.path.isfile(fp) and now - os.path.getmtime(fp) > 86400:
        try:
            os.remove(fp)
        except Exception:
            pass

proxy = get_proxy()
opts = get_ydl_opts(download_type, fmt_id, proxy)

try:
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
except Exception as e:
    logger.error(f"download failed: {e}")
    return {'status': 'error', 'message': str(e)}

# find the physical file we just downloaded
expected = sanitize_filename(info.get('title', 'video'))
for f in os.listdir(download_path):
    if expected in sanitize_filename(f):
        size = os.path.getsize(os.path.join(download_path, f))
        return {
            'status': 'success',
            'filename': f,
            'filesize': size,
            'download_url': f"/media/downloads/{f}",
        }

return {'status': 'error', 'message': 'File not found after download'}

#─ 3.  DJANGO VIEWS ───────────────────────────────────────────────────────╮

def video_downloader(request): return render(request, 'videodownloader/index.html')

@csrf_exempt def api_info(request): if request.method != 'POST': return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405) url = request.POST.get('url', '').strip() if not url: return JsonResponse({'status': 'error', 'message': 'URL is required'}, status=400) try: parsed = urlparse(url) if not parsed.scheme or not parsed.netloc: raise ValueError except ValueError: return JsonResponse({'status': 'error', 'message': 'Invalid URL'}, status=400)

data = extract_video_info(url)
return JsonResponse(data)

@csrf_exempt def api_download(request): if request.method != 'POST': return JsonResponse({'status': 'error', 'message': 'POST required'}, status=405)

url = request.POST.get('url', '').strip()
download_type = request.POST.get('type', 'both')  # 'audio'|'video'|'both'
fmt_id = request.POST.get('format_id') or None

if not url:
    return JsonResponse({'status': 'error', 'message': 'URL is required'}, status=400)

data = perform_download(url, download_type, fmt_id)
return JsonResponse(data)

def serve_download(request, filename): # basic secure file serving filename = os.path.basename(filename) path = os.path.join(settings.MEDIA_ROOT, 'downloads', filename) if not os.path.isfile(path): return JsonResponse({'status': 'error', 'message': 'File not found'}, status=404) resp = FileResponse(open(path, 'rb'), as_attachment=True, filename=filename) resp['Content-Length'] = os.path.getsize(path) resp['Accept-Ranges'] = 'bytes' return resp

