"""Constants for the Portfolio Tracker integration."""
from __future__ import annotations

from typing import Final

from homeassistant.const import Platform

DOMAIN: Final = "portfolio_tracker"

# Platforms
PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

# Configuration constants - InfluxDB v1 for HA Add-on compatibility
CONF_INFLUXDB_URL: Final = "influxdb_url"
CONF_INFLUXDB_USERNAME: Final = "influxdb_username"
CONF_INFLUXDB_PASSWORD: Final = "influxdb_password"
CONF_INFLUXDB_DATABASE: Final = "influxdb_database"
CONF_GOOGLE_SHEETS_ID: Final = "google_sheets_id"
CONF_GOOGLE_CREDENTIALS_JSON: Final = "google_credentials_json"
CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_AUTO_SYNC_SHEETS: Final = "auto_sync_sheets"

# Default values
DEFAULT_SCAN_INTERVAL: Final = 30  # minutes
DEFAULT_TIMEOUT: Final = 30  # seconds
DEFAULT_INFLUXDB_URL: Final = "http://homeassistant.local:8086"
DEFAULT_SHEET_RANGE: Final = "A1:Z3000"  # Default range for Google Sheets

# Service names
SERVICE_UPDATE_DATA: Final = "update_data"
SERVICE_RUN_ANALYTICS: Final = "run_analytics"
SERVICE_GET_STATUS: Final = "get_status"

# Events
EVENT_PORTFOLIO_UPDATED: Final = "portfolio_tracker_updated"
EVENT_ANALYTICS_COMPLETED: Final = "portfolio_analytics_completed"
EVENT_STATUS_RETRIEVED: Final = "portfolio_status_retrieved"

# Error codes for better error handling
ERROR_CODES = {
    "INFLUXDB_CONNECTION_FAILED": "Failed to connect to InfluxDB",
    "INFLUXDB_AUTH_FAILED": "InfluxDB authentication failed",
    "INFLUXDB_DATABASE_NOT_FOUND": "InfluxDB database not found",
    "GOOGLE_CREDENTIALS_INVALID": "Invalid Google service account credentials",
    "GOOGLE_CREDENTIALS_MISSING_FIELDS": "Missing required fields in Google credentials", 
    "GOOGLE_SHEETS_ACCESS_DENIED": "Access denied to Google Sheets",
    "GOOGLE_SHEETS_NOT_FOUND": "Google Sheets document not found",
    "DATA_SYNC_FAILED": "Failed to sync data from Google Sheets to InfluxDB",
    "DATA_FORMAT_INVALID": "Invalid data format in Google Sheets",
    "CONFIGURATION_INCOMPLETE": "Configuration is incomplete",
}

# Entity types
SENSOR_TYPES = {
    "portfolio_value": {
        "name": "Portfolio Value",
        "icon": "mdi:currency-usd",
        "unit": "$",
        "device_class": "monetary",
    },
    "daily_change": {
        "name": "Daily Change",
        "icon": "mdi:trending-up",
        "unit": "$",
        "device_class": "monetary",
    },
    "daily_change_percent": {
        "name": "Daily Change Percent",
        "icon": "mdi:percent",
        "unit": "%",
    },
    "total_positions": {
        "name": "Total Positions",
        "icon": "mdi:format-list-numbered",
    },
    "last_update": {
        "name": "Last Update",
        "icon": "mdi:clock",
        "device_class": "timestamp",
    },
}

BINARY_SENSOR_TYPES = {
    "data_source_health": {
        "name": "Data Source Health",
        "icon": "mdi:database",
        "device_class": "connectivity",
    },
    "influxdb_connected": {
        "name": "InfluxDB Connected",
        "icon": "mdi:database-check",
        "device_class": "connectivity",
    },
    "google_sheets_connected": {
        "name": "Google Sheets Connected",
        "icon": "mdi:google",
        "device_class": "connectivity",
    },
}

# Column mapping for Google Sheets flexibility
DEFAULT_COLUMN_MAPPING = {
    "symbol": ["symbol", "ticker", "stock"],
    "quantity": ["quantity", "shares", "amount"],
    "price": ["price", "current_price", "unit_price"],
    "value": ["value", "market_value", "total_value"],
    "change": ["change", "daily_change", "day_change"],
}