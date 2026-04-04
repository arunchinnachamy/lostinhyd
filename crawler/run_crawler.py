#!/usr/bin/env python3
"""
Crawler runner - CLI entry point for running crawlers
"""

import asyncio
import argparse
import logging
import sys
import os

from dotenv import load_dotenv

# Add crawler to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.data_store import RawDataStore
from sources.bookmyshow import BookMyShowCrawler
from core.browserless_client import BrowserlessClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("crawler.runner")


async def run_crawler(source_name: str, database_url: str, 
                      browserless_token: str = None, browserless_url: str = None):
    """Run a specific crawler"""
    # Initialize data store
    data_store = RawDataStore(database_url)
    await data_store.connect()
    
    try:
        # Create crawl batch
        batch_id = await data_store.create_crawl_batch(source_name)
        logger.info(f"Created crawl batch: {batch_id}")
        
        # Get crawler instance
        crawler = None
        if source_name == 'bookmyshow':
            crawler = BookMyShowCrawler(
                data_store=data_store,
                browserless_token=browserless_token,
                browserless_url=browserless_url
            )
        else:
            logger.error(f"Unknown source: {source_name}")
            return 1
        
        # Run crawl
        stats = await crawler.crawl(batch_id)
        
        # Update batch stats
        await data_store.update_batch_stats(batch_id, stats)
        
        # Update source last crawl
        if stats['errors'] > stats['found']:
            await data_store.update_source_last_crawl(
                source_name, 
                events_found=stats['found'],
                error=f"Had {stats['errors']} errors"
            )
        else:
            await data_store.update_source_last_crawl(
                source_name,
                events_found=stats['found']
            )
        
        logger.info(f"Crawl completed. Stats: {stats}")
        
    finally:
        await data_store.close()
    
    return 0


async def run_all_crawlers(database_url: str, browserless_token: str = None, browserless_url: str = None):
    """Run all active crawlers"""
    data_store = RawDataStore(database_url)
    await data_store.connect()
    
    try:
        # Get all active sources
        sources = await data_store.get_all_active_sources()
        logger.info(f"Found {len(sources)} active sources")
        
        for source in sources:
            source_name = source['source_name']
            logger.info(f"Running crawler for {source_name}")
            
            try:
                await run_crawler(source_name, database_url, browserless_token, browserless_url)
            except Exception as e:
                logger.error(f"Crawler {source_name} failed: {e}")
                continue
    
    finally:
        await data_store.close()


def main():
    parser = argparse.ArgumentParser(description='Lost in Hyd Event Crawler')
    parser.add_argument('--source', '-s', help='Source to crawl (bookmyshow, etc.)')
    parser.add_argument('--all', '-a', action='store_true', help='Run all active crawlers')
    parser.add_argument('--database-url', '-d', help='PostgreSQL database URL')
    parser.add_argument('--browserless-token', '-t', help='Browserless API token')
    parser.add_argument('--browserless-url', '-u', help='Browserless endpoint URL (default: https://chrome.browserless.io)')
    
    args = parser.parse_args()
    
    # Get database URL
    database_url = args.database_url or os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("No database URL provided. Set DATABASE_URL env var or use -d flag.")
        return 1
    
    # Get Browserless credentials
    browserless_token = args.browserless_token or os.getenv('BROWSERLESS_TOKEN')
    browserless_url = args.browserless_url or os.getenv('BROWSERLESS_URL', 'https://chrome.browserless.io')
    
    if browserless_token:
        logger.info(f"Using Browserless at {browserless_url}")
    else:
        logger.warning("No Browserless token provided. JavaScript sites may fail.")
    
    # Run crawlers
    if args.all:
        asyncio.run(run_all_crawlers(database_url, browserless_token, browserless_url))
    elif args.source:
        asyncio.run(run_crawler(args.source, database_url, browserless_token, browserless_url))
    else:
        parser.print_help()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
