"""
Base crawler class and utilities for event aggregation.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import aiohttp
from bs4 import BeautifulSoup
import json

from utils.db import Event, EventStatus, Database


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result of a crawl operation"""
    events: List[Event]
    success: bool
    error_message: Optional[str] = None
    events_added: int = 0
    events_updated: int = 0
    events_skipped: int = 0


class BaseCrawler(ABC):
    """Abstract base class for event crawlers"""

    def __init__(self, db: Database, rate_limit_seconds: float = 1.0):
        """
        Initialize crawler.

        Args:
            db: Database instance
            rate_limit_seconds: Seconds to wait between requests
        """
        self.db = db
        self.rate_limit_seconds = rate_limit_seconds
        self._last_request_time: Optional[datetime] = None

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source name for this crawler"""
        pass

    @abstractmethod
    async def crawl(self, **kwargs) -> CrawlResult:
        """
        Main crawl method. Must be implemented by subclasses.

        Returns:
            CrawlResult with found events
        """
        pass

    async def load_config(self) -> Dict[str, Any]:
        """
        Load crawler configuration from the sources table.

        Queries by source_name and returns a dict with url, is_active,
        and crawl_frequency. Returns an empty dict if the source is not
        found in the database.
        """
        config = await self.db.get_source_config(self.source_name)
        return config

    async def _rate_limit(self):
        """Ensure we don't exceed rate limits"""
        if self._last_request_time:
            elapsed = (datetime.now() - self._last_request_time).total_seconds()
            if elapsed < self.rate_limit_seconds:
                await asyncio.sleep(self.rate_limit_seconds - elapsed)
        self._last_request_time = datetime.now()

    async def fetch_page(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """
        Fetch a web page with rate limiting.

        Args:
            url: URL to fetch
            headers: Optional custom headers

        Returns:
            HTML content as string
        """
        await self._rate_limit()

        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        if headers:
            default_headers.update(headers)

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=default_headers, timeout=30) as response:
                response.raise_for_status()
                return await response.text()

    async def save_events(self, events: List[Event]) -> CrawlResult:
        """
        Save events to database.

        Args:
            events: List of Event objects to save

        Returns:
            CrawlResult with counts
        """
        added_count = 0
        updated_count = 0
        skipped_count = 0

        for event in events:
            try:
                event.source = self.source_name
                event_id = await self.db.upsert_event(event)

                if event.id:
                    updated_count += 1
                    logger.info(f"Updated event: {event.title[:50]}...")
                else:
                    added_count += 1
                    logger.info(f"New event: {event.title[:50]}...")

            except Exception as e:
                skipped_count += 1
                logger.error(f"Failed to save event '{event.title[:50]}...': {e}")

        return CrawlResult(
            events=events,
            success=skipped_count == 0,
            events_added=added_count,
            events_updated=updated_count,
            events_skipped=skipped_count,
        )

    def parse_date(self, date_str: str, formats: List[str] = None) -> Optional[datetime]:
        """
        Try to parse a date string with multiple formats.

        Args:
            date_str: Date string to parse
            formats: List of strptime formats to try

        Returns:
            Parsed datetime or None
        """
        if not formats:
            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d %b %Y',
                '%d %B %Y',
                '%a, %d %b %Y',
            ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def extract_area_from_location(self, location: str) -> Optional[str]:
        """
        Try to extract a Hyderabad area name from a location string.

        Common areas: Banjara Hills, Jubilee Hills, Hitech City, Gachibowli,
        Madhapur, Kondapur, Old City, Charminar, Secunderabad
        """
        areas = [
            'Banjara Hills', 'Jubilee Hills', 'Hitech City', 'Gachibowli',
            'Madhapur', 'Kondapur', 'Old City', 'Charminar', 'Secunderabad',
            'Begumpet', 'Ameerpet', 'Panjagutta', 'Himayatnagar', 'Kukatpally',
            'Kompally', 'Shamirpet', 'LB Nagar', 'Dilsukhnagar', 'Uppal',
            'Hussain Sagar', 'Tank Bund', 'Somajiguda', 'Barkas', 'Shahran',
            'Moazzam Jahi Market', 'Abids', 'Basheerbagh'
        ]

        location_lower = location.lower()
        for area in areas:
            if area.lower() in location_lower:
                return area

        return None


class HTMLCrawler(BaseCrawler):
    """Crawler for HTML-based websites using BeautifulSoup"""

    async def crawl(self, **kwargs) -> CrawlResult:
        """
        Override this to implement HTML scraping logic.
        Call self.fetch_page() to get HTML, then parse with BeautifulSoup.
        """
        return await self._crawl_html(**kwargs)

    @abstractmethod
    async def _crawl_html(self, **kwargs) -> CrawlResult:
        """Implement HTML scraping here"""
        pass

    def soup(self, html: str) -> BeautifulSoup:
        """Create BeautifulSoup object from HTML"""
        return BeautifulSoup(html, 'lxml')


class APICrawler(BaseCrawler):
    """Crawler for API-based data sources"""

    async def crawl(self, **kwargs) -> CrawlResult:
        """
        Override this to implement API fetching logic.
        Call self.fetch_api() to get JSON data.
        """
        return await self._crawl_api(**kwargs)

    @abstractmethod
    async def _crawl_api(self, **kwargs) -> CrawlResult:
        """Implement API fetching here"""
        pass

    async def fetch_api(
        self,
        url: str,
        method: str = 'GET',
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fetch JSON data from an API.

        Args:
            url: API endpoint
            method: HTTP method (GET, POST, etc.)
            headers: Optional headers
            params: Query parameters
            json_data: JSON body for POST requests

        Returns:
            Parsed JSON response
        """
        await self._rate_limit()

        default_headers = {
            'Accept': 'application/json',
            'User-Agent': 'LostInHydBot/1.0',
        }
        if headers:
            default_headers.update(headers)

        async with aiohttp.ClientSession() as session:
            if method.upper() == 'GET':
                async with session.get(url, headers=default_headers, params=params, timeout=30) as response:
                    response.raise_for_status()
                    return await response.json()
            elif method.upper() == 'POST':
                async with session.post(url, headers=default_headers, json=json_data, timeout=30) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                raise ValueError(f"Unsupported method: {method}")


# Crawler registry
_crawlers: Dict[str, type] = {}


def register_crawler(name: str):
    """Decorator to register a crawler class"""
    def decorator(cls):
        _crawlers[name] = cls
        return cls
    return decorator


def get_crawler(name: str, db: Database) -> Optional[BaseCrawler]:
    """Get an instance of a registered crawler"""
    crawler_class = _crawlers.get(name)
    if crawler_class:
        return crawler_class(db)
    return None


def list_crawlers() -> List[str]:
    """List all registered crawler names"""
    return list(_crawlers.keys())
