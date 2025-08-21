"""Google API integration using Home Assistant's Google authentication."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class GoogleSheetsAPI:
    """Google Sheets API client using HA's Google integration."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the Google Sheets API client."""
        self.hass = hass
        self.config_entry = config_entry
        self._service = None

    async def async_get_service(self):
        """Get or create the Google Sheets service."""
        if self._service is None:
            try:
                # First, check if Google integration is loaded
                if "google" not in self.hass.data:
                    _LOGGER.warning("Google integration not found in Home Assistant. Please install and configure Google Drive integration first.")
                    return None
                
                # Try to get authentication from Google integration 
                google_data = self.hass.data.get("google", {})
                
                # Check for Google config entries
                google_entries = [entry for entry in self.hass.config_entries.async_entries("google")]
                if not google_entries:
                    _LOGGER.warning("No Google integration entries found. Please configure Google Drive integration first.")
                    return None
                
                # Get the first Google entry
                google_entry = google_entries[0]
                entry_data = google_data.get(google_entry.entry_id)
                
                if entry_data and hasattr(entry_data, 'async_get_access_token'):
                    # Try to get access token from the Google integration
                    try:
                        token_info = await entry_data.async_get_access_token()
                        if token_info:
                            # Create credentials object
                            from google.oauth2.credentials import Credentials
                            credentials = Credentials(token=token_info['access_token'])
                            self._service = build("sheets", "v4", credentials=credentials)
                            _LOGGER.info("Successfully connected to Google Sheets API using HA Google integration")
                        else:
                            _LOGGER.warning("No access token available from Google integration")
                            return None
                    except Exception as token_error:
                        _LOGGER.warning(f"Failed to get access token: {token_error}")
                        return None
                else:
                    _LOGGER.warning("Google integration data not available or incompatible format")
                    return None
                
            except Exception as e:
                _LOGGER.error(f"Failed to connect to Google Sheets API: {e}")
                return None
                
        return self._service

    async def async_get_sheet_data(
        self, 
        spreadsheet_id: str, 
        range_name: str = "Sheet1!A1:Z1000"
    ) -> Optional[List[List[str]]]:
        """Get data from Google Sheets."""
        try:
            service = await self.async_get_service()
            if service is None:
                return None

            # Execute the request
            result = await self.hass.async_add_executor_job(
                self._get_values, service, spreadsheet_id, range_name
            )
            
            if result is None:
                return None
                
            values = result.get("values", [])
            _LOGGER.debug(f"Retrieved {len(values)} rows from Google Sheets")
            return values
            
        except HttpError as e:
            _LOGGER.error(f"Google Sheets API error: {e}")
            return None
        except Exception as e:
            _LOGGER.error(f"Unexpected error getting sheet data: {e}")
            return None

    def _get_values(self, service, spreadsheet_id: str, range_name: str):
        """Sync method to get values from Google Sheets."""
        try:
            result = (
                service.spreadsheets()
                .values()
                .get(spreadsheetId=spreadsheet_id, range=range_name)
                .execute()
            )
            return result
        except Exception as e:
            _LOGGER.error(f"Error executing sheets request: {e}")
            return None

    async def async_test_connection(self, spreadsheet_id: str) -> bool:
        """Test connection to Google Sheets."""
        try:
            service = await self.async_get_service()
            if service is None:
                return False

            # Try to get spreadsheet metadata
            result = await self.hass.async_add_executor_job(
                self._get_spreadsheet_metadata, service, spreadsheet_id
            )
            
            return result is not None
            
        except Exception as e:
            _LOGGER.error(f"Google Sheets connection test failed: {e}")
            return False

    def _get_spreadsheet_metadata(self, service, spreadsheet_id: str):
        """Get spreadsheet metadata to test connection."""
        try:
            result = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            return result
        except Exception as e:
            _LOGGER.error(f"Error getting spreadsheet metadata: {e}")
            return None

    async def async_get_connection_status(self) -> str:
        """Get current connection status."""
        try:
            service = await self.async_get_service()
            return "connected" if service is not None else "disconnected"
        except Exception:
            return "disconnected"


class GoogleAPIError(Exception):
    """Exception raised for Google API errors."""
    pass