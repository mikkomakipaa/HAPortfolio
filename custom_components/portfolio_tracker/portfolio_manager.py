"""Portfolio Manager for Home Assistant integration - InfluxDB v1 for HA Add-on."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_INFLUXDB_URL,
    CONF_INFLUXDB_USERNAME,
    CONF_INFLUXDB_PASSWORD,
    CONF_INFLUXDB_DATABASE,
    CONF_GOOGLE_SHEETS_ID,
    CONF_CREDENTIALS_PATH,
)
from .utils import parse_influxdb_url
from .google_api import GoogleSheetsAPI

_LOGGER = logging.getLogger(__name__)


class PortfolioManager:
    """Manages portfolio data collection and analysis for Home Assistant - InfluxDB v1."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any], config_entry: ConfigEntry = None) -> None:
        """Initialize the portfolio manager."""
        self.hass = hass
        self.config = config
        self.config_entry = config_entry
        self._google_api = None
        
        # Initialize Google Sheets API if configured and config_entry is available
        if config_entry and config.get(CONF_GOOGLE_SHEETS_ID):
            self._google_api = GoogleSheetsAPI(hass, config_entry)
        self._influx_client = None
        self._last_data = None

    def _get_influx_client(self):
        """Get or create InfluxDB v1 client with improved error handling."""
        if self._influx_client is None:
            try:
                from influxdb import InfluxDBClient
                
            except ImportError as e:
                _LOGGER.error("InfluxDB client not available. Please install influxdb package: %s", e)
                raise HomeAssistantError("InfluxDB client library not found. Please check installation.") from e
            
            try:
                # Extract and validate credentials
                username = self.config.get(CONF_INFLUXDB_USERNAME, "").strip()
                password = self.config.get(CONF_INFLUXDB_PASSWORD, "").strip()
                database = self.config.get(CONF_INFLUXDB_DATABASE, "portfolio").strip()
                
                if not username or not password:
                    raise HomeAssistantError("InfluxDB username and password are required")
                
                _LOGGER.debug("Creating InfluxDB v1 client for %s", self.config[CONF_INFLUXDB_URL])
                
                # Parse URL to get host and port
                url = self.config[CONF_INFLUXDB_URL]
                host, port, ssl = parse_influxdb_url(url)
                
                # Create client with improved settings
                self._influx_client = InfluxDBClient(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    database=database,
                    ssl=ssl,
                    verify_ssl=ssl,
                    timeout=30,
                    retries=3
                )
                
                _LOGGER.debug("InfluxDB v1 client created successfully")
                    
            except Exception as e:
                _LOGGER.error("Failed to create InfluxDB v1 client: %s", e)
                self._influx_client = None
                raise HomeAssistantError(f"InfluxDB v1 connection failed: {e}") from e
                
        return self._influx_client

    def test_connection(self) -> bool:
        """Test connection to InfluxDB v1 with improved error handling."""
        try:
            client = self._get_influx_client()
            if not client:
                return False
            
            # Test InfluxDB v1 connection with retry logic
            for attempt in range(3):
                try:
                    client.ping()
                    _LOGGER.info("InfluxDB v1 connection test successful")
                    break
                except Exception as ping_error:
                    if attempt == 2:  # Last attempt
                        raise ping_error
                    _LOGGER.debug("Ping attempt %d failed, retrying: %s", attempt + 1, ping_error)
            
            # Test database access
            database = self.config.get(CONF_INFLUXDB_DATABASE, "portfolio")
            try:
                databases = client.get_list_database()
                db_names = [db['name'] for db in databases]
                if database not in db_names:
                    _LOGGER.warning("Database '%s' not found. Available: %s", database, db_names)
                    # Create database if it doesn't exist
                    try:
                        client.create_database(database)
                        _LOGGER.info("Created database '%s'", database)
                    except Exception as create_error:
                        _LOGGER.warning("Could not create database '%s': %s", database, create_error)
                else:
                    _LOGGER.info("Database '%s' access confirmed", database)
            except Exception as e:
                _LOGGER.warning("Could not verify database access: %s", e)
            
            return True
            
        except Exception as e:
            _LOGGER.error("Connection test failed: %s", e)
            # Reset client on connection failure
            self._influx_client = None
            raise HomeAssistantError(f"Cannot connect to InfluxDB v1: {e}") from e

    async def async_get_google_sheets_data(self) -> dict[str, Any]:
        """Get portfolio data from Google Sheets using HA's Google integration."""
        if not self._google_api:
            return {"connected": False, "data": []}
            
        try:
            sheets_id = self.config.get(CONF_GOOGLE_SHEETS_ID)
            if not sheets_id:
                return {"connected": False, "data": []}
                
            # Test connection first
            connected = await self._google_api.async_test_connection(sheets_id)
            if not connected:
                return {"connected": False, "data": []}
                
            # Get data from the sheet (assuming 'historia' sheet as per your config)
            range_name = "historia!A1:E3000"  # Based on your portfolio_config.yaml
            data = await self._google_api.async_get_sheet_data(sheets_id, range_name)
            
            return {
                "connected": True,
                "data": data or [],
                "last_access": datetime.now().isoformat()
            }
            
        except Exception as e:
            _LOGGER.error(f"Error getting Google Sheets data: {e}")
            return {"connected": False, "data": [], "error": str(e)}

    async def async_get_google_sheets_status(self) -> str:
        """Get Google Sheets connection status."""
        if not self.config.get(CONF_GOOGLE_SHEETS_ID):
            return "not_configured"
            
        if not self._google_api:
            return "not_configured"
            
        try:
            return await self._google_api.async_get_connection_status()
        except Exception as e:
            _LOGGER.debug("Google Sheets status check failed: %s", e)
            return "disconnected"

    def get_portfolio_data(self) -> dict[str, Any]:
        """Get current portfolio data from InfluxDB v1."""
        try:
            client = self._get_influx_client()
            database = self.config.get(CONF_INFLUXDB_DATABASE, "portfolio")
            
            # Initialize default data structure
            portfolio_data = {
                'portfolio_value': 0.0,
                'daily_change': 0.0,
                'daily_change_percent': 0.0,
                'total_positions': 0,
                'last_update': datetime.now().isoformat(),
                'positions': [],
                'data_sources': {
                    'influxdb_connected': False,
                    'google_sheets_connected': False,
                }
            }
            
            # Test InfluxDB connectivity
            try:
                client.ping()
                portfolio_data['data_sources']['influxdb_connected'] = True
            except Exception:
                portfolio_data['data_sources']['influxdb_connected'] = False
            
            # Try to query actual portfolio data
            try:
                # Query for portfolio total value
                value_query = 'SELECT last("total_value") FROM "portfolio"'
                _LOGGER.debug("Executing portfolio value query: %s", value_query)
                
                result = client.query(value_query, database=database)
                points = list(result.get_points())
                
                if points:
                    value = points[0].get('last')
                    if value is not None:
                        portfolio_data['portfolio_value'] = float(value)
                        _LOGGER.debug("Found portfolio value: %s", value)
                
                # Query for daily change (compare last 2 daily values)
                change_query = '''
                SELECT last("total_value") 
                FROM "portfolio" 
                WHERE time > now() - 2d 
                GROUP BY time(1d)
                '''
                
                _LOGGER.debug("Executing daily change query")
                change_result = client.query(change_query, database=database)
                
                values = []
                for point in change_result.get_points():
                    value = point.get('last')
                    if value is not None:
                        values.append(float(value))
                
                if len(values) >= 2:
                    current_value = values[-1]
                    previous_value = values[-2]
                    daily_change = current_value - previous_value
                    daily_change_percent = (daily_change / previous_value * 100) if previous_value > 0 else 0.0
                    
                    portfolio_data['daily_change'] = daily_change
                    portfolio_data['daily_change_percent'] = daily_change_percent
                    
                    _LOGGER.debug("Daily change calculated: %s (%.2f%%)", daily_change, daily_change_percent)
                
                # Query for individual positions
                positions_query = '''
                SELECT last("value"), last("quantity"), last("change") 
                FROM "positions" 
                GROUP BY "symbol"
                '''
                
                _LOGGER.debug("Executing positions query")
                positions_result = client.query(positions_query, database=database)
                
                positions = []
                for series in positions_result:
                    symbol = series.get('tags', {}).get('symbol', 'Unknown')
                    points = list(series.get('points', []))
                    
                    if points:
                        point = points[0]
                        position = {
                            'symbol': symbol,
                            'value': float(point.get('last', 0)) if point.get('last') else 0.0,
                            'quantity': int(point.get('last_1', 0)) if point.get('last_1') else 0,
                            'change': float(point.get('last_2', 0)) if point.get('last_2') else 0.0,
                        }
                        positions.append(position)
                
                portfolio_data['positions'] = positions
                portfolio_data['total_positions'] = len(positions)
                
                _LOGGER.debug("Found %d positions", len(positions))
            
            except Exception as e:
                _LOGGER.warning("Failed to query portfolio data, using defaults: %s", e)
            
            # Check Google Sheets connectivity if configured
            if self.config.get(CONF_GOOGLE_SHEETS_ID) and self._google_api:
                try:
                    # Note: This is a sync method, so we can't call async methods directly
                    # Google Sheets status will be checked in the coordinator
                    portfolio_data['data_sources']['google_sheets_connected'] = False
                except Exception as e:
                    _LOGGER.debug("Google Sheets connectivity check failed: %s", e)
                    portfolio_data['data_sources']['google_sheets_connected'] = False
            
            # Store for future reference
            self._last_data = portfolio_data
            return portfolio_data
            
        except Exception as e:
            _LOGGER.error("Failed to get portfolio data: %s", e)
            return {
                'portfolio_value': 0.0,
                'daily_change': 0.0,
                'daily_change_percent': 0.0,
                'total_positions': 0,
                'last_update': datetime.now().isoformat(),
                'positions': [],
                'data_sources': {
                    'influxdb_connected': False,
                    'google_sheets_connected': False,
                },
                'error': str(e)
            }

    def update_portfolio_data(self) -> bool:
        """Manually trigger portfolio data update from Google Sheets to InfluxDB."""
        try:
            # This method should be called from async context with executor
            _LOGGER.warning("update_portfolio_data called in sync context - use async_update_portfolio_data instead")
            return False
        except Exception as e:
            _LOGGER.error("Failed to update portfolio data: %s", e)
            return False

    async def async_update_portfolio_data(self) -> bool:
        """Fetch data from Google Sheets and update InfluxDB."""
        try:
            if not self._google_api or not self.config.get(CONF_GOOGLE_SHEETS_ID):
                _LOGGER.info("Google Sheets not configured, skipping data sync")
                return True
            
            # Get data from Google Sheets
            _LOGGER.info("Fetching portfolio data from Google Sheets...")
            sheets_data = await self.async_get_google_sheets_data()
            
            if not sheets_data.get("connected") or not sheets_data.get("data"):
                _LOGGER.warning("Failed to fetch data from Google Sheets")
                return False
            
            # Process and write to InfluxDB
            success = await self.hass.async_add_executor_job(
                self._write_sheets_data_to_influx, sheets_data["data"]
            )
            
            if success:
                _LOGGER.info("Successfully updated InfluxDB with Google Sheets data")
            else:
                _LOGGER.error("Failed to write Google Sheets data to InfluxDB")
                
            return success
            
        except Exception as e:
            _LOGGER.error("Failed to update portfolio data from Google Sheets: %s", e)
            return False

    def _write_sheets_data_to_influx(self, sheets_data: list) -> bool:
        """Write Google Sheets data to InfluxDB (sync method for executor)."""
        try:
            client = self._get_influx_client()
            database = self.config.get(CONF_INFLUXDB_DATABASE, "portfolio")
            
            if not sheets_data or len(sheets_data) < 2:
                _LOGGER.warning("No valid data rows found in Google Sheets")
                return False
            
            # Assume first row is headers, process data rows
            headers = [str(cell).strip().lower() for cell in sheets_data[0]]
            data_rows = sheets_data[1:]
            
            _LOGGER.debug("Processing %d data rows with headers: %s", len(data_rows), headers)
            
            # Prepare data points for InfluxDB
            points = []
            portfolio_total = 0.0
            position_count = 0
            
            for row_index, row in enumerate(data_rows):
                if len(row) < len(headers):
                    continue  # Skip incomplete rows
                
                try:
                    # Create a dictionary from headers and row data
                    row_data = {}
                    for i, header in enumerate(headers):
                        if i < len(row):
                            row_data[header] = str(row[i]).strip()
                    
                    # Extract key fields (adjust based on your sheet structure)
                    symbol = row_data.get('symbol', row_data.get('ticker', ''))
                    quantity = float(row_data.get('quantity', row_data.get('shares', 0)))
                    price = float(row_data.get('price', row_data.get('current_price', 0)))
                    value = float(row_data.get('value', row_data.get('market_value', quantity * price)))
                    
                    if not symbol or value <= 0:
                        continue
                    
                    # Create InfluxDB point for individual position
                    position_point = {
                        "measurement": "positions",
                        "tags": {
                            "symbol": symbol.upper()
                        },
                        "fields": {
                            "quantity": quantity,
                            "price": price,
                            "value": value,
                            "change": float(row_data.get('change', row_data.get('daily_change', 0))),
                        },
                        "time": datetime.now().isoformat()
                    }
                    points.append(position_point)
                    
                    portfolio_total += value
                    position_count += 1
                    
                    _LOGGER.debug("Processed position: %s = $%.2f", symbol, value)
                    
                except (ValueError, KeyError) as e:
                    _LOGGER.warning("Skipping invalid row %d: %s", row_index, e)
                    continue
            
            # Add portfolio total point
            if portfolio_total > 0:
                portfolio_point = {
                    "measurement": "portfolio",
                    "fields": {
                        "total_value": portfolio_total,
                        "position_count": position_count,
                    },
                    "time": datetime.now().isoformat()
                }
                points.append(portfolio_point)
            
            # Write points to InfluxDB
            if points:
                client.write_points(points, database=database)
                _LOGGER.info("Written %d points to InfluxDB (portfolio value: $%.2f)", 
                           len(points), portfolio_total)
                return True
            else:
                _LOGGER.warning("No valid data points to write to InfluxDB")
                return False
                
        except Exception as e:
            _LOGGER.error("Failed to write data to InfluxDB: %s", e)
            return False

    def run_analytics(self, days: int = 30) -> dict[str, Any]:
        """Run portfolio analytics using InfluxDB v1."""
        try:
            client = self._get_influx_client()
            database = self.config.get(CONF_INFLUXDB_DATABASE, "portfolio")
            
            analytics_result = {
                'days_analyzed': days,
                'analysis_complete': False,
                'trends': {},
                'performance': {},
            }
            
            try:
                # Get portfolio values over the specified period
                analytics_query = f'''
                SELECT mean("total_value") 
                FROM "portfolio" 
                WHERE time > now() - {days}d 
                GROUP BY time(1d)
                '''
                
                _LOGGER.debug("Running analytics for %d days", days)
                result = client.query(analytics_query, database=database)
                
                values = []
                for point in result.get_points():
                    value = point.get('mean')
                    if value is not None:
                        values.append(float(value))
                
                if len(values) >= 2:
                    start_value = values[0]
                    end_value = values[-1]
                    total_change = end_value - start_value
                    percent_change = (total_change / start_value * 100) if start_value > 0 else 0
                    
                    # Calculate volatility (standard deviation)
                    if len(values) > 2:
                        mean_value = sum(values) / len(values)
                        variance = sum((v - mean_value) ** 2 for v in values) / len(values)
                        volatility = variance ** 0.5
                    else:
                        volatility = 0
                    
                    analytics_result.update({
                        'analysis_complete': True,
                        'performance': {
                            'start_value': start_value,
                            'end_value': end_value,
                            'total_change': total_change,
                            'percent_change': percent_change,
                            'volatility': volatility,
                            'data_points': len(values),
                        },
                        'trends': {
                            'direction': 'up' if total_change > 0 else 'down' if total_change < 0 else 'flat',
                            'trend_strength': 'strong' if abs(percent_change) > 10 else 'moderate' if abs(percent_change) > 5 else 'weak',
                            'volatility_level': 'high' if volatility > mean_value * 0.1 else 'low',
                        }
                    })
                    
                    _LOGGER.debug("Analytics complete: %.2f%% change over %d days", percent_change, days)
            
            except Exception as e:
                _LOGGER.warning("Analytics calculation failed: %s", e)
            
            return analytics_result
            
        except Exception as e:
            _LOGGER.error("Failed to run analytics: %s", e)
            return {
                'days_analyzed': days,
                'analysis_complete': False,
                'error': str(e)
            }

    def get_system_status(self) -> dict[str, Any]:
        """Get portfolio system status."""
        try:
            status = {
                'system_healthy': True,
                'components': {
                    'portfolio_tracker': True,
                    'influxdb': False,
                    'google_sheets': False,
                },
                'last_check': datetime.now().isoformat(),
                'version': 'v1-compatible',
            }
            
            # Check InfluxDB v1
            try:
                client = self._get_influx_client()
                client.ping()
                status['components']['influxdb'] = True
                
                # Check database access
                database = self.config.get(CONF_INFLUXDB_DATABASE, "portfolio")
                databases = client.get_list_database()
                db_names = [db['name'] for db in databases]
                if database not in db_names:
                    status['components']['influxdb'] = False
                    status['system_healthy'] = False
                    
            except Exception as e:
                _LOGGER.debug("InfluxDB health check failed: %s", e)
                status['system_healthy'] = False
            
            # Google Sheets check (if configured)
            if self.config.get(CONF_GOOGLE_SHEETS_ID):
                # Google Sheets health check would go here
                status['components']['google_sheets'] = False
            
            return status
            
        except Exception as e:
            _LOGGER.error("Failed to get system status: %s", e)
            return {
                'system_healthy': False,
                'error': str(e),
                'components': {
                    'portfolio_tracker': False,
                    'influxdb': False,
                    'google_sheets': False,
                },
                'last_check': datetime.now().isoformat(),
                'version': 'v1-compatible',
            }