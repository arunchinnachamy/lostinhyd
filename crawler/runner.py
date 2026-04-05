#!/usr/bin/env python3
"""
Main crawler runner for Lost in Hyd event aggregation.

Usage:
    python -m crawler.runner --source insider
    python -m crawler.runner --all
    python -m crawler.runner --list
"""

import asyncio
import argparse
import logging
import os
import sys
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.base import get_crawler, list_crawlers, CrawlResult
from utils.db import Database, get_connection_string


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crawler.log')
    ]
)
logger = logging.getLogger(__name__)


async def run_crawler(source: str, db: Database) -> CrawlResult:
    """Run a single crawler and record the run in crawl_logs."""
    logger.info(f"Starting crawler: {source}")

    crawler = get_crawler(source, db)
    if not crawler:
        logger.error(f"Unknown crawler: {source}")
        return CrawlResult(events=[], success=False, error_message=f"Unknown crawler: {source}")

    # Start crawl log entry
    log_id = await db.start_crawl_log(source)
    if log_id:
        logger.info(f"Crawl log started: {log_id}")
    else:
        logger.warning(f"Could not create crawl log for source '{source}' (missing from sources table?)")

    try:
        result = await crawler.crawl()
        logger.info(
            f"Crawler {source} complete: "
            f"{result.events_added} added, "
            f"{result.events_updated} updated, "
            f"{result.events_skipped} skipped"
        )

        # End crawl log with success/failure details
        if log_id:
            await db.end_crawl_log(
                log_id=log_id,
                success=result.success,
                error_message=result.error_message,
                events_found=len(result.events),
                events_added=result.events_added,
                events_updated=result.events_updated,
                events_skipped=result.events_skipped,
            )

        return result
    except Exception as e:
        logger.error(f"Crawler {source} failed: {e}")
        result = CrawlResult(events=[], success=False, error_message=str(e))

        if log_id:
            await db.end_crawl_log(
                log_id=log_id,
                success=False,
                error_message=str(e),
            )

        return result


async def run_all_crawlers(db: Database) -> dict:
    """Run all registered crawlers"""
    sources = list_crawlers()
    results = {}

    logger.info(f"Running {len(sources)} crawlers: {', '.join(sources)}")

    for source in sources:
        results[source] = await run_crawler(source, db)
        # Small delay between crawlers
        await asyncio.sleep(2)

    return results


def print_summary(results: dict):
    """Print summary of all crawler results"""
    print("\n" + "=" * 60)
    print("CRAWL SUMMARY")
    print("=" * 60)

    total_new = 0
    total_updated = 0
    total_failed = 0

    for source, result in results.items():
        status = "OK" if result.success else "FAIL"
        print(f"\n[{status}] {source}")
        print(f"   Added: {result.events_added} | Updated: {result.events_updated} | Skipped: {result.events_skipped}")

        if result.error_message:
            print(f"   Error: {result.error_message[:100]}")

        total_new += result.events_added
        total_updated += result.events_updated
        total_failed += result.events_skipped

    print("\n" + "-" * 60)
    print(f"TOTAL: {total_new} added, {total_updated} updated, {total_failed} skipped")
    print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Lost in Hyd Event Crawler")
    parser.add_argument('--source', '-s', help='Run specific crawler by name')
    parser.add_argument('--all', '-a', action='store_true', help='Run all crawlers')
    parser.add_argument('--list', '-l', action='store_true', help='List available crawlers')
    parser.add_argument('--database-url', '-d', help='PostgreSQL connection string')

    args = parser.parse_args()

    # List mode
    if args.list:
        crawlers = list_crawlers()
        print("Available crawlers:")
        for c in crawlers:
            print(f"  - {c}")
        return

    # Initialize database
    try:
        db_url = args.database_url or os.getenv('DATABASE_URL') or get_connection_string()
        db = Database(db_url)
        await db.connect()
        logger.info("Connected to database")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        print(f"Error: Could not connect to database. {e}")
        sys.exit(1)

    try:
        # Run single crawler
        if args.source:
            result = await run_crawler(args.source, db)
            print_summary({args.source: result})

        # Run all crawlers
        elif args.all:
            results = await run_all_crawlers(db)
            print_summary(results)

        else:
            parser.print_help()

    finally:
        await db.close()
        logger.info("Database connection closed")


if __name__ == '__main__':
    asyncio.run(main())
