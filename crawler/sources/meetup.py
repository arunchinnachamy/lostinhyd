"""
Meetup crawler for Hyderabad events
Uses Meetup API (requires API key)
"""

from typing import List, Dict, Any, Optional
import logging

from core.base_crawler import BaseCrawler
from core.http_client import RateLimitedClient
from utils.date_parser import DateParser
from utils.price_parser import PriceParser
from utils.venue_extractor import VenueExtractor

logger = logging.getLogger("crawler.sources.meetup")


class MeetupCrawler(BaseCrawler):
    """Crawler for Meetup.com Hyderabad events"""
    
    # Meetup GraphQL API endpoint
    API_URL = "https://api.meetup.com/gql"
    # Alternative: Find events by location
    EVENTS_URL = "https://www.meetup.com/find/?location=in--Hyderabad"
    
    def __init__(self, data_store=None, api_key=None):
        config = {
            'rate_limit': 30,  # Meetup API is more generous
            'timeout': 30,
            'retries': 3
        }
        super().__init__('meetup', config, data_store)
        self.api_key = api_key
    
    async def fetch_events(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch events from Meetup"""
        events = []
        
        async with RateLimitedClient(
            rate_limit=self.config['rate_limit'],
            timeout=self.config['timeout']
        ) as client:
            # Try web scraping first (simpler)
            events = await self._scrape_web(client)
            
            # If we have API key, use API instead
            if self.api_key and not events:
                events = await self._fetch_api(client)
        
        return events
    
    async def _scrape_web(self, client: RateLimitedClient) -> List[Dict[str, Any]]:
        """Scrape events from Meetup web interface"""
        events = []
        
        try:
            html = await client.get(self.EVENTS_URL)
            if not html:
                logger.error("Failed to fetch Meetup page")
                return events
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'lxml')
            
            # Look for event cards
            event_cards = soup.find_all('div', {'data-testid': 'event-card'})
            if not event_cards:
                event_cards = soup.find_all('div', class_=re.compile('event|card'))
            
            logger.info(f"Found {len(event_cards)} Meetup event cards")
            
            for card in event_cards:
                try:
                    # Extract data
                    title_elem = card.find(['h3', 'h4']) or card.find(class_=re.compile('title'))
                    title = title_elem.get_text(strip=True) if title_elem else None
                    
                    if not title:
                        continue
                    
                    # Meetup usually has structured data
                    time_elem = card.find('time')
                    date_text = time_elem.get_text(strip=True) if time_elem else None
                    
                    venue_elem = card.find(class_=re.compile('venue|location'))
                    venue_text = venue_elem.get_text(strip=True) if venue_elem else None
                    
                    group_elem = card.find(class_=re.compile('group|organizer'))
                    organizer = group_elem.get_text(strip=True) if group_elem else None
                    
                    link_elem = card.find('a', href=True)
                    event_url = link_elem['href'] if link_elem else None
                    if event_url and not event_url.startswith('http'):
                        event_url = f"https://www.meetup.com{event_url}"
                    
                    events.append({
                        'title': title,
                        'date_text': date_text,
                        'venue_text': venue_text,
                        'price_text': 'Free',  # Most Meetup events are free
                        'image_url': None,
                        'event_url': event_url or self.EVENTS_URL,
                        'category': None,
                        'organizer': organizer,
                        'source': 'meetup'
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing Meetup card: {e}")
            
        except Exception as e:
            logger.error(f"Error scraping Meetup web: {e}")
        
        return events
    
    async def _fetch_api(self, client: RateLimitedClient) -> List[Dict[str, Any]]:
        """Fetch events using Meetup API"""
        events = []
        logger.info("Using Meetup API")
        
        # GraphQL query to find events near Hyderabad
        query = """
        query FindEvents($lat: Float!, $lon: Float!, $radius: Int!) {
            findEventSummaries(
                filter: {lat: $lat, lon: $lon, source: EVENTS, radius: $radius}
                first: 20
            ) {
                edges {
                    node {
                        id
                        title
                        eventUrl
                        dateTime
                        venue {
                            name
                            address
                            city
                        }
                        group {
                            name
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            "lat": 17.4065,  # Hyderabad latitude
            "lon": 78.4772,  # Hyderabad longitude
            "radius": 10     # 10km radius
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}' if self.api_key else ''
        }
        
        try:
            import json
            response = await client.post(
                self.API_URL,
                headers=headers,
                json={'query': query, 'variables': variables}
            )
            
            if response:
                data = json.loads(response)
                edges = data.get('data', {}).get('findEventSummaries', {}).get('edges', [])
                
                for edge in edges:
                    node = edge.get('node', {})
                    venue = node.get('venue', {})
                    
                    events.append({
                        'title': node.get('title'),
                        'date_text': node.get('dateTime'),
                        'venue_text': venue.get('name'),
                        'price_text': 'Free',
                        'image_url': None,
                        'event_url': node.get('eventUrl'),
                        'category': None,
                        'organizer': node.get('group', {}).get('name'),
                        'source': 'meetup'
                    })
                
                logger.info(f"Found {len(events)} events via Meetup API")
        
        except Exception as e:
            logger.error(f"Error fetching Meetup API: {e}")
        
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
            'raw_image_urls': [],
            'raw_category_text': raw_data.get('category'),
            'raw_organizer': raw_data.get('organizer'),
            'raw_contact_info': None,
            
            'parsed_start_date': start_date,
            'parsed_start_time': None,
            'parsed_end_date': end_date,
            'parsed_venue_name': venue_info.get('venue_name'),
            'parsed_address': venue_info.get('address'),
            'parsed_city': venue_info.get('city', 'Hyderabad'),
            'parsed_is_free': is_free or True,  # Most Meetups are free
            'parsed_price_min': price_min,
            'parsed_price_max': price_max,
            'parsed_currency': currency,
            
            'source_url': raw_data.get('event_url', self.EVENTS_URL),
        }
