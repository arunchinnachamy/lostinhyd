"""
BookMyShow crawler for Hyderabad events
"""

from typing import List, Dict, Any, Optional
import json
import re
from bs4 import BeautifulSoup
import logging

from core.base_crawler import BaseCrawler
from core.http_client import RateLimitedClient
from utils.date_parser import DateParser
from utils.price_parser import PriceParser
from utils.venue_extractor import VenueExtractor

logger = logging.getLogger("crawler.sources.bookmyshow")


class BookMyShowCrawler(BaseCrawler):
    """Crawler for BookMyShow Hyderabad events"""
    
    BASE_URL = "https://in.bookmyshow.com/explore/events-hyderabad"
    
    def __init__(self, data_store=None):
        config = {
            'rate_limit': 20,
            'timeout': 30,
            'retries': 3
        }
        super().__init__('bookmyshow', config, data_store)
    
    async def fetch_events(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch events from BookMyShow"""
        events = []
        
        async with RateLimitedClient(
            rate_limit=self.config['rate_limit'],
            timeout=self.config['timeout']
        ) as client:
            # Fetch main events page
            html = await client.get(self.BASE_URL)
            if not html:
                logger.error("Failed to fetch BookMyShow events page")
                return events
            
            # Parse events
            soup = BeautifulSoup(html, 'lxml')
            event_cards = soup.find_all('div', class_=re.compile('event-card|listing'))
            
            logger.info(f"Found {len(event_cards)} event cards on page")
            
            for card in event_cards:
                try:
                    event_data = self._extract_event_from_card(card)
                    if event_data:
                        events.append(event_data)
                except Exception as e:
                    logger.warning(f"Error extracting event from card: {e}")
            
            # Also try to fetch from API if available
            api_events = await self._fetch_from_api(client)
            events.extend(api_events)
        
        return events
    
    def _extract_event_from_card(self, card: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract event data from HTML card"""
        try:
            # Extract title
            title_elem = card.find('h3') or card.find('h4') or card.find(class_=re.compile('title|name'))
            title = title_elem.get_text(strip=True) if title_elem else None
            
            if not title:
                return None
            
            # Extract date
            date_elem = card.find(class_=re.compile('date|day|time'))
            date_text = date_elem.get_text(strip=True) if date_elem else None
            
            # Extract venue
            venue_elem = card.find(class_=re.compile('venue|location|place'))
            venue_text = venue_elem.get_text(strip=True) if venue_elem else None
            
            # Extract price
            price_elem = card.find(class_=re.compile('price|cost|₹'))
            price_text = price_elem.get_text(strip=True) if price_elem else None
            
            # Extract image
            img_elem = card.find('img')
            image_url = img_elem.get('src') or img_elem.get('data-src') if img_elem else None
            
            # Extract link
            link_elem = card.find('a', href=True)
            event_url = None
            if link_elem:
                href = link_elem['href']
                if href.startswith('http'):
                    event_url = href
                else:
                    event_url = f"https://in.bookmyshow.com{href}"
            
            # Extract category
            category_elem = card.find(class_=re.compile('category|genre|tag'))
            category = category_elem.get_text(strip=True) if category_elem else None
            
            return {
                'title': title,
                'date_text': date_text,
                'venue_text': venue_text,
                'price_text': price_text,
                'image_url': image_url,
                'event_url': event_url,
                'category': category,
                'source': 'bookmyshow'
            }
            
        except Exception as e:
            logger.warning(f"Error parsing event card: {e}")
            return None
    
    async def _fetch_from_api(self, client: RateLimitedClient) -> List[Dict[str, Any]]:
        """Try to fetch from BookMyShow API if available"""
        events = []
        
        # BookMyShow sometimes exposes data via script tags
        try:
            html = await client.get(self.BASE_URL)
            if html:
                # Look for JSON data in script tags
                pattern = r'<script[^>]*>.*?(\{[^<]*"events"[^<]*\}).*?</script>'
                matches = re.findall(pattern, html, re.DOTALL)
                
                for match in matches:
                    try:
                        data = json.loads(match)
                        if 'events' in data or 'props' in data:
                            # Parse structured data
                            pass
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            logger.debug(f"API fetch failed (expected): {e}")
        
        return events
    
    def parse_event(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse raw event data into structured format"""
        if not raw_data.get('title'):
            return None
        
        # Parse date
        start_date = None
        end_date = None
        if raw_data.get('date_text'):
            start_date, end_date = DateParser.parse_date_range(raw_data['date_text'])
        
        # Parse price
        price_min, price_max, is_free, currency = PriceParser.parse_price(
            raw_data.get('price_text', '')
        )
        
        # Extract venue info
        venue_info = VenueExtractor.extract_venue(raw_data.get('venue_text', ''))
        
        # Build event dictionary
        event = {
            # Raw data
            'raw_title': raw_data.get('title'),
            'raw_description': None,  # Would need to fetch detail page
            'raw_date_text': raw_data.get('date_text'),
            'raw_time_text': None,
            'raw_location_text': raw_data.get('venue_text'),
            'raw_price_text': raw_data.get('price_text'),
            'raw_image_urls': [raw_data.get('image_url')] if raw_data.get('image_url') else [],
            'raw_category_text': raw_data.get('category'),
            'raw_organizer': None,
            'raw_contact_info': None,
            
            # Parsed data
            'parsed_start_date': start_date,
            'parsed_start_time': None,
            'parsed_end_date': end_date,
            'parsed_end_time': None,
            'parsed_venue_name': venue_info.get('venue_name'),
            'parsed_address': venue_info.get('address'),
            'parsed_city': venue_info.get('city', 'Hyderabad'),
            'parsed_latitude': None,
            'parsed_longitude': None,
            'parsed_is_free': is_free,
            'parsed_price_min': price_min,
            'parsed_price_max': price_max,
            'parsed_currency': currency,
            'parsed_age_limit': None,
            
            # Source URL
            'source_url': raw_data.get('event_url', self.BASE_URL),
        }
        
        return event
