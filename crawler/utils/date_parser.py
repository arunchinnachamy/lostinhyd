"""
Date parsing utilities for various date formats
"""

from datetime import datetime, date, time
from typing import Optional, Tuple
import re
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger("crawler.date_parser")


class DateParser:
    """Parse various date formats commonly found on event sites"""
    
    # Common patterns
    DATE_PATTERNS = [
        # 15 Jan 2026, 15 January 2026
        (r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b', 'dmy'),
        # Jan 15 2026, January 15 2026
        (r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{1,2})[,]?\s+(\d{4})\b', 'mdy'),
        # 15/01/2026, 15-01-2026
        (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', 'dmy_numeric'),
        # 2026-01-15 (ISO)
        (r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', 'ymd'),
        # Today, Tomorrow
        (r'\b(Today|Tomorrow)\b', 'relative'),
        # This weekend, Next weekend
        (r'\b(This|Next)\s+(weekend|week|month)\b', 'relative'),
    ]
    
    MONTH_MAP = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12,
    }
    
    @classmethod
    def parse_date(cls, date_text: str, reference_date: Optional[date] = None) -> Optional[date]:
        """
        Parse a date string into a date object
        
        Args:
            date_text: Raw date text
            reference_date: Reference date for relative dates (default: today)
            
        Returns:
            Parsed date or None
        """
        if not date_text:
            return None
        
        if reference_date is None:
            reference_date = date.today()
        
        date_text = date_text.strip().lower()
        
        # Try pattern matching first
        for pattern, pattern_type in cls.DATE_PATTERNS:
            match = re.search(pattern, date_text, re.IGNORECASE)
            if match:
                try:
                    if pattern_type == 'dmy':
                        day, month_str, year = match.groups()
                        month = cls.MONTH_MAP.get(month_str.lower())
                        if month:
                            return date(int(year), month, int(day))
                    
                    elif pattern_type == 'mdy':
                        month_str, day, year = match.groups()
                        month = cls.MONTH_MAP.get(month_str.lower())
                        if month:
                            return date(int(year), month, int(day))
                    
                    elif pattern_type == 'dmy_numeric':
                        day, month, year = map(int, match.groups())
                        return date(year, month, day)
                    
                    elif pattern_type == 'ymd':
                        year, month, day = map(int, match.groups())
                        return date(year, month, day)
                    
                    elif pattern_type == 'relative':
                        return cls._parse_relative_date(match.group(), reference_date)
                
                except ValueError as e:
                    logger.warning(f"Failed to parse date with pattern {pattern_type}: {e}")
        
        # Fallback to dateutil parser
        try:
            parsed = date_parser.parse(date_text, default=datetime(reference_date.year, 1, 1))
            return parsed.date()
        except Exception as e:
            logger.warning(f"dateutil failed to parse '{date_text}': {e}")
        
        return None
    
    @classmethod
    def _parse_relative_date(cls, relative_text: str, reference_date: date) -> Optional[date]:
        """Parse relative dates like 'today', 'tomorrow', 'this weekend'"""
        relative_text = relative_text.lower().strip()
        
        if 'today' in relative_text:
            return reference_date
        
        if 'tomorrow' in relative_text:
            return reference_date + relativedelta(days=1)
        
        if 'this weekend' in relative_text:
            # Next Saturday
            days_until_sat = (5 - reference_date.weekday()) % 7
            if days_until_sat == 0:  # If today is Saturday, go to next Saturday
                days_until_sat = 7
            return reference_date + relativedelta(days=days_until_sat)
        
        if 'next weekend' in relative_text:
            days_until_sat = (5 - reference_date.weekday()) % 7
            return reference_date + relativedelta(days=days_until_sat + 7)
        
        if 'this week' in relative_text:
            return reference_date
        
        if 'next week' in relative_text:
            return reference_date + relativedelta(weeks=1)
        
        if 'this month' in relative_text:
            return reference_date
        
        if 'next month' in relative_text:
            return reference_date + relativedelta(months=1)
        
        return None
    
    @classmethod
    def parse_time(cls, time_text: str) -> Optional[time]:
        """
        Parse a time string
        
        Args:
            time_text: Raw time text
            
        Returns:
            Parsed time or None
        """
        if not time_text:
            return None
        
        time_text = time_text.strip().lower()
        
        # Common patterns
        # 6:00 PM, 18:00, 6 PM, 6pm
        patterns = [
            r'(\d{1,2}):(\d{2})\s*(am|pm)',
            r'(\d{1,2})\s*(am|pm)',
            r'(\d{1,2}):(\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, time_text)
            if match:
                try:
                    groups = match.groups()
                    
                    if len(groups) == 3:  # HH:MM AM/PM
                        hour, minute, ampm = groups
                        hour = int(hour)
                        minute = int(minute)
                        if ampm == 'pm' and hour != 12:
                            hour += 12
                        elif ampm == 'am' and hour == 12:
                            hour = 0
                        return time(hour, minute)
                    
                    elif len(groups) == 2:
                        if groups[1] in ['am', 'pm']:  # HH AM/PM
                            hour, ampm = groups
                            hour = int(hour)
                            if ampm == 'pm' and hour != 12:
                                hour += 12
                            elif ampm == 'am' and hour == 12:
                                hour = 0
                            return time(hour, 0)
                        else:  # HH:MM
                            hour, minute = map(int, groups)
                            return time(hour, minute)
                
                except ValueError:
                    pass
        
        # Fallback to dateutil
        try:
            parsed = date_parser.parse(time_text)
            return parsed.time()
        except Exception:
            pass
        
        return None
    
    @classmethod
    def parse_date_range(cls, date_text: str) -> Tuple[Optional[date], Optional[date]]:
        """
        Parse a date range (e.g., "15-17 Jan 2026")
        
        Returns:
            Tuple of (start_date, end_date) or (None, None)
        """
        if not date_text:
            return None, None
        
        # Pattern: 15-17 Jan 2026 or 15 to 17 Jan 2026
        range_pattern = r'(\d{1,2})\s*[-to]+\s*(\d{1,2})\s+([A-Za-z]+)\s*(\d{4})?'
        match = re.search(range_pattern, date_text, re.IGNORECASE)
        
        if match:
            start_day, end_day, month_str, year = match.groups()
            year = year or str(date.today().year)
            month = cls.MONTH_MAP.get(month_str.lower())
            
            if month:
                try:
                    start_date = date(int(year), month, int(start_day))
                    end_date = date(int(year), month, int(end_day))
                    return start_date, end_date
                except ValueError:
                    pass
        
        # Single date
        single_date = cls.parse_date(date_text)
        return single_date, None
