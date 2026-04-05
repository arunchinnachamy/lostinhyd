"""
Database models and connection utilities for Lost in Hyd event aggregation system.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json
import os


class EventStatus(Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PlaceCategory(Enum):
    CAFE = "cafe"
    RESTAURANT = "restaurant"
    ATTRACTION = "attraction"
    PARK = "park"
    MARKET = "market"
    MUSEUM = "museum"
    OTHER = "other"


@dataclass
class Event:
    """Represents an event in Hyderabad"""
    title: str
    description: Optional[str] = None
    event_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[str] = None
    area: Optional[str] = None
    venue: Optional[str] = None
    price: Optional[str] = None
    currency: str = "INR"
    link: Optional[str] = None
    image_url: Optional[str] = None
    source: str = "manual"
    source_url: Optional[str] = None
    source_id: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = None
    status: EventStatus = EventStatus.DRAFT
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    crawled_at: Optional[datetime] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'location': self.location,
            'area': self.area,
            'venue': self.venue,
            'price': self.price,
            'currency': self.currency,
            'link': self.link,
            'image_url': self.image_url,
            'source': self.source,
            'source_url': self.source_url,
            'source_id': self.source_id,
            'category': self.category,
            'tags': self.tags,
            'status': self.status.value,
        }


@dataclass
class Place:
    """Represents a place in Hyderabad"""
    name: str
    description: Optional[str] = None
    area: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    map_link: Optional[str] = None
    category: Optional[PlaceCategory] = None
    tags: List[str] = None
    hero_image_url: Optional[str] = None
    image_urls: List[str] = None
    best_time: Optional[str] = None
    must_try: Optional[str] = None
    price_range: Optional[str] = None
    timings: Optional[Dict[str, str]] = None
    contact_info: Optional[Dict[str, str]] = None
    source: str = "manual"
    source_url: Optional[str] = None
    featured: bool = False
    status: EventStatus = EventStatus.DRAFT
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.image_urls is None:
            self.image_urls = []


class Database:
    """Database connection and operations"""

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            connection_string: PostgreSQL connection string. If not provided,
                             will look for DATABASE_URL env variable.
        """
        self.connection_string = connection_string or os.getenv('DATABASE_URL')
        if not self.connection_string:
            raise ValueError("Database connection string required. Set DATABASE_URL env variable.")

        self._pool = None

    async def connect(self):
        """Initialize connection pool"""
        import asyncpg
        self._pool = await asyncpg.create_pool(self.connection_string)

    async def close(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()

    async def upsert_event(self, event: Event) -> str:
        """
        Insert or update an event.
        Returns the event ID.
        """
        async with self._pool.acquire() as conn:
            # Check if event exists
            if event.source_id:
                existing = await conn.fetchrow(
                    "SELECT id FROM events WHERE source = $1 AND source_id = $2",
                    event.source, event.source_id
                )
                if existing:
                    event.id = existing['id']

            if event.id:
                # Update
                await conn.execute(
                    """
                    UPDATE events SET
                        title = $1, description = $2, event_date = $3, end_date = $4,
                        location = $5, area = $6, venue = $7, price = $8, currency = $9,
                        link = $10, image_url = $11, category = $12, tags = $13,
                        status = $14, source_url = $15, updated_at = NOW()
                    WHERE id = $16
                    """,
                    event.title, event.description, event.event_date, event.end_date,
                    event.location, event.area, event.venue, event.price, event.currency,
                    event.link, event.image_url, event.category, event.tags,
                    event.status.value, event.source_url, event.id
                )
                return event.id
            else:
                # Insert
                record = await conn.fetchrow(
                    """
                    INSERT INTO events (
                        title, description, event_date, end_date, location, area, venue,
                        price, currency, link, image_url, source, source_url, source_id,
                        category, tags, status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                    RETURNING id
                    """,
                    event.title, event.description, event.event_date, event.end_date,
                    event.location, event.area, event.venue, event.price, event.currency,
                    event.link, event.image_url, event.source, event.source_url, event.source_id,
                    event.category, event.tags, event.status.value
                )
                return record['id']

    async def get_upcoming_events(
        self,
        area: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 50
    ) -> List[Event]:
        """Get upcoming events with optional filters"""
        async with self._pool.acquire() as conn:
            query = """
                SELECT * FROM events
                WHERE event_date >= NOW()
                AND status IN ('draft', 'published')
            """
            params = []

            if area:
                query += f" AND area ILIKE ${len(params) + 1}"
                params.append(f"%{area}%")

            if category:
                query += f" AND category = ${len(params) + 1}"
                params.append(category)

            query += " ORDER BY event_date ASC LIMIT $" + str(len(params) + 1)
            params.append(limit)

            rows = await conn.fetch(query, *params)
            return [self._row_to_event(row) for row in rows]

    async def get_events_by_source(self, source: str, days: int = 7) -> List[Event]:
        """Get events from a specific source crawled in last N days"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM events
                WHERE source = $1
                AND crawled_at >= NOW() - INTERVAL '$2 days'
                ORDER BY crawled_at DESC
                """,
                source, days
            )
            return [self._row_to_event(row) for row in rows]

    async def start_crawl_log(self, source_name: str) -> Optional[str]:
        """
        Start a crawl log entry for the given source.

        Looks up the source_id from sources by name, inserts a new
        crawl_logs row with status='running', and returns the log id.
        Returns None if the source is not found or an error occurs.
        """
        try:
            async with self._pool.acquire() as conn:
                source_row = await conn.fetchrow(
                    "SELECT id FROM sources WHERE name = $1",
                    source_name,
                )
                if not source_row:
                    return None

                row = await conn.fetchrow(
                    """
                    INSERT INTO crawl_logs (source_id, status)
                    VALUES ($1, 'running')
                    RETURNING id
                    """,
                    source_row['id'],
                )
                return str(row['id'])
        except Exception:
            return None

    async def end_crawl_log(
        self,
        log_id: str,
        success: bool,
        error_message: Optional[str] = None,
        events_found: int = 0,
        events_added: int = 0,
        events_updated: int = 0,
        events_skipped: int = 0,
    ) -> None:
        """
        Finalise a crawl log entry with results.

        Args:
            log_id: The crawl_logs row id returned by start_crawl_log.
            success: Whether the crawl succeeded.
            error_message: Error message if the crawl failed.
            events_found: Total events discovered.
            events_added: New events inserted.
            events_updated: Existing events updated.
            events_skipped: Events that were skipped.
        """
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE crawl_logs SET
                        completed_at = NOW(),
                        status = $1,
                        errors = $2,
                        events_found = $3,
                        events_added = $4,
                        events_updated = $5,
                        events_skipped = $6
                    WHERE id = $7
                    """,
                    'success' if success else 'failed',
                    error_message,
                    events_found,
                    events_added,
                    events_updated,
                    events_skipped,
                    int(log_id),
                )
        except Exception:
            pass

    async def get_source_config(self, source_name: str) -> Dict[str, Any]:
        """
        Load configuration for a crawler source from sources table.

        Args:
            source_name: The name of the source.

        Returns:
            Dict with url, is_active, crawl_frequency,
            or empty dict if not found.
        """
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT url, is_active, crawl_frequency
                    FROM sources WHERE name = $1
                    """,
                    source_name,
                )
                if not row:
                    return {}
                return {
                    'url': row['url'],
                    'is_active': row['is_active'],
                    'crawl_frequency': row['crawl_frequency'],
                }
        except Exception:
            return {}

    def _row_to_event(self, row) -> Event:
        """Convert database row to Event object"""
        return Event(
            id=str(row['id']),
            title=row['title'],
            description=row['description'],
            event_date=row['event_date'],
            end_date=row['end_date'],
            location=row['location'],
            area=row['area'],
            venue=row['venue'],
            price=row['price'],
            currency=row['currency'],
            link=row['link'],
            image_url=row['image_url'],
            source=row['source'],
            source_url=row['source_url'],
            source_id=row['source_id'],
            category=row['category'],
            tags=row['tags'] or [],
            status=EventStatus(row['status']),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            crawled_at=row['crawled_at'],
        )


# Connection string helper
def get_connection_string(
    host: Optional[str] = None,
    port: Optional[int] = None,
    database: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None
) -> str:
    """Build connection string from components or env vars"""
    host = host or os.getenv('PGHOST', 'localhost')
    port = port or int(os.getenv('PGPORT', '5432'))
    database = database or os.getenv('PGDATABASE', 'lostinhyd')
    user = user or os.getenv('PGUSER', 'postgres')
    password = password or os.getenv('PGPASSWORD', '')

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"
