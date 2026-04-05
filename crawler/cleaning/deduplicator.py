"""
Event deduplication module
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from difflib import SequenceMatcher

logger = logging.getLogger("crawler.cleaning.deduplicator")


class EventDeduplicator:
    """Find and handle duplicate events"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.similarity_threshold = similarity_threshold
    
    def find_duplicates(self, new_event: Dict[str, Any], 
                       existing_events: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], float]]:
        """
        Find potential duplicates of new_event in existing_events
        
        Args:
            new_event: Event to check
            existing_events: List of existing events to compare against
            
        Returns:
            List of (existing_event, similarity_score) tuples
        """
        duplicates = []
        
        for existing in existing_events:
            similarity = self._calculate_similarity(new_event, existing)
            
            if similarity >= self.similarity_threshold:
                duplicates.append((existing, similarity))
            
            # Also check exact match on source_id
            if (new_event.get('source_name') == existing.get('source_name') and
                new_event.get('source_id') == existing.get('source_id')):
                duplicates.append((existing, 1.0))
        
        # Sort by similarity (highest first)
        duplicates.sort(key=lambda x: x[1], reverse=True)
        
        return duplicates
    
    def _calculate_similarity(self, event1: Dict[str, Any], 
                              event2: Dict[str, Any]) -> float:
        """Calculate similarity score between two events"""
        scores = []
        
        # Title similarity (most important)
        title1 = event1.get('raw_title', '').lower()
        title2 = event2.get('raw_title', '').lower()
        if title1 and title2:
            title_sim = SequenceMatcher(None, title1, title2).ratio()
            scores.append(title_sim * 0.5)  # 50% weight
        
        # Date similarity
        date1 = event1.get('parsed_start_date')
        date2 = event2.get('parsed_start_date')
        if date1 and date2:
            if date1 == date2:
                scores.append(0.3)  # 30% weight for same date
            else:
                scores.append(0.0)
        
        # Venue similarity
        venue1 = (event1.get('parsed_venue_name') or '').lower()
        venue2 = (event2.get('parsed_venue_name') or '').lower()
        if venue1 and venue2:
            venue_sim = SequenceMatcher(None, venue1, venue2).ratio()
            scores.append(venue_sim * 0.2)  # 20% weight
        
        return sum(scores) if scores else 0.0
    
    def merge_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple duplicate events into one, keeping best data from each
        
        Args:
            events: List of duplicate events
            
        Returns:
            Merged event with best fields
        """
        if not events:
            return {}
        
        if len(events) == 1:
            return events[0]
        
        # Start with first event
        merged = dict(events[0])
        
        # Track all source URLs
        all_sources = set()
        
        for event in events:
            # Prefer longer/more complete descriptions
            if len(str(event.get('raw_description', ''))) > len(str(merged.get('raw_description', ''))):
                merged['raw_description'] = event['raw_description']
            
            # Prefer more images
            if len(event.get('raw_image_urls', [])) > len(merged.get('raw_image_urls', [])):
                merged['raw_image_urls'] = event['raw_image_urls']
            
            # Prefer lower prices
            if event.get('parsed_price_min') and merged.get('parsed_price_min'):
                if event['parsed_price_min'] < merged['parsed_price_min']:
                    merged['parsed_price_min'] = event['parsed_price_min']
            
            # Track sources
            all_sources.add((event.get('source_name'), event.get('source_url')))
        
        # Store duplicate info
        merged['duplicate_sources'] = list(all_sources)
        merged['processing_notes'] = f"Merged from {len(events)} duplicate sources"
        
        return merged
    
    def select_best_version(self, duplicates: List[Tuple[Dict[str, Any], float]]) -> Dict[str, Any]:
        """
        Select the best version from duplicates based on quality scores
        
        Args:
            duplicates: List of (event, similarity) tuples
            
        Returns:
            Best event
        """
        if not duplicates:
            return None
        
        if len(duplicates) == 1:
            return duplicates[0][0]
        
        # Sort by quality score
        def quality_score(item):
            event = item[0]
            return (
                event.get('completeness_score', 0) +
                event.get('accuracy_score', 0) +
                event.get('confidence_score', 0)
            )
        
        duplicates.sort(key=quality_score, reverse=True)
        
        return duplicates[0][0]
