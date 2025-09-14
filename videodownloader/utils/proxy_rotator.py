import requests
from bs4 import BeautifulSoup
import random
import time
from django.core.cache import cache

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.last_refresh = 0
        self.refresh_interval = 1800  # 30 minutes

    def refresh_proxies(self):
        """Scrape fresh proxies from free sources"""
        try:
            sources = [
                'https://www.sslproxies.org/',
                'https://free-proxy-list.net/'
            ]
            
            new_proxies = []
            for url in sources:
                try:
                    response = requests.get(url, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    table = soup.find('table', {'id': 'proxylisttable'})
                    
                    for row in table.tbody.find_all('tr'):
                        cols = row.find_all('td')
                        if len(cols) >= 2:
                            ip = cols[0].text.strip()
                            port = cols[1].text.strip()
                            new_proxies.append(f"http://{ip}:{port}")
                except Exception:
                    continue

            if new_proxies:
                self.proxies = list(set(new_proxies))
                self.last_refresh = time.time()
                cache.set('available_proxies', self.proxies, timeout=1800)

        except Exception as e:
            print(f"Proxy refresh failed: {str(e)}")

    def get_valid_proxy(self, max_attempts=3):
        """Get a working proxy with health checks"""
        proxies = cache.get('available_proxies', [])
        
        if not proxies or time.time() - self.last_refresh > self.refresh_interval:
            self.refresh_proxies()
            proxies = self.proxies

        for _ in range(max_attempts):
            if not proxies:
                return None
                
            proxy = random.choice(proxies)
            if self._is_proxy_working(prox