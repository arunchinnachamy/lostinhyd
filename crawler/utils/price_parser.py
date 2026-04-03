"""
Price parsing utilities
"""

import re
from typing import Optional, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger("crawler.price_parser")


class PriceParser:
    """Parse price information from various formats"""
    
    @staticmethod
    def parse_price(price_text: str) -> Tuple[Optional[Decimal], Optional[Decimal], bool, str]:
        """
        Parse price text and return (min_price, max_price, is_free, currency)
        
        Args:
            price_text: Raw price text
            
        Returns:
            Tuple of (min_price, max_price, is_free, currency)
        """
        if not price_text:
            return None, None, False, 'INR'
        
        price_text = price_text.strip()
        
        # Check for free events
        free_keywords = ['free', 'gratis', 'no charge', 'complimentary', 'rsvp']
        if any(keyword in price_text.lower() for keyword in free_keywords):
            return Decimal('0'), Decimal('0'), True, 'INR'
        
        # Determine currency
        currency = 'INR'  # Default
        if '$' in price_text or 'usd' in price_text.lower():
            currency = 'USD'
        elif '€' in price_text or 'eur' in price_text.lower():
            currency = 'EUR'
        elif '£' in price_text or 'gbp' in price_text.lower():
            currency = 'GBP'
        
        # Extract all numbers that look like prices
        # Patterns: ₹500, Rs. 500, INR 500, 500/-, 500/- onwards
        price_pattern = r'(?:₹|Rs\.?|INR)?\s*(\d{1,6}(?:,\d{3})*(?:\.\d{2})?)'
        matches = re.findall(price_pattern, price_text.replace(',', ''))
        
        if not matches:
            return None, None, False, currency
        
        # Parse numbers
        prices = []
        for match in matches:
            try:
                price = Decimal(str(match))
                if price > 0:
                    prices.append(price)
            except:
                pass
        
        if not prices:
            return None, None, False, currency
        
        # Determine min and max
        if len(prices) == 1:
            return prices[0], prices[0], False, currency
        else:
            return min(prices), max(prices), False, currency
    
    @staticmethod
    def format_price(price_min: Optional[Decimal], price_max: Optional[Decimal], 
                     is_free: bool, currency: str = 'INR') -> str:
        """Format price for display"""
        if is_free:
            return 'Free'
        
        currency_symbols = {
            'INR': '₹',
            'USD': '$',
            'EUR': '€',
            'GBP': '£'
        }
        symbol = currency_symbols.get(currency, currency)
        
        if price_min is None and price_max is None:
            return 'Price TBA'
        
        if price_min == price_max:
            return f"{symbol}{price_min}"
        
        if price_min is not None and price_max is not None:
            return f"{symbol}{price_min} - {symbol}{price_max}"
        
        if price_min is not None:
            return f"From {symbol}{price_min}"
        
        return f"Up to {symbol}{price_max}"
