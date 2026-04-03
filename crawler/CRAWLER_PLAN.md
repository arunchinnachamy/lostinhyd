# Lost in Hyd - Event Crawler Plan

## Overview
Multi-source event crawler system for aggregating Hyderabad events from popular platforms. Raw crawled data stored in PostgreSQL, verified and cleaned before pushing to D1.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Event Sources  │────▶│  Crawler Engine  │────▶│  PostgreSQL   │
│  (Websites)     │     │  (Python)        │     │  (Raw Data)     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                                                            │
                                                            ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Cloudflare D1  │◀────│  Data Cleaner    │◀────│  Verification   │
│  (Production)   │     │  & Transformer   │     │  Queue          │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Phase 1: Target Sources (Priority Order)

### Tier 1 - High Priority (High volume, structured data)
1. **BookMyShow** (in.bookmyshow.com/explore/events-hyderabad)
   - Events, parties, meetups, comedy shows
   - Rich metadata: dates, venue, prices, images
   - ~100-200 events/month

2. **EventsHigh** (eventshigh.com/hyderabad)
   - Local events, workshops, classes
   - Good categorization
   - ~50-100 events/month

3. **Meetup.com** (meetup.com/find/in--hyderabad/)
   - Tech meetups, networking, hobby groups
   - API available
   - ~30-50 events/month

### Tier 2 - Medium Priority (Good data, moderate volume)
4. **AllEvents.in** (allevents.in/hyderabad)
   - Comprehensive listing
   - Free and paid events
   - ~40-80 events/month

5. **Townscript** (townscript.com/in/hyderabad)
   - Workshops, conferences, marathons
   - ~20-40 events/month

6. **FullHyderabad** (events.fullhyderabad.com)
   - Local city events
   - Cultural events focus
   - ~30-60 events/month

### Tier 3 - Future Expansion
7. **10Times** (10times.com/hyderabad-in) - Conferences, trade shows
8. **Hyderabad Party Animal** (Instagram/Facebook based)
9. **Venue-specific**: Hard Rock Cafe, The Moonshine Project, etc.
10. **Social Media**: Eventbrite, Facebook Events (via API)

## Phase 2: PostgreSQL Schema (Raw Crawled Data)

### Schema: `crawler`

#### Table: `raw_events`
```sql
CREATE TABLE crawler.raw_events (
    id SERIAL PRIMARY KEY,
    
    -- Source tracking
    source_name VARCHAR(50) NOT NULL,  -- 'bookmyshow', 'meetup', etc.
    source_url TEXT NOT NULL,          -- Original event URL
    source_id VARCHAR(255),             -- Source's internal event ID
    crawl_batch_id UUID,                -- Group crawls together
    
    -- Raw extracted data (as-is from source)
    raw_title TEXT NOT NULL,
    raw_description TEXT,
    raw_date_text TEXT,                 -- Original date string
    raw_time_text TEXT,                 -- Original time string
    raw_location_text TEXT,             -- Venue/location as text
    raw_price_text TEXT,                -- Price as displayed
    raw_image_urls TEXT[],              -- Array of image URLs
    raw_category_text TEXT,             -- Category as text
    raw_organizer TEXT,
    raw_contact_info TEXT,
    
    -- Structured data (parsed but not cleaned)
    parsed_start_date DATE,
    parsed_start_time TIME,
    parsed_end_date DATE,
    parsed_end_time TIME,
    parsed_venue_name TEXT,
    parsed_address TEXT,
    parsed_city TEXT DEFAULT 'Hyderabad',
    parsed_latitude DECIMAL(10,8),
    parsed_longitude DECIMAL(11,8),
    parsed_is_free BOOLEAN,
    parsed_price_min DECIMAL(10,2),
    parsed_price_max DECIMAL(10,2),
    parsed_currency VARCHAR(3) DEFAULT 'INR',
    parsed_age_limit TEXT,
    
    -- Crawl metadata
    crawl_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    crawl_status VARCHAR(20) DEFAULT 'success',  -- success, error, partial
    crawl_error_message TEXT,
    http_status INTEGER,
    page_html_hash VARCHAR(64),         -- For change detection
    
    -- Processing status
    processing_status VARCHAR(20) DEFAULT 'pending',  -- pending, cleaning, verified, rejected, duplicate
    processing_notes TEXT,
    duplicate_of_id INTEGER REFERENCES crawler.raw_events(id),
    
    -- Data quality scores
    completeness_score INTEGER,  -- 0-100
    accuracy_score INTEGER,      -- 0-100
    confidence_score INTEGER,    -- 0-100
    
    -- Verification
    verified_by VARCHAR(50),     -- 'auto', 'manual', 'ai'
    verified_at TIMESTAMP,
    
    -- Migration tracking
    migrated_to_d1 BOOLEAN DEFAULT FALSE,
    migrated_at TIMESTAMP,
    d1_event_id INTEGER,         -- Reference to lostinhyd.events
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_raw_events_source ON crawler.raw_events(source_name);
CREATE INDEX idx_raw_events_status ON crawler.raw_events(processing_status);
CREATE INDEX idx_raw_events_migrated ON crawler.raw_events(migrated_to_d1);
CREATE INDEX idx_raw_events_date ON crawler.raw_events(parsed_start_date);
CREATE INDEX idx_raw_events_crawl_time ON crawler.raw_events(crawl_timestamp);
CREATE INDEX idx_raw_events_batch ON crawler.raw_events(crawl_batch_id);
```

