#!/usr/bin/env python3
"""
Data cleaning process for raw crawled events
Usage: python clean_data.py [--batch-id <uuid>]
"""

import asyncio
import argparse
import logging
import sys
import os
from datetime import date

# Add crawler to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
from core.data_store import RawDataStore
from cleaning.data_cleaner import DataCleaner

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("crawler.cleaner")


async def clean_batch(batch_id: str, database_url: str, dry_run: bool = False):
    """Clean all pending events in a batch"""
    data_store = RawDataStore(database_url)
    await data_store.connect()
    
    cleaner = DataCleaner()
    stats = {
        'processed': 0,
        'cleaned': 0,
        'verified': 0,
        'rejected': 0,
        'errors': 0
    }
    
    try:
        # Get pending events
        async with data_store.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM crawler.raw_events
                WHERE crawl_batch_id = $1
                  AND processing_status = 'pending'
                  AND crawl_status = 'success'
                ORDER BY id
            """, batch_id)
        
        logger.info(f"Found {len(rows)} pending events to clean")
        
        for row in rows:
            try:
                raw_event = dict(row)
                stats['processed'] += 1
                
                # Clean the event
                cleaned, issues = cleaner.clean_event(raw_event)
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would clean: {cleaned['raw_title'][:50]}")
                    logger.info(f"  Issues: {issues}")
                    continue
                
                # Determine status
                if cleaner.should_auto_verify(cleaned):
                    cleaned['processing_status'] = 'verified'
                    cleaned['verified_by'] = 'auto'
                    cleaned['verified_at'] = date.today()
                    stats['verified'] += 1
                elif cleaned.get('completeness_score', 0) < 40:
                    cleaned['processing_status'] = 'rejected'
                    stats['rejected'] += 1
                else:
                    cleaned['processing_status'] = 'cleaned'
                    stats['cleaned'] += 1
                
                # Update in database
                async with data_store.pool.acquire() as conn:
                    await conn.execute("""
                        UPDATE crawler.raw_events
                        SET 
                            parsed_start_date = $1,
                            parsed_start_time = $2,
                            parsed_end_date = $3,
                            parsed_end_time = $4,
                            parsed_venue_name = $5,
                            parsed_address = $6,
                            parsed_area = $7,
                            parsed_city = $8,
                            parsed_latitude = $9,
                            parsed_longitude = $10,
                            parsed_is_free = $11,
                            parsed_price_min = $12,
                            parsed_price_max = $13,
                            parsed_currency = $14,
                            parsed_age_limit = $15,
                            raw_description = $16,
                            raw_image_urls = $17,
                            completeness_score = $18,
                            accuracy_score = $19,
                            confidence_score = $20,
                            processing_status = $21,
                            processing_notes = $22,
                            verified_by = $23,
                            verified_at = $24,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = $25
                    """,
                        cleaned.get('parsed_start_date'),
                        cleaned.get('parsed_start_time'),
                        cleaned.get('parsed_end_date'),
                        cleaned.get('parsed_end_time'),
                        cleaned.get('parsed_venue_name'),
                        cleaned.get('parsed_address'),
                        cleaned.get('parsed_area'),
                        cleaned.get('parsed_city'),
                        cleaned.get('parsed_latitude'),
                        cleaned.get('parsed_longitude'),
                        cleaned.get('parsed_is_free'),
                        cleaned.get('parsed_price_min'),
                        cleaned.get('parsed_price_max'),
                        cleaned.get('parsed_currency'),
                        cleaned.get('parsed_age_limit'),
                        cleaned.get('raw_description'),
                        cleaned.get('raw_image_urls'),
                        cleaned.get('completeness_score'),
                        cleaned.get('accuracy_score'),
                        cleaned.get('confidence_score'),
                        cleaned.get('processing_status'),
                        '; '.join(issues) if issues else None,
                        cleaned.get('verified_by'),
                        cleaned.get('verified_at'),
                        raw_event['id']
                    )
                
                logger.info(f"Cleaned: {cleaned['raw_title'][:50]}... -> {cleaned['processing_status']}")
                
            except Exception as e:
                logger.error(f"Error cleaning event {row.get('id')}: {e}")
                stats['errors'] += 1
        
        logger.info(f"Cleaning completed: {stats}")
        
    finally:
        await data_store.close()


async def clean_all_pending(database_url: str, dry_run: bool = False):
    """Clean all pending events across all batches"""
    data_store = RawDataStore(database_url)
    await data_store.connect()
    
    try:
        # Get all pending events
        async with data_store.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT crawl_batch_id, COUNT(*) as count
                FROM crawler.raw_events
                WHERE processing_status = 'pending'
                  AND crawl_status = 'success'
                GROUP BY crawl_batch_id
                ORDER BY count DESC
            """)
        
        logger.info(f"Found {len(rows)} batches with pending events")
        
        for row in rows:
            batch_id = row['crawl_batch_id']
            count = row['count']
            logger.info(f"\nProcessing batch {batch_id} ({count} events)")
            await clean_batch(batch_id, database_url, dry_run)
    
    finally:
        await data_store.close()


def main():
    parser = argparse.ArgumentParser(description='Clean raw crawled event data')
    parser.add_argument('--batch-id', '-b', help='Specific batch ID to clean')
    parser.add_argument('--all', '-a', action='store_true', help='Clean all pending events')
    parser.add_argument('--dry-run', '-d', action='store_true', help='Show what would be done without modifying')
    parser.add_argument('--database-url', help='PostgreSQL database URL')
    
    args = parser.parse_args()
    
    database_url = args.database_url or os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("No database URL provided. Set DATABASE_URL env var or use --database-url.")
        return 1
    
    if args.batch_id:
        asyncio.run(clean_batch(args.batch_id, database_url, args.dry_run))
    elif args.all:
        asyncio.run(clean_all_pending(database_url, args.dry_run))
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
