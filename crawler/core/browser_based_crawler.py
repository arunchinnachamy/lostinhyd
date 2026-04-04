"""
Browser-based base crawler using Browserless
For sites that require JavaScript rendering (BookMyShow, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
import hashlib

from core.base_crawler import BaseCrawler
from core.browserless_client import BrowserlessClient

logger = logging.getLogger("crawler.browser_based")


class BrowserBasedCrawler(BaseCrawler, ABC):
    """
    Abstract base class for crawlers that need a real browser
    Uses Browserless for headless Chrome automation
    """
    
    def __init__(self, source_name: str, config: Dict[str, Any], data_store=None,
                 browserless_token: Optional[str] = None,
                 browserless_url: Optional[str] = None):
        super().__init__(source_name, config, data_store)
        
        # Browserless configuration
        self.browserless_token = browserless_token or config.get('browserless_token')
        self.browserless_url = browserless_url or config.get(
            'browserless_url', 
            "https://chrome.browserless.io"
        )
        
        # Browserless client (initialized in crawl)
        self.browser: Optional[BrowserlessClient] = None
        
    async def crawl(self, batch_id: str, **kwargs) -> Dict[str, int]:
        """Main crawl method with Browserless"""
        
        if not self.browserless_token:
            logger.warning(f"No Browserless token provided for {self.source_name}")
            logger.info("Attempting fallback to HTTP crawling...")
            # Fallback to regular HTTP crawling
            return await super().crawl(batch_id, **kwargs)
        
        # Initialize Browserless client
        async with BrowserlessClient(
            token=self.browserless_token,
            base_url=self.browserless_url,
            timeout=self.config.get('browser_timeout', 60)
        ) as browser:
            self.browser = browser
            
            logger.info(f"Starting browser-based crawl for {self.source_name}", 
                       batch_id=batch_id)
            self.stats = {k: 0 for k in self.stats}
            
            try:
                # Fetch raw events using browser
                raw_events = await self.fetch_events_with_browser(**kwargs)
                logger.info(f"Fetched {len(raw_events)} raw events via browser")
                
                for raw in raw_events:
                    try:
                        parsed = self.parse_event(raw)
                        if not parsed:
                            self.stats['skipped'] += 1
                            continue
                        
                        parsed['source_name'] = self.source_name
                        parsed['crawl_batch_id'] = batch_id
                        parsed['source_id'] = self.generate_source_id(raw)
                        
                        if self.data_store:
                            event_id = await self.data_store.store_raw_event(parsed)
                            if event_id:
                                self.stats['added'] += 1
                            else:
                                self.stats['updated'] += 1
                        
                        self.stats['found'] += 1
                        
                    except Exception as e:
                        logger.error(f"Error parsing event: {e} [raw={raw}]")
                        self.stats['errors'] += 1
                
                logger.info(f"Crawl completed: {self.stats}")
                return self.stats
                
            except Exception as e:
                logger.error(f"Browser crawl failed: {e}")
                raise
            finally:
                self.browser = None
    
    @abstractmethod
    async def fetch_events_with_browser(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Fetch events using Browserless
        Must be implemented by subclass
        """
        pass
    
    async def scrape_page(self, url: str, 
                         wait_for: Optional[str] = None,
                         wait_timeout: int = 30000) -> Optional[str]:
        """
        Helper method to scrape a page via Browserless
        
        Args:
            url: URL to scrape
            wait_for: CSS selector to wait for
            wait_timeout: Wait timeout in ms
            
        Returns:
            HTML content or None
        """
        if not self.browser:
            logger.error("Browser not initialized")
            return None
        
        return await self.browser.scrape_page(
            url, 
            wait_for=wait_for,
            wait_timeout=wait_timeout,
            reject_resource_types=["image", "stylesheet", "font", "media"]
        )
    
    async def extract_with_selectors(self, url: str,
                                    selectors: Dict[str, str],
                                    wait_for: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Extract data using CSS selectors via Browserless
        
        Args:
            url: URL to load
            selectors: Dict of {field_name: css_selector}
            wait_for: Optional selector to wait for
            
        Returns:
            Extracted data dict or None
        """
        if not self.browser:
            logger.error("Browser not initialized")
            return None
        
        # Build extraction script
        script_lines = ["const data = {};"]
        
        for field, selector in selectors.items():
            # Handle multiple elements
            script_lines.append(f"""
                try {{
                    const els = document.querySelectorAll('{selector}');
                    if (els.length === 1) {{
                        data['{field}'] = els[0].textContent.trim();
                    }} else if (els.length > 1) {{
                        data['{field}'] = Array.from(els).map(el => el.textContent.trim());
                    }} else {{
                        data['{field}'] = null;
                    }}
                }} catch(e) {{ 
                    data['{field}'] = null; 
                }}
            """)
        
        script_lines.append("return data;")
        script = "\n".join(script_lines)
        
        return await self.browser.execute_script(url, script, wait_for)
