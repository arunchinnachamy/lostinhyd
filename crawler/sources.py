"""
Crawler implementations for Hyderabad event sources.

- AllEvents.in: HTML scraping (server-rendered event cards)
- Meetup.com: Scrape __NEXT_DATA__ JSON from the SSR page
- Insider.in: Client-rendered SPA — requires headless browser (stubbed)
- BookMyShow: Client-rendered SPA — requires headless browser (stubbed)
"""

import asyncio
import logging
import json
import re
from typing import List, Optional
from datetime import datetime, timedelta

from crawler.base import HTMLCrawler, APICrawler, register_crawler, CrawlResult
from utils.db import Event, EventStatus


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# AllEvents.in — server-rendered HTML
# ---------------------------------------------------------------------------

@register_crawler("allevents")
class AllEventsCrawler(HTMLCrawler):
    """Crawler for allevents.in/hyderabad. Selectors verified April 2026."""

    @property
    def source_name(self) -> str:
        return "allevents"

    async def _crawl_html(self, **kwargs) -> CrawlResult:
        events: List[Event] = []

        config = await self.load_config()
        if config and config.get('is_active') is False:
            logger.info("Crawler 'allevents' is disabled, skipping")
            return CrawlResult(events=[], success=True)

        try:
            url = config.get('url', 'https://allevents.in/hyderabad/all') if config else 'https://allevents.in/hyderabad/all'
            html = await self.fetch_page(url)
            soup = self.soup(html)

            # Each event card lives inside <div class="event-style-top-v3">
            event_cards = soup.find_all('div', class_='event-style-top-v3')
            logger.info(f"Found {len(event_cards)} event cards on allevents.in")

            for card in event_cards:
                try:
                    # The card wraps a single <a class="item-v3"> with href and title
                    link_elem = card.find('a', class_='item-v3')
                    if not link_elem:
                        continue

                    href = link_elem.get('href', '')
                    title_attr = link_elem.get('title', '').strip()

                    # Title is also in <h3 class="event-title-v3">
                    title_elem = card.find('h3', class_='event-title-v3')
                    title = (title_elem.text.strip() if title_elem else title_attr) or None
                    if not title:
                        continue

                    # Date in <div class="event-date-v3">
                    date_elem = card.find('div', class_='event-date-v3')
                    date_str = date_elem.text.strip() if date_elem else None
                    event_date = self._parse_allevents_date(date_str) if date_str else None

                    # Image in <img class="banner-image-v3">
                    img_elem = card.find('img', class_='banner-image-v3')
                    image_url = img_elem.get('src') if img_elem else None

                    # Source event ID from data-eid on the interested button
                    eid_elem = card.find('i', class_='event-interested-action')
                    source_event_id = eid_elem.get('data-eid') if eid_elem else None

                    event = Event(
                        title=title,
                        event_date=event_date,
                        link=href,
                        image_url=image_url,
                        source_url=href,
                        source_id=source_event_id,
                        category="events",
                        status=EventStatus.DRAFT,
                    )
                    events.append(event)

                except Exception as e:
                    logger.error(f"Error parsing allevents card: {e}")
                    continue

            return await self.save_events(events)

        except Exception as e:
            logger.error(f"Error crawling allevents.in: {e}")
            return CrawlResult(events=events, success=False, error_message=str(e))

    def _parse_allevents_date(self, text: str) -> Optional[datetime]:
        """Parse date strings like 'Sun, 26 Apr . 05:00 AM' or 'Sat, 12 Apr'."""
        text = text.replace('•', '.').replace('·', '.').strip()
        # Try with time
        for fmt in [
            '%a, %d %b . %I:%M %p',
            '%a, %d %b %Y . %I:%M %p',
            '%a, %d %b',
            '%a, %d %b %Y',
        ]:
            try:
                dt = datetime.strptime(text, fmt)
                # If year is 1900 (missing), assume current year
                if dt.year == 1900:
                    dt = dt.replace(year=datetime.now().year)
                return dt
            except ValueError:
                continue
        return self.parse_date(text)


# ---------------------------------------------------------------------------
# Meetup.com — extract Apollo state from __NEXT_DATA__ JSON
# ---------------------------------------------------------------------------

