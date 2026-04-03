"""
Data cleaning pipeline for raw crawled events
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
import re
from datetime import datetime, date

from utils.date_parser import DateParser
from utils.price_parser import PriceParser
from utils.venue_extractor import VenueExtractor

logger = logging.getLogger("crawler.cleaning.data_cleaner")


class DataCleaner:
    """Clean and normalize raw crawled event data"""
    
    def __init__(self):
        self.venue_cache = {}  # Cache venue extractions
    
    def clean_event(self, raw_event: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
        """
        Clean a raw event and return cleaned data + list of issues
        
        Args:
            raw_event: Raw event dictionary from raw_events table
            
        Returns:
            Tuple of (cleaned_event, list_of_issues)
        """
        issues = []
        cleaned = dict(raw_event)  # Copy original
        
        # 1. Clean title
        cleaned['raw_title'] = self._clean_text(raw_event.get('raw_title', ''))
        if len(cleaned['raw_title']) < 5:
            issues.append("Title too short")
        
        # 2. Parse and validate date
        if raw_event.get('raw_date_text'):
            try:
                start_date, end_date = DateParser.parse_date_range(raw_event['raw_date_text'])
                cleaned['parsed_start_date'] = start_date
                cleaned['parsed_end_date'] = end_date
                
                if start_date and start_date < date.today():
                    issues.append("Event date is in the past")
                
            except Exception as e:
                issues.append(f"Date parsing failed: {e}")
        else:
            issues.append("No date information")
        
        # 3. Parse time
        if raw_event.get('raw_time_text'):
            parsed_time = DateParser.parse_time(raw_event['raw_time_text'])
            cleaned['parsed_start_time'] = parsed_time
        
        # 4. Clean and extract venue
        if raw_event.get('raw_location_text'):
            venue_info = VenueExtractor.extract_venue(raw_event['raw_location_text'])
            cleaned['parsed_venue_name'] = venue_info['venue_name']
            cleaned['parsed_address'] = venue_info['address']
            cleaned['parsed_area'] = venue_info['area']
            cleaned['parsed_city'] = venue_info['city']
        else:
            issues.append("No venue information")
        
        # 5. Parse price
        if raw_event.get('raw_price_text'):
            price_min, price_max, is_free, currency = PriceParser.parse_price(
                raw_event['raw_price_text']
            )
            cleaned['parsed_price_min'] = price_min
            cleaned['parsed_price_max'] = price_max
            cleaned['parsed_is_free'] = is_free
            cleaned['parsed_currency'] = currency
        
        # 6. Clean description
        if raw_event.get('raw_description'):
            cleaned['raw_description'] = self._clean_html(raw_event['raw_description'])
        
        # 7. Clean images
        if raw_event.get('raw_image_urls'):
            cleaned['raw_image_urls'] = [
                url for url in raw_event['raw_image_urls']
                if url and url.startswith('http')
            ]
        
        # 8. Calculate updated quality scores
        scores = self._calculate_quality_scores(cleaned)
        cleaned['completeness_score'] = scores['completeness']
        cleaned['accuracy_score'] = scores['accuracy']
        cleaned['confidence_score'] = scores['confidence']
        
        return cleaned, issues
    
    def _clean_text(self, text: str) -> str:
        """Clean text fields"""
        if not text:
            return text
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\-\'\.&,!?()]', '', text)
        
        return text.strip()
    
    def _clean_html(self, html: str) -> str:
        """Clean HTML from description"""
        if not html:
            return html
        
        # Remove script and style tags
        html = re.sub(r'<(script|style)[^>]*>[^<]*</\1>', '', html, flags=re.IGNORECASE)
        
        # Replace common HTML entities
        html = html.replace('&nbsp;', ' ')
        html = html.replace('&amp;', '&')
        html = html.replace('&lt;', '<')
        html = html.replace('&gt;', '>')
        html = html.replace('&quot;', '"')
        
        # Remove remaining HTML tags
        html = re.sub(r'<[^>]+>', ' ', html)
        
        # Clean up whitespace
        html = ' '.join(html.split())
        
        return html.strip()
    
    def _calculate_quality_scores(self, event: Dict[str, Any]) -> Dict[str, int]:
        """Calculate quality scores for cleaned event"""
        scores = {
            'completeness': 0,
            'accuracy': 0,
            'confidence': 0
        }
        
        # Completeness - required fields
        required = ['raw_title', 'parsed_start_date', 'parsed_venue_name']
        optional = ['raw_description', 'parsed_start_time', 'parsed_price_min', 'raw_image_urls']
        
        required_filled = sum(1 for f in required if event.get(f))
        optional_filled = sum(1 for f in optional if event.get(f))
        
        scores['completeness'] = int(
            (required_filled / len(required) * 70) +
            (optional_filled / len(optional) * 30)
        )
        
        # Accuracy - basic validations
        validations = [
            len(str(event.get('raw_title', ''))) >= 5,
            len(str(event.get('raw_description', ''))) >= 20 if event.get('raw_description') else True,
            event.get('parsed_start_date') is not None,
            event.get('parsed_price_min', 0) >= 0 if event.get('parsed_price_min') else True
        ]
        scores['accuracy'] = int(sum(validations) / len(validations) * 100)
        
        # Confidence based on source
        source_weights = {
            'bookmyshow': 95,
            'meetup': 90,
            'eventshigh': 85,
            'allevents': 80,
            'townscript': 80,
            'fullhyderabad': 75
        }
        scores['confidence'] = source_weights.get(event.get('source_name'), 70)
        
        return scores
    
    def should_auto_verify(self, event: Dict[str, Any]) -> bool:
        """Determine if event should be auto-verified based on scores"""
        completeness = event.get('completeness_score', 0)
        accuracy = event.get('accuracy_score', 0)
        confidence = event.get('confidence_score', 0)
        
        # Auto-verify if all scores are high
        if completeness >= 80 and accuracy >= 90 and confidence >= 85:
            return True
        
        # Auto-reject if too low quality
        if completeness < 40 or accuracy < 50:
            return False
        
        # Otherwise needs manual review
        return False
