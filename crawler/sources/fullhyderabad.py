"""
FullHyderabad crawler for Hyderabad events
"""

from typing import List, Dict, Any, Optional
import re
from bs4 import BeautifulSoup
import logging

from core.base_crawler import BaseCrawler
from core.http_client import RateLimitedClient
from utils.date_parser import DateParser
from utils.price_parser import PriceParser
from utils.venue_extractor import VenueExtractor

logger = logging.getLogger("crawler.sources.fullhyderabad")


class FullHyderabadCrawler(BaseCrawler):
    """Crawler for FullHyderabad.com events"""
    
    BASE_URL = "https://www.fullhyderabad.com/events"
    
    def __init__(self, data_store=None):
        config = {
            'rate_limit': 10,
            'timeout': 30,
            'retries': 3
        }
        super().__init__('fullhyderabad', config, data_store)
    
    async def fetch_events(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch events from FullHyderabad"""
        events = []
        
        async with RateLimitedClient(
            rate_limit=self.config['rate_limit'],
            timeout=self.config['timeout']
        ) as client:
            html = await client.get(self.BASE_URL)
            if not html:
                logger.error("Failed to fetch FullHyderabad page")
                return events
            
            soup = BeautifulSoup(html, 'lxml')
            
            # Look for event listings
            event_cards = soup.find_all('div', class_=re.compile('event|listing|item|post'))
            
            logger.info(f"Found {len(event_cards)} FullHyderabad event cards")
            
            for card in event_cards:
                try:
                    event_data = self._extract_event_from_card(card)
                    if event_data:
                        events.append(event_data)
                except Exception as e:
                    logger.warning(f"Error extracting event: {e}")
            
            # Try JSON-LD
            if not events:
                events = self._extract_from_metadata(soup)
        
        return events
    
    def _extract_event_from_card(self, card: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract event data from HTML card"""
        try:
            title_elem = card.find(['h2', 'h3', 'h4', 'h1']) or card.find(class_=re.compile('title|heading|entry-title'))
            title = title_elem.get_text(strip=True) if title_elem else None
            
            if not title or len(title) < 3:
                return None
            
            date_elem = card.find(class_=re.compile('date|time|event-date'))
            date_text = date_elem.get_text(strip=True) if date_elem else None
            
            venue_elem = card.find(class_=re.compile('venue|location|place|address'))
            venue_text = venue_elem.get_text(strip=True) if venue_elem else None
            
            price_elem = card.find(class_=re.compile('price|cost|ticket|fee'))
            price_text = price_elem.get_text(strip=True) if price_elem else None
            
            img_elem = card.find('img')
            image_url = img_elem.get('src') if img_elem else None
            
            link_elem = card.find('a', href=True)
            event_url = None
            if link_elem:
                href = link_elem['href']
                if href.startswith('http'):
                    event_url = href
                else:
                    event_url = f"https://www.fullhyderabad.com{href}"
            
            category_elem = card.find(class_=re.compile('category|tag'))
            category = category_elem.get_text(strip=True) if category_elem else None
            
            return {
                'title': title,
                'date_text': date_text,
                'venue_text': venue_text,
                'price_text': price_text,
                'image_url': image_url,
                'event_url': event_url or self.BASE_URL,
                'category': category,
                'source': 'fullhyderabad'
            }
            
        except Exception as e:
            logger.warning(f"Error parsing card: {e}")
            return None
    
    def _extract_from_metadata(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract events from JSON-LD"""
        events = []
        
        scripts = soup.find_all('script', type='application/ld+json')
        for script in scripts:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, list):
                    for item in data:
                        if item.get('@type') == 'Event':
                            events.append({
                                'title': item.get('name'),
                                'date_text': item.get('startDate'),
                                'venue_text': item.get('location', {}).get('name') if isinstance(item.get('location'), dict) else None,
                                'price_text': None,
                                'image_url': item.get('image'),
                                'event_url': item.get('url'),
                                'category': None,
                                'source': 'fullhyderabad'
                            })
            except Exception as e:
                logger.debug(f"Error parsing JSON-LD: {e}")
        
        return events
    
    def parse_event(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse raw event data into structured format"""
        if not raw_data.get('title'):
            return None
        
        start_date, end_date = DateParser.parse_date_range(raw_data.get('date_text', ''))
        price_min, price_max, is_free, currency = PriceParser.parse_price(raw_data.get('price_text', ''))
        venue_info = VenueExtractor.extract_venue(raw_data.get('venue_text', ''))
        
        return {
            'raw_title': raw_data.get('title'),
            'raw_description': None,
            'raw_date_text': raw_data.get('date_text'),
            'raw_time_text': None,
            'raw_location_text': raw_data.get('venue_text'),
            'raw_price_text': raw_data.get('price_text'),
            'raw_image_urls': [raw_data.get('image_url')] if raw_data.get('image_url') else [],
            'raw_category_text': raw_data.get('category'),
            'raw_organizer': None,
            'raw_contact_info': None,
            
            'parsed_start_date': start_date,
            'parsed_start_time': None,
            'parsed_end_date': end_date,
            'parsed_venue_name': venue_info.get('venue_name'),
            'parsed_address': venue_info.get('address'),
            'parsed_city': venue_info.get('city', 'Hyderabad'),
            'parsed_is_free': is_free,
            'parsed_price_min': price_min,
            'parsed_price_max': price_max,
            'parsed_currency': currency,
            
            'source_url': raw_data.get('event_url', self.BASE_URL),
        }
