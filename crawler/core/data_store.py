"""
PostgreSQL data store for raw crawled events
"""

import asyncpg
from typing import Dict, Any, Optional, List
import logging
import json


class RawDataStore:
    """Store and retrieve raw crawled event data from PostgreSQL"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None
        self.logger = logging.getLogger("crawler.data_store")
    
    async def connect(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(
            self.database_url,
            min_size=2,
            max_size=10
        )
        self.logger.info("Connected to PostgreSQL")
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            self.logger.info("Disconnected from PostgreSQL")
    
    async def create_crawl_batch(self, source_name: Optional[str] = None) -> str:
        """
        Create a new crawl batch and return batch_id
        
        Args:
            source_name: Name of source being crawled (or None for multi-source)
            
        Returns:
            UUID batch ID
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO crawler.crawl_batches (source_name, status)
                   VALUES ($1, 'running') RETURNING id""",
                source_name
            )
            batch_id = str(row['id'])
            self.logger.info(f"Created crawl batch {batch_id}")
            return batch_id
    
    async def store_raw_event(self, event: Dict[str, Any]) -> Optional[int]:
        """
        Store raw event data in PostgreSQL
        
        Args:
            event: Parsed event dictionary
            
        Returns:
            Event ID if new, None if updated/duplicate
        """
        async with self.pool.acquire() as conn:
            # Calculate quality scores
            completeness = self._calculate_completeness(event)
            
            try:
                row = await conn.fetchrow("""
                    INSERT INTO crawler.raw_events (
                        source_name, source_url, source_id, crawl_batch_id,
                        raw_title, raw_description, raw_date_text, raw_time_text,
                        raw_location_text, raw_price_text, raw_image_urls, raw_category_text,
                        raw_organizer, raw_contact_info,
                        parsed_start_date, parsed_start_time, parsed_end_date, parsed_end_time,
                        parsed_venue_name, parsed_address, parsed_city,
                        parsed_latitude, parsed_longitude,
                        parsed_is_free, parsed_price_min, parsed_price_max, parsed_currency,
                        parsed_age_limit,
                        crawl_status, http_status,
                        completeness_score, processing_status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14,
                              $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, 
                              $29, $30, $31, $32)
                    ON CONFLICT (source_name, source_id) DO UPDATE SET
                        raw_title = EXCLUDED.raw_title,
                        raw_description = EXCLUDED.raw_description,
                        raw_date_text = EXCLUDED.raw_date_text,
                        raw_time_text = EXCLUDED.raw_time_text,
                        raw_location_text = EXCLUDED.raw_location_text,
                        raw_price_text = EXCLUDED.raw_price_text,
                        raw_image_urls = EXCLUDED.raw_image_urls,
                        crawl_timestamp = CURRENT_TIMESTAMP,
                        crawl_batch_id = EXCLUDED.crawl_batch_id,
                        completeness_score = EXCLUDED.completeness_score,
                        processing_status = CASE 
                            WHEN crawler.raw_events.processing_status = 'verified' THEN 'pending_review'
                            ELSE 'pending'
                        END,
                        migrated_to_d1 = FALSE
                    WHERE crawler.raw_events.crawl_status != 'error'
                    RETURNING id, (xmax = 0) as is_insert
                """, 
                    event.get('source_name'),
                    event.get('source_url'),
                    event.get('source_id'),
                    event.get('crawl_batch_id'),
                    event.get('raw_title'),
                    event.get('raw_description'),
                    event.get('raw_date_text'),
                    event.get('raw_time_text'),
                    event.get('raw_location_text'),
                    event.get('raw_price_text'),
                    event.get('raw_image_urls', []),
                    event.get('raw_category_text'),
                    event.get('raw_organizer'),
                    event.get('raw_contact_info'),
                    event.get('parsed_start_date'),
                    event.get('parsed_start_time'),
                    event.get('parsed_end_date'),
                    event.get('parsed_end_time'),
                    event.get('parsed_venue_name'),
                    event.get('parsed_address'),
                    event.get('parsed_city', 'Hyderabad'),
                    event.get('parsed_latitude'),
                    event.get('parsed_longitude'),
                    event.get('parsed_is_free'),
                    event.get('parsed_price_min'),
                    event.get('parsed_price_max'),
                    event.get('parsed_currency', 'INR'),
                    event.get('parsed_age_limit'),
                    event.get('crawl_status', 'success'),
                    event.get('http_status', 200),
                    completeness,
                    'pending'
                )
                
                if row:
                    event_id = row['id']
                    is_insert = row['is_insert']
                    
                    if is_insert:
                        self.logger.debug(f"Inserted new event {event_id}")
                        return event_id
                    else:
                        self.logger.debug(f"Updated existing event {event_id}")
                        return None
                
            except Exception as e:
                self.logger.error(f"Error storing event: {e}", event=event)
                raise
    
    async def update_batch_stats(self, batch_id: str, stats: Dict[str, int]):
        """
        Update crawl batch statistics
        
        Args:
            batch_id: UUID of crawl batch
            stats: Dictionary with found, added, updated, errors counts
        """
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE crawler.crawl_batches
                SET events_found = $1,
                    events_added = $2,
                    events_updated = $3,
                    errors_count = $4,
                    completed_at = CURRENT_TIMESTAMP,
                    status = 'completed'
                WHERE id = $5
            """, 
                stats.get('found', 0),
                stats.get('added', 0),
                stats.get('updated', 0),
                stats.get('errors', 0),
                batch_id
            )
            self.logger.info(f"Updated batch {batch_id} stats", stats=stats)
    
    async def get_pending_verification(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get events pending verification
        
        Args:
            limit: Maximum events to return
            
        Returns:
            List of event dictionaries
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM crawler.raw_events
                WHERE processing_status = 'pending'
                  AND crawl_status = 'success'
                  AND migrated_to_d1 = FALSE
                ORDER BY completeness_score DESC, crawl_timestamp DESC
                LIMIT $1
            """, limit)
            return [dict(row) for row in rows]
    
    async def get_source_config(self, source_name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a source
        
        Args:
            source_name: Name of the source
            
        Returns:
            Configuration dictionary or None
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM crawler.source_configs WHERE source_name = $1",
                source_name
            )
            return dict(row) if row else None
    
    async def get_all_active_sources(self) -> List[Dict[str, Any]]:
        """
        Get all active source configurations
        
        Returns:
            List of source configuration dictionaries
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM crawler.source_configs WHERE is_active = TRUE ORDER BY source_name"
            )
            return [dict(row) for row in rows]
    
    async def update_source_last_crawl(self, source_name: str, events_found: int = 0, error: Optional[str] = None):
        """
        Update source last crawl timestamp
        
        Args:
            source_name: Name of source
            events_found: Number of events found
            error: Error message if crawl failed
        """
        async with self.pool.acquire() as conn:
            if error:
                await conn.execute("""
                    UPDATE crawler.source_configs
                    SET last_crawled_at = CURRENT_TIMESTAMP,
                        last_error_at = CURRENT_TIMESTAMP,
                        last_error_message = $1,
                        total_crawls = total_crawls + 1
                    WHERE source_name = $2
                """, error, source_name)
            else:
                await conn.execute("""
                    UPDATE crawler.source_configs
                    SET last_crawled_at = CURRENT_TIMESTAMP,
                        last_error_at = NULL,
                        last_error_message = NULL,
                        total_crawls = total_crawls + 1,
                        total_events_found = total_events_found + $1
                    WHERE source_name = $2
                """, events_found, source_name)
    
    def _calculate_completeness(self, event: Dict[str, Any]) -> int:
        """Calculate completeness score for an event"""
        score = 0
        
        # Required fields (70 points)
        if event.get('raw_title'):
            score += 30
        if event.get('raw_date_text'):
            score += 20
        if event.get('raw_location_text'):
            score += 20
        
        # Optional fields (30 points)
        if event.get('raw_description'):
            score += 10
        if event.get('raw_time_text'):
            score += 5
        if event.get('raw_price_text'):
            score += 5
        if event.get('raw_image_urls'):
            score += 10
        
        return min(score, 100)
