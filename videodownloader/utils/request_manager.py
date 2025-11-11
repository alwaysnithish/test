from django.core.cache import cache
from django.http import JsonResponse
import time

def check_rate_limit(request, limit=5, period=60):
    """
    Rate limiting middleware
    - limit: requests per period
    - period: in seconds
    """
    ip = request.META.get('REMOTE_ADDR', '')
    if not ip:
        return None

    cache_key = f"rate_limit_{ip}"
    requests = cache.get(cache_key, [])

    # Remove old requests
    now = time.time()
    requests = [t for t in requests if now - t < period]

    if len(requests) >= limit:
        return JsonResponse(
            {
                'status': 'error',
                'message': f'Rate limit exceeded. Try again in {period} seconds.'
            },
            status=429
        )

    requests.append(now)
    cache.set(cache_key, requests, period)
    return None