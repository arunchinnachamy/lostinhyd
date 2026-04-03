"""
Base crawler module - Abstract base class for all event crawlers
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging
import hashlib
from datetime import datetime


class BaseCrawler(ABC):
    """Abstract base class for all event crawlers"""
    
    def __init__(self, source_name: str, config: Dict[str, Any], data_store=None):
        self.source_name = source_name
        self.config = config
        self.data_store = data_store
        self.logger = logging.getLogger(f"crawler.{source_name}")
        self.stats = {
            'found': 0,
            'added': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
    
    @abstractmethod
    async def fetch_events(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch raw events from source"""
        pass
    
    @abstractmethod
    def parse_event(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse raw data into structured format"""
        pass
    
    def generate_source_id(self, raw_data: Dict[str, Any]) -> str:
        """Generate unique source ID for deduplication"""
        # Default implementation uses hash of title + date
        title = raw_data.get('title', '')
        date = raw_data.get('date', '')
        unique_string = f"{self.source_name}:{title}:{date}"
        return hashlib.sha256(unique_string.encode()).hexdigest()[:16]
    
    async def crawl(self, batch_id: str, **kwargs) -> Dict[str, int]:
        """Main crawl method"""
        self.logger.info(f"Starting crawl for {self.source_name} [batch={batch_id}]")
        self.stats = {k: 0 for k in self.stats}  # Reset stats
        
        try:
            # Fetch raw events
            raw_events = await self.fetch_events(**kwargs)
            self.logger.info(f"Fetched {len(raw_events)} raw events")
            
            for raw in raw_events:
                try:
                    # Parse event
                    parsed = self.parse_event(raw)
                    if not parsed:
                        self.stats['skipped'] += 1
                        continue
                    
                    # Add metadata
                    parsed['source_name'] = self.source_name
                    parsed['crawl_batch_id'] = batch_id
                    parsed['source_id'] = self.generate_source_id(raw)
                    
                    # Store in database
                    if self.data_store:
                        event_id = await self.data_store.store_raw_event(parsed)
                        if event_id:
                            self.stats['added'] += 1
                        else:
                            self.stats['updated'] += 1
                    
                    self.stats['found'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error parsing event: {e} [raw={raw}]")
                    self.stats['errors'] += 1
            
            self.logger.info(f"Crawl completed: {self.stats}")
            return self.stats
            
        except Exception as e:
            self.logger.error(f"Crawl failed: {e}")
            raise
    
    def _calculate_quality_scores(self, event: Dict[str, Any]) -> Dict[str, int]:
        """Calculate data quality scores for an event"""
        scores = {
            'completeness': 0,
            'accuracy': 0,
            'confidence': 0
        }
        
        # Completeness score (fields filled)
        required_fields = ['raw_title', 'raw_date_text', 'raw_location_text']
        optional_fields = ['raw_description', 'raw_price_text', 'raw_time_text', 'raw_image_urls']
        
        required_filled = sum(1 for f in required_fields if event.get(f))
        optional_filled = sum(1 for f in optional_fields if event.get(f))
        
        scores['completeness'] = int(
            (required_filled / len(required_fields) * 70) + 
            (optional_filled / len(optional_fields) * 30)
        )
        
        # Accuracy score (basic validations)
        validations = [
            len(event.get('raw_title', '')) >= 5,
            len(event.get('raw_description', '')) >= 20,
            event.get('parsed_start_date') is not None,
            event.get('parsed_price_min', 0) >= 0
        ]
        scores['accuracy'] = int(sum(validations) / len(validations) * 100)
        
        # Confidence score (source-specific)
        source_weights = {
            'bookmyshow': 95,
            'meetup': 90,
            'eventshigh': 85,
            'allevents': 80,
            'townscript': 80,
            'fullhyderabad': 75
        }
        scores['confidence'] = source_weights.get(self.source_name, 70)
        
        return scores