@register_crawler("meetup")
class MeetupCrawler(HTMLCrawler):
    """
    Crawler for Meetup.com Hyderabad events.
    Meetup is a Next.js app that embeds Apollo state in __NEXT_DATA__.
    No API key needed — scrapes the public search page.
    """

    @property
    def source_name(self) -> str:
        return "meetup"

    async def _crawl_html(self, **kwargs) -> CrawlResult:
        events: List[Event] = []

        config = await self.load_config()
        if config and config.get('is_active') is False:
            logger.info("Crawler 'meetup' is disabled, skipping")
            return CrawlResult(events=[], success=True)

        try:
            url = (
                config.get('url', 'https://www.meetup.com/find/?location=in--hyderabad&source=EVENTS')
                if config
                else 'https://www.meetup.com/find/?location=in--hyderabad&source=EVENTS'
            )
            html = await self.fetch_page(url)

            # Extract __NEXT_DATA__ JSON
            match = re.search(
                r'id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                html,
                re.DOTALL,
            )
            if not match:
                logger.warning("Could not find __NEXT_DATA__ on Meetup page")
                return CrawlResult(events=[], success=False, error_message="No __NEXT_DATA__")

            next_data = json.loads(match.group(1))
            apollo = (
                next_data.get('props', {})
                .get('pageProps', {})
                .get('__APOLLO_STATE__', {})
            )

            # Collect Event entries from Apollo cache
            event_entries = {
                k: v for k, v in apollo.items()
                if k.startswith('Event:') and isinstance(v, dict) and 'title' in v
            }
            logger.info(f"Found {len(event_entries)} events in Meetup Apollo state")

            for key, node in event_entries.items():
                try:
                    title = node.get('title', '').strip()
                    if not title:
                        continue

                    # Date
                    dt_str = node.get('dateTime', '')
                    event_date = None
                    if dt_str:
                        try:
                            event_date = datetime.fromisoformat(dt_str)
                        except ValueError:
                            event_date = self.parse_date(dt_str)

                    event_url = node.get('eventUrl', '')

                    # Image: resolve __ref to PhotoInfo
                    image_url = None
                    photo_ref = node.get('featuredEventPhoto', {})
                    if isinstance(photo_ref, dict) and '__ref' in photo_ref:
                        photo = apollo.get(photo_ref['__ref'], {})
                        image_url = photo.get('highResUrl') or photo.get('baseUrl')

                    # Group name (venue proxy)
                    group_ref = node.get('group', {})
                    group_name = None
                    if isinstance(group_ref, dict) and '__ref' in group_ref:
                        group = apollo.get(group_ref['__ref'], {})
                        group_name = group.get('name')

                    # Venue info
                    venue_ref = node.get('venue', {})
                    venue_name = None
                    venue_address = None
                    if isinstance(venue_ref, dict) and '__ref' in venue_ref:
                        venue = apollo.get(venue_ref['__ref'], {})
                        venue_name = venue.get('name')
                        venue_address = venue.get('address')

                    location = venue_name or group_name
                    area = self.extract_area_from_location(location) if location else None

                    # Fee
                    fee = node.get('feeSettings')
                    price = None
                    if isinstance(fee, dict) and fee.get('amount'):
                        price = f"{fee['amount']} {fee.get('currency', 'INR')}"

                    event = Event(
                        title=title,
                        description=(node.get('description', '') or '')[:500],
                        event_date=event_date,
                        location=location,
                        area=area,
                        venue=venue_name or group_name,
                        price=price,
                        link=event_url,
                        image_url=image_url,
                        source_url=event_url,
                        source_id=str(node.get('id', '')),
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
            return CrawlResult(events=events, success=False, error_message=str(e))


# ---------------------------------------------------------------------------
# Insider.in — SPA, requires headless browser
# ---------------------------------------------------------------------------

@register_crawler("insider")
class InsiderCrawler(HTMLCrawler):
    """
    Crawler for insider.in Hyderabad events.

    Insider.in is a pure client-rendered SPA. Static HTML fetching returns
    only a shell with <script> tags. A headless browser (Playwright/Selenium)
    is required to render the page and extract events.

    TODO: Implement with Playwright when headless browser support is added.
    """

    @property
    def source_name(self) -> str:
        return "insider"

    async def _crawl_html(self, **kwargs) -> CrawlResult:
        config = await self.load_config()
        if config and config.get('is_active') is False:
            logger.info("Crawler 'insider' is disabled, skipping")
            return CrawlResult(events=[], success=True)

        logger.warning(
            "Insider.in is a client-rendered SPA. "
            "Static crawling is not possible — needs headless browser."
        )
        return CrawlResult(
            events=[],
            success=False,
            error_message="Insider.in requires headless browser (Playwright). Not yet implemented.",
        )


# ---------------------------------------------------------------------------
# BookMyShow — SPA, requires headless browser
# ---------------------------------------------------------------------------

@register_crawler("bookmyshow")
class BookMyShowCrawler(HTMLCrawler):
    """
    Crawler for BookMyShow Hyderabad events.

    BookMyShow is a client-rendered SPA. Static fetching returns no event
    data. Requires headless browser.

    TODO: Implement with Playwright when headless browser support is added.
    """

    @property
    def source_name(self) -> str:
        return "bookmyshow"

    async def _crawl_html(self, **kwargs) -> CrawlResult:
        config = await self.load_config()
        if config and config.get('is_active') is False:
            logger.info("Crawler 'bookmyshow' is disabled, skipping")
            return CrawlResult(events=[], success=True)

        logger.warning(
            "BookMyShow is a client-rendered SPA. "
            "Static crawling is not possible — needs headless browser."
        )
        return CrawlResult(
            events=[],
            success=False,
            error_message="BookMyShow requires headless browser (Playwright). Not yet implemented.",
        )
