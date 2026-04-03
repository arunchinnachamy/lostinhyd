"""
Rate-limited HTTP client for crawling
"""

import asyncio
import aiohttp
import random
import time
from typing import Optional, Dict, Any
import logging


class RateLimitedClient:
    """HTTP client with rate limiting, retry logic, and user-agent rotation"""
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    ]
    
    def __init__(self, rate_limit: int = 10, timeout: int = 30, retries: int = 3):
        """
        Args:
            rate_limit: Maximum requests per minute
            timeout: Request timeout in seconds
            retries: Number of retry attempts
        """
        self.rate_limit = rate_limit
        self.timeout = timeout
        self.retries = retries
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(rate_limit)
        self._last_request_time = 0
        self.logger = logging.getLogger("crawler.http_client")
        
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        headers = {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
        }
        
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _apply_rate_limit(self):
        """Apply rate limiting between requests"""
        min_interval = 60.0 / self.rate_limit
        elapsed = time.time() - self._last_request_time
        if elapsed < min_interval:
            delay = min_interval - elapsed + random.uniform(0.5, 2.0)
            self.logger.debug(f"Rate limiting: sleeping {delay:.2f}s")
            await asyncio.sleep(delay)
        self._last_request_time = time.time()
    
    async def get(self, url: str, **kwargs) -> Optional[str]:
        """
        Perform GET request with rate limiting and retries
        
        Args:
            url: URL to fetch
            **kwargs: Additional aiohttp request kwargs
            
        Returns:
            Response text or None if failed
        """
        async with self._semaphore:
            await self._apply_rate_limit()
            
            for attempt in range(self.retries):
                try:
                    self.logger.debug(f"Fetching {url} (attempt {attempt + 1}/{self.retries})")
                    
                    async with self.session.get(url, **kwargs) as response:
                        if response.status == 200:
                            text = await response.text()
                            self.logger.debug(f"Successfully fetched {url} ({len(text)} bytes)")
                            return text
                        elif response.status == 429:  # Rate limited
                            wait_time = int(response.headers.get('Retry-After', 60))
                            self.logger.warning(f"Rate limited by {url}, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                        else:
                            self.logger.warning(f"HTTP {response.status} for {url}")
                            if response.status >= 500:  # Server error, retry
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
    
    async def post(self, url: str, data: Dict[str, Any] = None, json_data: Dict[str, Any] = None, **kwargs) -> Optional[str]:
        """
        Perform POST request with rate limiting
        
        Args:
            url: URL to post to
            data: Form data
            json_data: JSON data
            **kwargs: Additional aiohttp request kwargs
            
        Returns:
            Response text or None if failed
        """
        async with self._semaphore:
            await self._apply_rate_limit()
            
            try:
                async with self.session.post(url, data=data, json=json_data, **kwargs) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        self.logger.warning(f"HTTP {response.status} for POST {url}")
                        return None
            except Exception as e:
                self.logger.error(f"Error POSTing to {url}: {e}")
                return None
