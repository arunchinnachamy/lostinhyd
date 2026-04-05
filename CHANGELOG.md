# Changelog

All notable changes to Lost in Hyd are documented here.

## [0.1.0.0] - 2026-04-05

### Added
- Admin control centre: React Admin SPA on Cloudflare Pages with bearer token auth
- Events, venues, sources, and crawl logs CRUD endpoints with column-whitelisted queries
- Dashboard with draft count, crawl run stats, success rate, and last-run-per-source table
- 46 integration tests (vitest) running against real PostgreSQL
- Database migrations matching the production lostinhyd schema (integer IDs, check constraints)
- Hyperdrive setup script for one-command Cloudflare deployment config

### Changed
- Crawlers aligned to real database schema: `sources` table (not `event_sources`), `venues` (not `places`), integer IDs
- AllEvents.in crawler: real CSS selectors from live HTML (`event-style-top-v3`, `event-title-v3`, `event-date-v3`)
- Meetup.com crawler: scrapes `__NEXT_DATA__` Apollo state instead of requiring API key
- Insider.in and BookMyShow crawlers: documented as client-rendered SPAs needing headless browser, return clear errors instead of silently failing
- Crawler field names updated: `events_added`/`events_skipped`/`completed_at`/`errors` matching production columns
- Python DB utilities (`utils/db.py`) updated for real schema: `sources` table, correct column names

### Fixed
- Dashboard "undefined%" display when crawl stats API returns empty data
- Dashboard fetch error handling for non-OK API responses
