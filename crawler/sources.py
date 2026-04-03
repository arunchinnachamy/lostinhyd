"""
Example crawler implementations for Hyderabad event sources.
These are templates - you'll need to adapt selectors based on actual site structures.
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime, timedelta

from crawler.base import HTMLCrawler, APICrawler, register_crawler, CrawlResult
from utils.db import Event, EventStatus


logger = logging.getLogger(__name__)


@register_crawler("insider")
class InsiderCrawler(HTMLCrawler):
    """Crawler for Insider.in Hyderabad events"""
    
    @property
    def source_name(self) -> str:
        return "insider"
    
    async def _crawl_html(self, **kwargs) -> CrawlResult:
        """Crawl Insider.in for Hyderabad events"""
        events = []
        
        try:
            # Fetch the Hyderabad events page
            # Note: This URL and selectors need to be verified against actual site
            url = "https://insider.in/hyderabad"
            html = await self.fetch_page(url)
            soup = self.soup(html)
            
            # Find event cards - adjust selectors based on actual HTML structure
            event_cards = soup.find_all('div', class_='event-card')  # Example class
            
            for card in event_cards:
                try:
                    # Extract event details - adjust selectors
                    title_elem = card.find('h3', class_='event-title')
                    title = title_elem.text.strip() if title_elem else None
                    
                    if not title:
                        continue
                    
                    link_elem = card.find('a', href=True)
                    link = f"https://insider.in{link_elem['href']}" if link_elem else None
                    
                    date_elem = card.find('span', class_='event-date')
                    date_str = date_elem.text.strip() if date_elem else None
                    event_date = self.parse_date(date_str) if date_str else None
                    
                    venue_elem = card.find('span', class_='venue-name')
                    venue = venue_elem.text.strip() if venue_elem else None
                    
                    # Try to extract area from venue
                    area = self.extract_area_from_location(venue) if venue else None
                    
                    # Get description if available
                    desc_elem = card.find('p', class_='description')
                    description = desc_elem.text.strip() if desc_elem else None
                    
                    event = Event(
                        title=title,
                        description=description,
                        event_date=event_date,
                        venue=venue,
                        area=area,
                        link=link,
                        category="events",  # Infer from title/description
                        status=EventStatus.DRAFT,
                    )
                    events.append(event)
                    
                except Exception as e:
                    logger.error(f"Error parsing event card: {e}")
                    continue
            
            # Save to database
            return await self.save_events(events)
            
        except Exception as e:
            logger.error(f"Error crawling Insider.in: {e}")
            return CrawlResult(
                events=events,
                success=False,
                error_message=str(e)
            )


@register_crawler("allevents")
class AllEventsCrawler(HTMLCrawler):
    """Crawler for Allevents.in Hyderabad"""
    
    @property
    def source_name(self) -> str:
        return "allevents"
    
    async def _crawl_html(self, **kwargs) -> CrawlResult:
        """Crawl Allevents.in for Hyderabad events"""
        events = []
        
        try:
            # Allevents has a Hyderabad specific page
            url = "https://allevents.in/hyderabad/all"
            html = await self.fetch_page(url)
            soup = self.soup(html)
            
            # Adjust selectors based on actual site structure
            event_items = soup.find_all('div', class_='event-item')
            
            for item in event_items:
                try:
                    title_elem = item.find('h3')
                    title = title_elem.text.strip() if title_elem else None
                    
                    if not title:
                        continue
                    
                    link_elem = item.find('a', href=True)
                    link = link_elem['href'] if link_elem else None
                    
                    # Allevents often has structured date info
                    date_elem = item.find('time')
                    if date_elem:
                        datetime_attr = date_elem.get('datetime')
                        event_date = self.parse_date(datetime_attr) if datetime_attr else None
                    else:
                        event_date = None
                    
                    location_elem = item.find('span', class_='venue')
                    location = location_elem.text.strip() if location_elem else None
                    area = self.extract_area_from_location(location) if location else None
                    
                    image_elem = item.find('img')
                    image_url = image_elem.get('src') if image_elem else None
                    
                    event = Event(
                        title=title,
                        event_date=event_date,
                        location=location,
                        area=area,
                        link=link,
                        image_url=image_url,
                        status=EventStatus.DRAFT,
                    )
                    events.append(event)
                    
                except Exception as e:
                    logger.error(f"Error parsing event: {e}")
                    continue
            
            return await self.save_events(events)
            
        except Exception as e:
            logger.error(f"Error crawling Allevents: {e}")
            return CrawlResult(
                events=events,
                success=False,
                error_message=str(e)
            )


@register_crawler("bookmyshow")
class BookMyShowCrawler(HTMLCrawler):
    """Crawler for BookMyShow Hyderabad events"""
    
    @property
    def source_name(self) -> str:
        return "bookmyshow"
    
    async def _crawl_html(self, **kwargs) -> CrawlResult:
        """
        Crawl BookMyShow for Hyderabad events.
        Note: BMS may require handling of dynamic content/JavaScript rendering.
        """
        events = []
        
        try:
            # BMS explore page for Hyderabad
            url = "https://in.bookmyshow.com/explore/home/hyderabad"
            html = await self.fetch_page(url)
            soup = self.soup(html)
            
            # BMS often loads content dynamically
            # You might need to use Playwright or Selenium for this
            # This is a basic example assuming static content
            
            event_cards = soup.find_all('div', class_='card-container')
            
            for card in event_cards:
                try:
                    title_elem = card.find('h4')
                    title = title_elem.text.strip() if title_elem else None
                    
                    if not title:
                        continue
                    
                    # BMS has specific event types - movies, events, sports
                    # Filter for non-movie events
                    event_type_elem = card.find('span', class_='event-type')
                    event_type = event_type_elem.text.strip() if event_type_elem else "events"
                    
                    if event_type.lower() in ['movie', 'movies', 'film']:
                        continue  # Skip movies
                    
                    link_elem = card.find('a', href=True)
                    link = f"https://in.bookmyshow.com{link_elem['href']}" if link_elem else None
                    
                    venue_elem = card.find('span', class_='venue')
                    venue = venue_elem.text.strip() if venue_elem else None
                    area = self.extract_area_from_location(venue) if venue else None
                    
                    event = Event(
                        title=title,
                        venue=venue,
                        area=area,
                        link=link,
                        category=event_type,
                        status=EventStatus.DRAFT,
                    )
                    events.append(event)
                    
                except Exception as e:
                    logger.error(f"Error parsing BMS card: {e}")
                    continue
            
            return await self.save_events(events)
            
        except Exception as e:
            logger.error(f"Error crawling BookMyShow: {e}")
            return CrawlResult(
                events=events,
                success=False,
                error_message=str(e)
            )


@register_crawler("meetup")
class MeetupCrawler(APICrawler):
    """
    Crawler for Meetup.com events in Hyderabad.
    Requires Meetup API key.
    """
    
    @property
    def source_name(self) -> str:
        return "meetup"
    
    async def _crawl_api(self, **kwargs) -> CrawlResult:
        """Fetch Meetup events via API"""
        events = []
        api_key = kwargs.get('api_key')
        
        if not api_key:
            return CrawlResult(
                events=[],
                success=False,
                error_message="Meetup API key required"
            )
        
        try:
            # Meetup GraphQL API
            url = "https://api.meetup.com/gql"
            
            # GraphQL query for Hyderabad events
            query = """
            query($lat: Float!, $lon: Float!, $radius: Int!) {
                findEventTypeEvents(
                    filter: {lat: $lat, lon: $lon, radius: $radius}
                    sort: {sortField: START_TIME, sortOrder: ASC}
                ) {
                    edges {
                        node {
                            title
                            description
                            eventUrl
                            venue {
                                name
                                address
                                city
                            }
                            dateTime
                            endTime
                            imageUrl
                            fee {
                                amount
                                currency
                            }
                        }
                    }
                }
            }
            """
            
            # Hyderabad coordinates
            variables = {
                "lat": 17.4065,
                "lon": 78.4772,
                "radius": 25  # km
            }
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            data = await self.fetch_api(
                url, 
                method='POST',
                headers=headers,
                json_data={'query': query, 'variables': variables}
            )
            
            # Parse events
            edges = data.get('data', {}).get('findEventTypeEvents', {}).get('edges', [])
            
            for edge in edges:
                node = edge.get('node', {})
                
                try:
                    # Parse date
                    date_str = node.get('dateTime', '')
                    event_date = self.parse_date(date_str.replace('Z', '+00:00')) if date_str else None
                    
                    end_str = node.get('endTime', '')
                    end_date = self.parse_date(end_str.replace('Z', '+00:00')) if end_str else None
                    
                    venue_data = node.get('venue', {})
                    venue_name = venue_data.get('name', '')
                    venue_address = venue_data.get('address', '')
                    venue_city = venue_data.get('city', '')
                    
                    location_parts = [p for p in [venue_name, venue_address, venue_city] if p]
                    location = ', '.join(location_parts)
                    area = self.extract_area_from_location(location)
                    
                    # Price info
                    fee = node.get('fee', {})
                    price = None
                    if fee and fee.get('amount'):
                        price = f"{fee['amount']} {fee.get('currency', 'INR')}"
                    
                    event = Event(
                        title=node.get('title', 'Untitled'),
                        description=node.get('description', '')[:500],
                        event_date=event_date,
                        end_date=end_date,
                        location=location,
                        area=area,
                        venue=venue_name,
                        price=price,
                        link=node.get('eventUrl'),
                        image_url=node.get('imageUrl'),
                        category="meetup",
                        status=EventStatus.DRAFT,
                    )
                    events.append(event)
                    
                except Exception as e:
                    logger.error(f"Error parsing Meetup event: {e}")
                    continue
            
            return await self.save_events(events)
            
        except Exception as e:
            logger.error(f"Error crawling Meetup: {e}")
            return CrawlResult(
                events=events,
                success=False,
                error_message=str(e)
            )


# Example manual event entry
def create_manual_event(
    title: str,
    description: str,
    event_date: datetime,
    location: str,
    db: Database
) -> Event:
    """Helper to create a manually entered event"""
    event = Event(
        title=title,
        description=description,
        event_date=event_date,
        location=location,
        area=None,  # Will be extracted
        source="venue_manual",
        source_id=f"manual-{datetime.now().timestamp()}",
        status=EventStatus.DRAFT,
    )
    return event
