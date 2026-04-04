"""
Browserless client for headless browser crawling
Uses Browserless.io or self-hosted Browserless/Chromium
"""

import asyncio
import aiohttp
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger("crawler.browserless")


class BrowserlessClient:
    """
    Client for Browserless headless browser service
    
    Supports:
    - Browserless.io cloud service
    - Self-hosted Browserless (Docker)
    - Any Chrome DevTools Protocol (CDP) compatible endpoint
    """
    
    def __init__(self, token: Optional[str] = None, 
                 base_url: str = "https://chrome.browserless.io",
                 timeout: int = 60):
        """
        Initialize Browserless client
        
        Args:
            token: Browserless API token (for browserless.io)
            base_url: Browserless endpoint URL
            timeout: Request timeout in seconds
        """
        self.token = token
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {
            'Content-Type': 'application/json',
        }
        if self.token:
            # Browserless.io uses token in query param, not header
            pass
        return headers
    
    def _build_url(self, path: str) -> str:
        """Build full URL with auth token if needed"""
        url = f"{self.base_url}{path}"
        if self.token:
            # Add token as query parameter
            separator = '&' if '?' in url else '?'
            url = f"{url}{separator}token={self.token}"
        return url
    
    async def scrape_page(self, url: str, 
                         wait_for: Optional[str] = None,
                         wait_timeout: int = 30000,
                         viewport: Optional[Dict[str, int]] = None,
                         reject_resource_types: Optional[List[str]] = None) -> Optional[str]:
        """
        Scrape a page using Browserless /content endpoint
        
        Args:
            url: URL to scrape
            wait_for: CSS selector to wait for (not used in this endpoint)
            wait_timeout: Wait timeout in milliseconds (converted to seconds for gotoOptions)
            viewport: Browser viewport {width, height}
            reject_resource_types: Resource types to block (image, stylesheet, font, etc.)
            
        Returns:
            HTML content or None if failed
        """
        endpoint = self._build_url("/content")
        
        # Build request body for /content endpoint
        # This endpoint returns the page content/HTML
        body = {
            "url": url,
        }
        
        # Add gotoOptions for wait timeout and waitUntil strategy
        goto_options = {
            "timeout": wait_timeout,
            "waitUntil": "networkidle0"  # Wait until network is idle (no connections for 500ms)
        }
        body["gotoOptions"] = goto_options
        
        if viewport:
            body["viewport"] = viewport
        
        try:
            logger.info(f"Scraping {url} via Browserless (timeout={wait_timeout}ms)")
            
            async with self.session.post(
                endpoint,
                headers=self._get_auth_headers(),
                json=body
            ) as response:
                
                if response.status == 200:
                    html = await response.text()
                    logger.info(f"Successfully scraped {url} ({len(html)} bytes)")
                    return html
                else:
                    text = await response.text()
                    logger.error(f"Browserless error {response.status}: {text[:200]}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
    
    async def execute_script(self, url: str, script: str,
                             wait_for: Optional[str] = None) -> Optional[Any]:
        """
        Execute custom JavaScript on a page using /function endpoint
        
        Args:
            url: URL to load
            script: JavaScript code to execute
            wait_for: Optional selector to wait for before executing
            
        Returns:
            Result of script execution
        """
        endpoint = self._build_url("/function")
        
        # Browserless /function endpoint requires specific format
        body = {
            "url": url,
            "code": script,  # Use "code" not "function"
        }
        
        # Add goto options for waiting
        goto_options = {
            "waitUntil": "networkidle0",
            "timeout": 45000
        }
        
        if wait_for:
            # Add page wait options if selector provided
            goto_options["waitForSelector"] = {
                "selector": wait_for,
                "timeout": 10000
            }
        
        body["gotoOptions"] = goto_options
        
        try:
            logger.info(f"Executing script on {url}")
            
            async with self.session.post(
                endpoint,
                headers=self._get_auth_headers(),
                json=body
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return result.get('result')
                else:
                    text = await response.text()
                    logger.error(f"Browserless function error {response.status}: {text[:200]}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error executing script on {url}: {e}")
            return None
    
    async def screenshot(self, url: str, 
                        viewport: Optional[Dict[str, int]] = None) -> Optional[bytes]:
        """
        Take screenshot of a page
        
        Args:
            url: URL to screenshot
            viewport: Viewport dimensions
            
        Returns:
            PNG image bytes or None
        """
        endpoint = self._build_url("/screenshot")
        
        body = {
            "url": url,
            "options": {
                "type": "png",
                "fullPage": True
            }
        }
        
        if viewport:
            body["viewport"] = viewport
        
        try:
            logger.info(f"Taking screenshot of {url}")
            
            async with self.session.post(
                endpoint,
                headers=self._get_auth_headers(),
                json=body
            ) as response:
                
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Screenshot error {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error taking screenshot of {url}: {e}")
            return None
    
    async def extract_data(self, url: str, 
                          selectors: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Extract structured data using CSS selectors
        
        Args:
            url: URL to scrape
            selectors: Dict of {field_name: css_selector}
            
        Returns:
            Extracted data or None
        """
        # Build JavaScript to extract data
        script_lines = ["const data = {};"]
        
        for field, selector in selectors.items():
            script_lines.append(f"""
                try {{
                    const el = document.querySelector('{selector}');
                    data['{field}'] = el ? el.textContent.trim() : null;
                }} catch(e) {{ data['{field}'] = null; }}
            """)
        
        script_lines.append("return data;")
        script = "\n".join(script_lines)
        
        result = await self.execute_script(url, script)
        return result
