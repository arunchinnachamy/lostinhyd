"""
Venue extraction utilities
"""

import re
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger("crawler.venue_extractor")


class VenueExtractor:
    """Extract and normalize venue information"""
    
    # Common Hyderabad areas/neighborhoods
    HYDERABAD_AREAS = [
        'banjara hills', 'jubilee hills', 'hitech city', 'gachibowli',
        'madhapur', 'kondapur', 'kukatpally', 'secunderabad', 'begumpet',
        'somajiguda', 'punjagutta', 'ameerpet', 'sr nagar', 'nagarjuna hills',
        'film nagar', 'road no', 'rd no', 'kbr park', 'masab tank',
        'tolichowki', 'mehdipatnam', 'charminar', 'old city', 'uppal',
        'lb nagar', 'dilsukhnagar', 'koti', 'abids', 'basheerbagh',
        'himayatnagar', 'necklace road', 'cyber towers', 'inorbit mall',
        'forum mall', 'gvk one', 'irrnm', ' Mindspace'
    ]
    
    # Common venue types
    VENUE_TYPES = [
        'stadium', 'arena', 'auditorium', 'hall', 'center', 'centre',
        'club', 'lounge', 'bar', 'pub', 'restaurant', 'cafe', 'hotel',
        'theater', 'theatre', 'cinema', 'multiplex', 'mall', 'park',
        'ground', 'convention centre', 'convention center', 'exhibition centre'
    ]
    
    @classmethod
    def extract_venue(cls, location_text: str) -> Dict[str, Any]:
        """
        Extract venue information from location text
        
        Args:
            location_text: Raw location text
            
        Returns:
            Dictionary with venue_name, address, area, city
        """
        if not location_text:
            return {
                'venue_name': None,
                'address': None,
                'area': None,
                'city': 'Hyderabad'
            }
        
        location_text = location_text.strip()
        
        # Split by common separators
        parts = re.split(r'[,;\n-]', location_text)
        parts = [p.strip() for p in parts if p.strip()]
        
        venue_name = None
        address = None
        area = None
        city = 'Hyderabad'
        
        if len(parts) >= 1:
            venue_name = parts[0]
        
        if len(parts) >= 2:
            # Last part might be city
            if 'hyderabad' in parts[-1].lower() or 'secunderabad' in parts[-1].lower():
                city = parts[-1]
                address = ', '.join(parts[1:-1]) if len(parts) > 2 else None
            else:
                address = ', '.join(parts[1:])
        
        # Extract area from venue name or address
        area = cls._extract_area(location_text)
        
        return {
            'venue_name': venue_name,
            'address': address,
            'area': area,
            'city': city
        }
    
    @classmethod
    def _extract_area(cls, text: str) -> Optional[str]:
        """Extract area/neighborhood from text"""
        text_lower = text.lower()
        
        for area in cls.HYDERABAD_AREAS:
            if area.lower() in text_lower:
                return area.title()
        
        # Try to extract from address patterns
        # e.g., "Road No. 12, Banjara Hills"
        road_pattern = r'road no\.?\s*\d+,?\s*([^,]+)'
        match = re.search(road_pattern, text, re.IGNORECASE)
        if match:
            potential_area = match.group(1).strip()
            if len(potential_area) > 3:
                return potential_area.title()
        
        return None
    
    @classmethod
    def clean_venue_name(cls, name: str) -> str:
        """Clean and normalize venue name"""
        if not name:
            return name
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Remove common suffixes/prefixes that aren't part of the name
        prefixes_to_remove = [
            r'^[\s\-:]+',  # Leading punctuation
            r'\(.*\)$',    # Trailing parenthetical
        ]
        
        for pattern in prefixes_to_remove:
            name = re.sub(pattern, '', name).strip()
        
        return name.title()
