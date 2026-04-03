# Lost in Hyd Event Crawler

A multi-source event crawler for aggregating Hyderabad events from popular platforms.

## Architecture

```
Sources (Websites) → Crawler → PostgreSQL (Raw) → Cleaner → Verified → D1 (Production)
```

## Features

- **Multi-source crawling**: BookMyShow, EventsHigh, Meetup, AllEvents, Townscript, FullHyderabad
- **Raw data storage**: All crawled data stored in PostgreSQL for verification
- **Rate limiting**: Respects website rate limits with configurable delays
- **Data quality scoring**: Completeness, accuracy, and confidence scores
- **Duplicate detection**: Prevents storing the same event multiple times
- **D1 sync**: Only verified data syncs to production D1 database

## Quick Start

### 1. Setup Environment
```bash
cd crawler
pip install -r requirements.txt
```

### 2. Configure Database
Set `DATABASE_URL` environment variable (use your actual database URL):
```bash
export DATABASE_URL="your-postgres-connection-string"
```

### 3. Run Crawler
```bash
# Run specific crawler
python run_crawler.py --source bookmyshow

# Run all active crawlers
python run_crawler.py --all
```

## Database Schema

The crawler uses a separate `crawler` schema in PostgreSQL with:

- **`raw_events`**: Stores all crawled event data
- **`crawl_batches`**: Tracks crawl operations
- **`source_configs`**: Configuration for each source
- **`data_quality_rules`**: Rules for data validation

See `schema.sql` for full schema definition.

## Adding New Sources

1. Create a new file in `sources/` (e.g., `eventshigh.py`)
2. Inherit from `BaseCrawler`
3. Implement `fetch_events()` and `parse_event()` methods
4. Add source config to `crawler.source_configs` table

Example:
```python
from core.base_crawler import BaseCrawler

class EventsHighCrawler(BaseCrawler):
    async def fetch_events(self, **kwargs):
        # Fetch logic
        pass
    
    def parse_event(self, raw_data):
        # Parse logic
        pass
```

## Data Flow

1. **Crawl**: Fetch raw data from source websites
2. **Parse**: Extract structured information (dates, venues, prices)
3. **Store**: Save raw data to PostgreSQL with quality scores
4. **Clean**: Validate, deduplicate, normalize data
5. **Verify**: Manual or automated review
6. **Sync**: Push verified data to D1 for website display

## Target Sources

| Source | Type | Priority | Status |
|--------|------|----------|--------|
| BookMyShow | HTML | High | ✅ Implemented |
| EventsHigh | HTML | High | 🔄 Pending |
| Meetup.com | API | High | 🔄 Pending |
| AllEvents.in | HTML | Medium | 🔄 Pending |
| Townscript | HTML | Medium | 🔄 Pending |
| FullHyderabad | HTML | Medium | 🔄 Pending |

## Configuration

Sources are configured in the `crawler.source_configs` table:

```sql
SELECT * FROM crawler.source_configs;
```

Fields:
- `source_name`: Unique identifier
- `source_url`: Base URL
- `source_type`: 'html_scrape', 'api', 'rss'
- `crawl_frequency`: 'hourly', 'daily', 'weekly'
- `rate_limit_requests`: Max requests per minute

## Data Quality

Events are scored on:
- **Completeness** (0-100): % of fields filled
- **Accuracy** (0-100): Validation of data formats
- **Confidence** (0-100): Source reliability weight

Events with score > 90 can be auto-verified. Events < 70 are rejected.

## Next Steps

1. Implement remaining crawlers (EventsHigh, Meetup, etc.)
2. Build data cleaning pipeline
3. Create verification workflow
4. Build D1 sync process
5. Add monitoring and alerting
6. Schedule automated crawls (cron/Celery)

## Documentation

- `CRAWLER_PLAN.md`: Detailed architecture and implementation plan
- `schema.sql`: Database schema definition
