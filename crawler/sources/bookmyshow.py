"""
BookMyShow crawler for Hyderabad events
Uses Browserless for JavaScript rendering
"""

from typing import List, Dict, Any, Optional
import json
import re
from bs4 import BeautifulSoup
import logging

from core.browser_based_crawler import BrowserBasedCrawler
from core.browserless_client import BrowserlessClient
from utils.date_parser import DateParser
from utils.price_parser import PriceParser
from utils.venue_extractor import VenueExtractor

logger = logging.getLogger("crawler.sources.bookmyshow")


class BookMyShowCrawler(BrowserBasedCrawler):
    """Crawler for BookMyShow Hyderabad events using Browserless"""
    
    BASE_URL = "https://in.bookmyshow.com/explore/events-hyderabad"
    
    def __init__(self, data_store=None, browserless_token=None, browserless_url=None):
        config = {
            'rate_limit': 10,  # Slower for browser automation
            'timeout': 60,
            'retries': 2,
            'browser_timeout': 90,
            'browserless_token': browserless_token,
            'browserless_url': browserless_url,
        }
        super().__init__('bookmyshow', config, data_store, 
                        browserless_token, browserless_url)
    
    async def fetch_events_with_browser(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch events from BookMyShow using Browserless"""
        events = []
        
        # Scrape the main events page
        logger.info(f"Fetching {self.BASE_URL} via Browserless")
        
        html = await self.scrape_page(
            self.BASE_URL,
            wait_for="[class*='event-card'], [class*='listing']",
            wait_timeout=45000  # 45 seconds
        )
        
        if not html:
            logger.error("Failed to fetch BookMyShow events page via Browserless")
            return events
        
        # Parse events from HTML
        events = self._parse_events_html(html)
        
        if events:
            logger.info(f"Found {len(events)} events on main page")
        else:
            logger.warning("No events found in HTML, trying fallback parsing")
            # Save HTML for debugging
            import os
            debug_file = os.path.expanduser("~/lostinhyd/crawler/debug_bookmyshow.html")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"Saved HTML to {debug_file} for debugging")
        
        return events
    
    def _parse_events_html(self, html: str) -> List[Dict[str, Any]]:
        """Parse events from HTML"""
        events = []
        soup = BeautifulSoup(html, 'lxml')
        
        # Look for event cards with various class patterns
        selectors = [
            'div[class*="event-card"]',
            'div[class*="listing"]',
            'a[href*="/events/"]',
            '[data-selector*="event"]'
        ]
        
        event_cards = []
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                event_cards = cards
                logger.info(f"Found {len(cards)} event cards with selector: {selector}")
                break
        
        for card in event_cards:
            try:
                event_data = self._extract_event_from_card(card)
                if event_data:
                    events.append(event_data)
            except Exception as e:
                logger.warning(f"Error extracting event from card: {e}")
        
        return events
    
    async def _extract_via_selectors(self) -> List[Dict[str, Any]]:
        """Extract data using CSS selectors via Browserless"""
        logger.info("Attempting selector-based extraction")
        
        selectors = {
            'titles': 'h3, h4, [class*="title"], [class*="name"]',
            'dates': '[class*="date"], [class*="day"]',
            'venues': '[class*="venue"], [class*="location"], [class*="place"]',
            'prices': '[class*="price"], [class*="cost"]',
            'links': 'a[href*="/events/"]'
        }
        
        data = await self.extract_with_selectors(self.BASE_URL, selectors)
        
        if not data:
            return []
        
        # Convert to event format
        events = []
        titles = data.get('titles', [])
        dates = data.get('dates', [])
        venues = data.get('venues', [])
        prices = data.get('prices', [])
        links = data.get('links', [])
        
        for i, title in enumerate(titles):
            if not title:
                continue
                
            event = {
                'title': title,
                'date_text': dates[i] if i < len(dates) else None,
                'venue_text': venues[i] if i < len(venues) else None,
                'price_text': prices[i] if i < len(prices) else None,
                'event_url': links[i] if i < len(links) else None,
                'source': 'bookmyshow'
            }
            events.append(event)
        
        return events
    
    def _extract_event_from_card(self, card: BeautifulSoup) -> Optional[Dict[str, Any]]:
        """Extract event data from HTML card"""
        try:
            # Extract title
            title_elem = card.find(['h3', 'h4', 'h5']) or card.find(class_=re.compile('title|name'))
            title = title_elem.get_text(strip=True) if title_elem else None
            
            if not title:
                # Try finding any text in the card
                title = card.get_text(strip=True)[:100]
            
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
            image_url = None
            if img_elem:
                image_url = img_elem.get('src') or img_elem.get('data-src')
            
            # Extract link
            link_elem = card.find('a', href=True)
            event_url = None
            if link_elem:
                href = link_elem['href']
                if href.startswith('http'):
                    event_url = href
                elif href.startswith('/'):
                    event_url = f"https://in.bookmyshow.com{href}"
            
            # Extract category
            category_elem = card.find(class_=re.compile('category|genre'))
            category = category_elem.get_text(strip=True) if category_elem else None
            
            if title and len(title) > 5:  # Minimum title length
                return {
                    'title': title,
                    'date_text': date_text,
                    'venue_text': venue_text,
                    'price_text': price_text,
                    'image_url': image_url,
                    'event_url': event_url or self.BASE_URL,
                    'category': category,
                    'source': 'bookmyshow'
                }
            
        except Exception as e:
            logger.warning(f"Error parsing event card: {e}")
        
        return None
    
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
            'raw_title': raw_data.get('title'),
            'raw_description': None,
            'raw_date_text': raw_data.get('date_text'),
            'raw_time_text': None,
            'raw_location_text': raw_data.get('venue_text'),
            'raw_price_text': raw_data.get('price_text'),
            'raw_image_urls': [raw_data.get('image_url')] if raw_data.get('image_url') else [],
            'raw_category_text': raw_data.get('category'),
            'raw_organizer': 'BookMyShow',
            'raw_contact_info': None,
            
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
            
            'source_url': raw_data.get('event_url', self.BASE_URL),
        }
        
        return event
