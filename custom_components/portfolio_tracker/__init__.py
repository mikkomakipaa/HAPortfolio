"""Portfolio Tracker integration for Home Assistant."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    CONF_INFLUXDB_URL,
    CONF_INFLUXDB_USERNAME,
    CONF_INFLUXDB_PASSWORD,
    CONF_INFLUXDB_DATABASE,
    CONF_GOOGLE_SHEETS_ID,
    CONF_UPDATE_INTERVAL,
    CONF_AUTO_SYNC_SHEETS,
)
from .portfolio_manager import PortfolioManager

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


class PortfolioDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching portfolio data from multiple sources."""

    def __init__(
        self,
        hass: HomeAssistant,
        portfolio_manager: PortfolioManager,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.portfolio_manager = portfolio_manager
        self._last_successful_data = None

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from portfolio tracker."""
        data = {}
        errors = []
        
        # Check if auto-sync is enabled
        auto_sync = self.portfolio_manager.config.get(CONF_AUTO_SYNC_SHEETS, True)
        
        # Optionally sync from Google Sheets to InfluxDB first
        if auto_sync and self.portfolio_manager.config.get(CONF_GOOGLE_SHEETS_ID):
            try:
                _LOGGER.debug("Auto-syncing data from Google Sheets to InfluxDB...")
                sync_success = await self.portfolio_manager.async_update_portfolio_data()
                if sync_success:
                    _LOGGER.info("Successfully synced Google Sheets data to InfluxDB")
                    data["last_sync"] = "success"
                else:
                    _LOGGER.warning("Failed to sync Google Sheets data to InfluxDB")
                    data["last_sync"] = "failed"
            except Exception as err:
                _LOGGER.warning("Error during auto-sync: %s", err)
                data["last_sync"] = f"error: {err}"
        
        try:
            # Test InfluxDB connection first
            influxdb_connected = await self.hass.async_add_executor_job(
                self.portfolio_manager.test_connection
            )
            data["influxdb_status"] = "connected" if influxdb_connected else "disconnected"
        except Exception as err:
            _LOGGER.warning("InfluxDB connection test failed: %s", err)
            data["influxdb_status"] = "disconnected"
            data["influxdb_error"] = str(err)
            errors.append(f"InfluxDB: {err}")

        try:
            # Get portfolio data from InfluxDB
            portfolio_data = await self.hass.async_add_executor_job(
                self.portfolio_manager.get_portfolio_data
            )
            data.update(portfolio_data)
            
            # Store successful data as backup
            if not errors:
                self._last_successful_data = data.copy()
                
        except Exception as err:
            _LOGGER.warning("Portfolio data fetch failed: %s", err)
            errors.append(f"Portfolio data: {err}")
            
            # Return last successful data if available, otherwise raise error
            if self._last_successful_data:
                _LOGGER.info("Using last successful data due to fetch failure")
                data.update(self._last_successful_data)
                data["error"] = f"Using cached data - {err}"
            else:
                raise UpdateFailed(f"Error communicating with portfolio tracker: {err}")

        # Get Google Sheets status
        try:
            google_sheets_status = await self.portfolio_manager.async_get_google_sheets_status()
            data["google_sheets_status"] = google_sheets_status
        except Exception as err:
            _LOGGER.warning("Google Sheets status check failed: %s", err)
            data["google_sheets_status"] = "disconnected"
            data["google_sheets_error"] = str(err)

        # Add data source status
        data["data_sources"] = {
            "influxdb_connected": data.get("influxdb_status") == "connected",
            "google_sheets_connected": data.get("google_sheets_status") == "connected",
        }
        
        if errors:
            data["partial_errors"] = errors
            
        return data


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Portfolio Tracker from a config entry."""
    _LOGGER.info("Setting up Portfolio Tracker integration (entry_id: %s)", entry.entry_id)
    
    # Extract configuration
    config = {
        CONF_INFLUXDB_URL: entry.data[CONF_INFLUXDB_URL],
        CONF_INFLUXDB_USERNAME: entry.data[CONF_INFLUXDB_USERNAME],
        CONF_INFLUXDB_PASSWORD: entry.data[CONF_INFLUXDB_PASSWORD],
        CONF_INFLUXDB_DATABASE: entry.data.get(CONF_INFLUXDB_DATABASE, "portfolio"),
        CONF_GOOGLE_SHEETS_ID: entry.data.get(CONF_GOOGLE_SHEETS_ID),
        CONF_AUTO_SYNC_SHEETS: entry.data.get(CONF_AUTO_SYNC_SHEETS, True),
    }

    # Initialize portfolio manager with config entry for Google API access
    portfolio_manager = PortfolioManager(hass, config, entry)
    
    # Test the connection (non-blocking setup)
    try:
        connection_test = await hass.async_add_executor_job(portfolio_manager.test_connection)
        if not connection_test:
            _LOGGER.warning("Portfolio Tracker InfluxDB connection test failed, but continuing setup. Check your InfluxDB configuration.")
        else:
            _LOGGER.info("Portfolio Tracker InfluxDB connection successful")
    except Exception as err:
        _LOGGER.warning("Failed to test portfolio tracker connection during setup: %s. Integration will continue loading but may not function correctly.", err)
        # Don't fail setup completely - allow integration to load with limited functionality

    # Create data update coordinator
    update_interval = timedelta(
        minutes=entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_SCAN_INTERVAL)
    )
    coordinator = PortfolioDataUpdateCoordinator(
        hass, portfolio_manager, update_interval
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    # Store coordinator and manager in hass data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "portfolio_manager": portfolio_manager,
    }

    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services with error handling
    try:
        await _async_setup_services(hass, portfolio_manager)
    except Exception as err:
        _LOGGER.warning("Failed to register services: %s. Some functionality may not be available.", err)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_setup_services(hass: HomeAssistant, portfolio_manager: PortfolioManager) -> None:
    """Set up portfolio tracker services."""
    
    async def update_portfolio_data(call) -> dict:
        """Service to manually update portfolio data from Google Sheets to InfluxDB."""
        try:
            success = await portfolio_manager.async_update_portfolio_data()
            if success:
                hass.bus.async_fire("portfolio_tracker_updated", {"status": "success"})
                return {"success": True, "message": "Portfolio data updated successfully"}
            else:
                hass.bus.async_fire("portfolio_tracker_updated", {"status": "error", "error": "Failed to sync data"})
                return {"success": False, "error": "Failed to sync data"}
        except Exception as err:
            _LOGGER.error("Failed to update portfolio data: %s", err)
            hass.bus.async_fire("portfolio_tracker_updated", {"status": "error", "error": str(err)})
            return {"success": False, "error": str(err)}

    async def run_analytics(call) -> dict:
        """Service to run portfolio analytics."""
        days = call.data.get("days", 30)
        try:
            result = await hass.async_add_executor_job(
                portfolio_manager.run_analytics, days
            )
            hass.bus.async_fire("portfolio_analytics_completed", {"status": "success", "result": result})
            return {"success": True, "analytics": result, "days_analyzed": days}
        except Exception as err:
            _LOGGER.error("Failed to run analytics: %s", err)
            hass.bus.async_fire("portfolio_analytics_completed", {"status": "error", "error": str(err)})
            return {"success": False, "error": str(err)}

    async def get_portfolio_status(call) -> dict:
        """Service to get portfolio system status."""
        try:
            status = await hass.async_add_executor_job(portfolio_manager.get_system_status)
            hass.bus.async_fire("portfolio_status_retrieved", {"status": "success", "data": status})
            return {"success": True, "status": status}
        except Exception as err:
            _LOGGER.error("Failed to get portfolio status: %s", err)
            hass.bus.async_fire("portfolio_status_retrieved", {"status": "error", "error": str(err)})
            return {"success": False, "error": str(err)}

    # Register services with improved schema validation
    try:
        import voluptuous as vol
        import homeassistant.helpers.config_validation as cv
    except ImportError as err:
        _LOGGER.error("Required validation libraries not available: %s", err)
        return
    
    hass.services.async_register(
        DOMAIN, 
        "update_data", 
        update_portfolio_data,
        schema=vol.Schema({}),
        supports_response=vol.Schema({
            vol.Required("success"): bool,
            vol.Optional("message"): str,
            vol.Optional("error"): str,
        })
    )
    hass.services.async_register(
        DOMAIN, 
        "run_analytics", 
        run_analytics,
        schema=vol.Schema({
            vol.Optional("days", default=30, description="Number of days to analyze"): vol.All(
                cv.positive_int, vol.Range(min=1, max=365)
            )
        }),
        supports_response=vol.Schema({
            vol.Required("success"): bool,
            vol.Optional("analytics"): dict,
            vol.Optional("days_analyzed"): int,
            vol.Optional("error"): str,
        })
    )
    hass.services.async_register(
        DOMAIN, 
        "get_status", 
        get_portfolio_status,
        schema=vol.Schema({}),
        supports_response=vol.Schema({
            vol.Required("success"): bool,
            vol.Optional("status"): dict,
            vol.Optional("error"): str,
        })
    )