#### Table: `crawl_batches`
```sql
CREATE TABLE crawler.crawl_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    source_name VARCHAR(50),  -- NULL = all sources
    events_found INTEGER DEFAULT 0,
    events_added INTEGER DEFAULT 0,
    events_updated INTEGER DEFAULT 0,
    events_rejected INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'running',  -- running, completed, failed
    logs TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Table: `source_configs`
```sql
CREATE TABLE crawler.source_configs (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(50) UNIQUE NOT NULL,
    source_url TEXT NOT NULL,
    source_type VARCHAR(20) NOT NULL,  -- 'api', 'html_scrape', 'rss', 'graphql'
    
    -- Crawl settings
    crawl_frequency VARCHAR(20) DEFAULT 'daily',  -- hourly, daily, weekly
    crawl_hour INTEGER DEFAULT 6,  -- UTC hour to run
    rate_limit_requests INTEGER DEFAULT 10,  -- per minute
    request_timeout INTEGER DEFAULT 30,  -- seconds
    retry_attempts INTEGER DEFAULT 3,
    
    -- Selector configs (for HTML scraping)
    selector_config JSONB,  -- Store CSS selectors, XPath, etc.
    
    -- API configs
    api_config JSONB,  -- endpoints, headers, auth
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_crawled_at TIMESTAMP,
    last_error_at TIMESTAMP,
    last_error_message TEXT,
    total_crawls INTEGER DEFAULT 0,
    total_events_found INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert source configs
INSERT INTO crawler.source_configs (source_name, source_url, source_type, crawl_frequency, rate_limit_requests) VALUES
('bookmyshow', 'https://in.bookmyshow.com/explore/events-hyderabad', 'html_scrape', 'daily', 20),
('eventshigh', 'https://www.eventshigh.com/hyderabad', 'html_scrape', 'daily', 15),
('meetup', 'https://www.meetup.com/find/in--hyderabad/', 'api', 'daily', 30),
('allevents', 'https://allevents.in/hyderabad', 'html_scrape', 'daily', 15),
('townscript', 'https://www.townscript.com/in/hyderabad', 'html_scrape', 'daily', 10),
('fullhyderabad', 'https://events.fullhyderabad.com', 'html_scrape', 'daily', 10);
```

#### Table: `data_quality_rules`
```sql
CREATE TABLE crawler.data_quality_rules (
    id SERIAL PRIMARY KEY,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,  -- 'required', 'format', 'range', 'custom'
    field_name VARCHAR(100) NOT NULL,
    condition TEXT,  -- SQL expression or regex
    error_message TEXT,
    severity VARCHAR(20) DEFAULT 'warning',  -- error, warning, info
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert quality rules
INSERT INTO crawler.data_quality_rules (rule_name, rule_type, field_name, condition, error_message, severity) VALUES
('title_required', 'required', 'raw_title', NULL, 'Event title is required', 'error'),
('title_length', 'format', 'raw_title', 'LENGTH(raw_title) >= 5', 'Title must be at least 5 characters', 'warning'),
('date_required', 'required', 'raw_date_text', NULL, 'Event date is required', 'warning'),
('future_date', 'custom', 'parsed_start_date', 'parsed_start_date >= CURRENT_DATE', 'Event date is in the past', 'warning'),
('price_positive', 'range', 'parsed_price_min', 'parsed_price_min >= 0', 'Price cannot be negative', 'error'),
('venue_required', 'required', 'raw_location_text', NULL, 'Venue information is missing', 'warning'),
('description_length', 'format', 'raw_description', 'LENGTH(raw_description) >= 20', 'Description is too short', 'info');
```

## Phase 3: Crawler Architecture

### Directory Structure
```
crawler/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Config, env vars
│   └── sources.py           # Source definitions
├── core/
│   ├── __init__.py
│   ├── base_crawler.py      # Abstract base class
│   ├── http_client.py       # Rate-limited HTTP client
│   ├── parser.py            # HTML/JSON parsers
│   └── data_store.py        # PostgreSQL interface
├── sources/
│   ├── __init__.py
│   ├── bookmyshow.py        # BookMyShow crawler
│   ├── eventshigh.py        # EventsHigh crawler
│   ├── meetup.py            # Meetup crawler
│   ├── allevents.py         # AllEvents crawler
│   ├── townscript.py        # Townscript crawler
│   └── fullhyderabad.py     # FullHyderabad crawler
├── cleaning/
│   ├── __init__.py
│   ├── data_cleaner.py      # Clean & normalize
│   ├── venue_matcher.py     # Match venues
│   ├── deduplicator.py      # Find duplicates
│   └── validator.py         # Apply quality rules
├── pipeline/
│   ├── __init__.py
│   ├── crawler_runner.py    # Orchestrate crawls
│   ├── batch_manager.py     # Manage crawl batches
│   └── d1_sync.py           # Sync to D1 (verified only)
├── utils/
│   ├── __init__.py
│   ├── date_parser.py       # Parse various date formats
│   ├── venue_extractor.py   # Extract venue info
│   ├── price_parser.py      # Parse price text
│   └── logger.py            # Structured logging
├── tests/
│   └── ...
├── requirements.txt
├── run_crawler.py           # CLI entry point
└── run_cleaner.py           # Data cleaning entry point
```

### Core Components

#### 1. Base Crawler (`core/base_crawler.py`)
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging

class BaseCrawler(ABC):
    """Abstract base class for all event crawlers"""
    
    def __init__(self, source_name: str, config: Dict[str, Any]):
        self.source_name = source_name
        self.config = config
        self.logger = logging.getLogger(f"crawler.{source_name}")
        self.stats = {
            'found': 0,
            'added': 0,
            'updated': 0,
            'errors': 0
        }
    
    @abstractmethod
    async def fetch_events(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch raw events from source"""
        pass
    
    @abstractmethod
    def parse_event(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse raw data into structured format"""
        pass
    
    async def crawl(self, batch_id: str) -> Dict[str, int]:
        """Main crawl method"""
        self.logger.info(f"Starting crawl for {self.source_name}")
        
        try:
            raw_events = await self.fetch_events()
            
            for raw in raw_events:
                try:
                    parsed = self.parse_event(raw)
                    await self._store_raw_event(parsed, batch_id)
                    self.stats['found'] += 1
                except Exception as e:
                    self.logger.error(f"Error parsing event: {e}")
                    self.stats['errors'] += 1
            
            self.logger.info(f"Crawl completed: {self.stats}")
            return self.stats
            
        except Exception as e:
            self.logger.error(f"Crawl failed: {e}")
            raise
    
    async def _store_raw_event(self, event: Dict[str, Any], batch_id: str):
        """Store in PostgreSQL raw_events table"""
        # Implementation
        pass
```

#### 2. Rate-Limited HTTP Client (`core/http_client.py`)
```python
import asyncio
import aiohttp
from typing import Optional
import random

class RateLimitedClient:
    """HTTP client with rate limiting and retry logic"""
    
    def __init__(self, rate_limit: int = 10, timeout: int = 30):
        self.rate_limit = rate_limit  # requests per minute
        self.timeout = timeout
        self.session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(rate_limit)
        self._last_request_time = 0
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get(self, url: str, **kwargs) -> aiohttp.ClientResponse:
        async with self._semaphore:
            # Rate limiting delay
            await self._apply_rate_limit()
            
            try:
                async with self.session.get(url, **kwargs) as response:
                    await response.text()  # Read body
                    return response
            except Exception as e:
                self.logger.error(f"HTTP error for {url}: {e}")
                raise
    
    async def _apply_rate_limit(self):
        """Ensure we don't exceed rate limit"""
        min_interval = 60.0 / self.rate_limit
        elapsed = asyncio.get_event_loop().time() - self._last_request_time
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed + random.uniform(0.1, 0.5))
        self._last_request_time = asyncio.get_event_loop().time()
```

#### 3. Data Store (`core/data_store.py`)
```python
import asyncpg
from typing import Dict, Any, Optional
import json

class RawDataStore:
    """Interface to PostgreSQL raw data schema"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        self.pool = await asyncpg.create_pool(self.database_url)
    
    async def close(self):
        if self.pool:
            await self.pool.close()
    
    async def create_crawl_batch(self, source_name: Optional[str] = None) -> str:
        """Create a new crawl batch and return batch_id"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO crawler.crawl_batches (source_name, status)
                   VALUES ($1, 'running') RETURNING id""",
                source_name
            )
            return str(row['id'])
    
    async def store_raw_event(self, event: Dict[str, Any], batch_id: str) -> int:
        """Store raw event data"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO crawler.raw_events (
                    source_name, source_url, source_id, crawl_batch_id,
                    raw_title, raw_description, raw_date_text, raw_time_text,
                    raw_location_text, raw_price_text, raw_image_urls, raw_category_text,
                    parsed_start_date, parsed_start_time, parsed_venue_name,
                    crawl_timestamp, crawl_status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, NOW(), 'success')
                ON CONFLICT (source_name, source_id) DO UPDATE SET
                    raw_title = EXCLUDED.raw_title,
                    raw_description = EXCLUDED.raw_description,
                    crawl_timestamp = NOW(),
                    crawl_batch_id = EXCLUDED.crawl_batch_id
                RETURNING id
            """, 
                event.get('source_name'),
                event.get('source_url'),
                event.get('source_id'),
                batch_id,
                event.get('raw_title'),
                event.get('raw_description'),
                event.get('raw_date_text'),
                event.get('raw_time_text'),
                event.get('raw_location_text'),
                event.get('raw_price_text'),
                event.get('raw_image_urls', []),
                event.get('raw_category_text'),
                event.get('parsed_start_date'),
                event.get('parsed_start_time'),
                event.get('parsed_venue_name')
            )
            return row['id']
    
    async def update_batch_stats(self, batch_id: str, stats: Dict[str, int]):
        """Update crawl batch statistics"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE crawler.crawl_batches
                SET events_found = $1,
                    events_added = $2,
                    completed_at = NOW(),
                    status = 'completed'
                WHERE id = $3
            """, stats['found'], stats['added'], batch_id)
    
    async def get_pending_verification(self, limit: int = 100) -> list:
        """Get events pending verification"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM crawler.raw_events
                WHERE processing_status = 'pending'
                  AND crawl_status = 'success'
                ORDER BY crawl_timestamp DESC
                LIMIT $1
            """, limit)
            return [dict(row) for row in rows]
```

## Phase 4: Data Cleaning Pipeline

### Cleaning Process
1. **Parse & Normalize**
   - Parse dates (handle multiple formats)
   - Normalize venue names
   - Extract price ranges
   - Clean HTML from descriptions

2. **Deduplication**
   - Compare with existing events (title + date + venue)
   - Fuzzy matching for similar titles
   - Mark duplicates, keep best version

3. **Venue Matching**
   - Match against known venues in D1
   - Extract new venues for review
   - Geocode addresses to lat/lng

4. **Quality Scoring**
   - Completeness: % of fields filled
   - Accuracy: regex validations
   - Confidence: source reliability

5. **Category Mapping**
   - Map source categories to D1 categories
   - Auto-categorize if missing

### Verification Levels
- **Auto-verified** (score > 90): Direct to D1
- **Manual review** (score 70-90): Queue for human check
- **Rejected** (score < 70): Keep in raw but don't sync

## Phase 5: D1 Sync Process

### Sync Rules
1. Only sync `processing_status = 'verified'`
2. Never sync `migrated_to_d1 = TRUE` (prevent duplicates)
3. Check for existing events in D1 before insert
4. Transform to D1 schema
5. Update `migrated_to_d1` flag after successful sync

### Sync Frequency
- Auto-verified: Every 2 hours
- Manual verified: Immediately after approval
- Daily full reconciliation

## Implementation Timeline

### Week 1
- [ ] Set up PostgreSQL crawler schema
- [ ] Build core crawler framework
- [ ] Implement HTTP client with rate limiting
- [ ] Create data store interface

### Week 2
- [ ] Implement BookMyShow crawler
- [ ] Implement EventsHigh crawler
- [ ] Add date/price/venue parsers
- [ ] Build crawler runner CLI

### Week 3
- [ ] Implement Meetup crawler (API-based)
- [ ] Implement AllEvents crawler
- [ ] Build data cleaning pipeline
- [ ] Add deduplication logic

### Week 4
- [ ] Implement remaining crawlers
- [ ] Build verification UI/API
- [ ] Create D1 sync process
- [ ] Add monitoring and alerting
- [ ] Deploy to production

## Success Metrics
- **Coverage**: 80%+ of Hyderabad events from major sources
- **Freshness**: Events updated within 24 hours of source
- **Accuracy**: <5% error rate in event details
- **Completeness**: 90%+ of events have date, venue, title
- **Latency**: New events appear on site within 4 hours of source

## Risks & Mitigations
1. **Source blocking**: Rotate IPs, respect robots.txt, add delays
2. **Data quality**: Multi-level verification, manual review queue
3. **Schema changes**: Versioned parsers, monitoring alerts
4. **Scale**: PostgreSQL for raw data, D1 for production
