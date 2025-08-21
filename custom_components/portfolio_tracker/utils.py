"""Utility functions for Portfolio Tracker integration."""
from __future__ import annotations

import logging
from typing import Tuple
from urllib.parse import urlparse

_LOGGER = logging.getLogger(__name__)


def parse_influxdb_url(url: str) -> Tuple[str, int, bool]:
    """Parse InfluxDB URL and return host, port, and SSL status.
    
    Args:
        url: The InfluxDB URL to parse
        
    Returns:
        Tuple of (host, port, ssl_enabled)
        
    Raises:
        ValueError: If URL format is invalid
    """
    if not url:
        raise ValueError("URL cannot be empty")
    
    try:
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            # Default to http if no scheme specified
            url = f"http://{url}"
        
        parsed = urlparse(url)
        
        if not parsed.hostname:
            raise ValueError(f"Invalid hostname in URL: {url}")
        
        host = parsed.hostname
        
        # Determine port
        if parsed.port:
            port = parsed.port
        else:
            # Default ports
            port = 8086 if parsed.scheme == 'http' else 8086
        
        # Determine SSL
        ssl = parsed.scheme == 'https'
        
        _LOGGER.debug("Parsed URL %s -> host=%s, port=%d, ssl=%s", url, host, port, ssl)
        
        return host, port, ssl
        
    except Exception as e:
        _LOGGER.error("Failed to parse URL %s: %s", url, e)
        raise ValueError(f"Invalid URL format: {url}") from e


def validate_google_sheets_id(sheets_id: str) -> bool:
    """Validate Google Sheets ID format.
    
    Args:
        sheets_id: The Google Sheets ID to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not sheets_id:
        return False
    
    # Google Sheets ID should be alphanumeric with some special chars
    # Typical format: 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
    if len(sheets_id) < 40 or len(sheets_id) > 60:
        return False
    
    # Should contain only alphanumeric characters, hyphens, and underscores
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_')
    return all(c in allowed_chars for c in sheets_id)


def sanitize_entity_name(name: str) -> str:
    """Sanitize entity name to be HA compliant.
    
    Args:
        name: The name to sanitize
        
    Returns:
        Sanitized name suitable for HA entities
    """
    if not name:
        return "unknown"
    
    # Replace spaces and special chars with underscores
    sanitized = ''.join(c if c.isalnum() else '_' for c in name.lower())
    
    # Remove multiple consecutive underscores
    while '__' in sanitized:
        sanitized = sanitized.replace('__', '_')
    
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    
    return sanitized or "unknown"


def format_currency(value: float, currency: str = "USD") -> str:
    """Format currency value for display.
    
    Args:
        value: The numeric value
        currency: Currency code (default: USD)
        
    Returns:
        Formatted currency string
    """
    if value is None:
        return "N/A"
    
    try:
        if currency == "USD":
            return f"${value:,.2f}"
        else:
            return f"{value:,.2f} {currency}"
    except (ValueError, TypeError):
        return str(value)


def format_percentage(value: float) -> str:
    """Format percentage value for display.
    
    Args:
        value: The percentage value (e.g., 0.05 for 5%)
        
    Returns:
        Formatted percentage string
    """
    if value is None:
        return "N/A"
    
    try:
        return f"{value:.2f}%"
    except (ValueError, TypeError):
        return str(value)