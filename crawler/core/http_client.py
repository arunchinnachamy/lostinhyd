"""
Enhanced HTTP client with better browser emulation
"""

import asyncio
import aiohttp
import random
import time
from typing import Optional, Dict, Any
import logging
import brotli

logger = logging.getLogger("crawler.http_client")


class RateLimitedClient:
    """HTTP client with rate limiting, retry logic, and browser emulation"""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]
    
    REFERERS = [
        'https://www.google.com/',
        'https://www.bing.com/',
        'https://search.yahoo.com/',
        'https://www.facebook.com/',
        'https://twitter.com/',
    ]
    
    def __init__(self, rate_limit: int = 10, timeout: int = 30, retries: int = 3):
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.retries = retries
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(rate_limit)
        self._last_request_time = 0
        self.logger = logging.getLogger("crawler.http_client")
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        # Create session without automatic decompression
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            auto_decompress=False
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _apply_rate_limit(self):
        min_interval = 60.0 / self.rate_limit
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            delay = min_interval - elapsed + random.uniform(0.5, 2.0)
            await asyncio.sleep(delay)
        self._last_request_time = time.time()
    
    def _get_headers(self, url: str) -> Dict[str, str]:
        """Generate realistic browser headers"""
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': random.choice(self.REFERERS),
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    
    async def _decode_content(self, response: aiohttp.ClientResponse, data: bytes) -> str:
        """Decode content based on encoding"""
        encoding = response.headers.get('Content-Encoding', '').lower()
        
        try:
            if encoding == 'br':
                data = brotli.decompress(data)
            elif encoding == 'gzip':
                import gzip
                data = gzip.decompress(data)
            elif encoding == 'deflate':
                import zlib
                data = zlib.decompress(data)
        except Exception as e:
            self.logger.warning(f"Failed to decompress {encoding}: {e}")
        
        # Try different encodings
        for charset in ['utf-8', 'iso-8859-1', 'windows-1252']:
            try:
                return data.decode(charset)
            except UnicodeDecodeError:
                continue
        
        return data.decode('utf-8', errors='ignore')
    
    async def get(self, url: str, **kwargs) -> Optional[str]:
        async with self._semaphore:
            await self._apply_rate_limit()
            
            for attempt in range(self.retries):
                try:
                    headers = self._get_headers(url)
                    headers.update(kwargs.get('headers', {}))
                    
                    async with self.session.get(
                        url, 
                        headers=headers,
                        allow_redirects=True,
                        **{k: v for k, v in kwargs.items() if k != 'headers'}
                    ) as response:
                        
                        # Read raw bytes
                        data = await response.read()
                        
                        if response.status == 200:
                            text = await self._decode_content(response, data)
                            self.logger.debug(f"Fetched {url} ({len(text)} bytes)")
                            return text
                        
                        elif response.status == 429:
                            wait_time = int(response.headers.get('Retry-After', 60))
                            self.logger.warning(f"Rate limited by {url}, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                        
                        elif response.status in [403, 406]:
                            self.logger.warning(f"Blocked ({response.status}) by {url}")
                            # Try once more with different headers
                            if attempt < self.retries - 1:
                                await asyncio.sleep(5)
                                continue
                            return None
                        
                        else:
                            self.logger.warning(f"HTTP {response.status} for {url}")
                            if response.status >= 500:
                                await asyncio.sleep(2 ** attempt)
                            else:
                                return None
                                
                except asyncio.TimeoutError:
                    self.logger.warning(f"Timeout for {url} (attempt {attempt + 1})")
                    await asyncio.sleep(2 ** attempt)
                    
                except Exception as e:
                    self.logger.error(f"Error fetching {url}: {e}")
                    if attempt < self.retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        return None
            
            return None
