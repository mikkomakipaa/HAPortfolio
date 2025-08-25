"""Google API integration using service account or API key authentication."""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as UserCredentials

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_GOOGLE_CREDENTIALS_JSON

_LOGGER = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class GoogleSheetsAPI:
    """Google Sheets API client using service account credentials."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the Google Sheets API client."""
        self.hass = hass
        self.config_entry = config_entry
        self._service = None
        self._credentials = None

    async def async_get_service(self):
        """Get or create the Google Sheets service using service account credentials."""
        if self._service is None:
            try:
                # Get credentials from config entry
                credentials_json = self.config_entry.data.get(CONF_GOOGLE_CREDENTIALS_JSON)
                
                if not credentials_json:
                    _LOGGER.warning("No Google credentials configured. Google Sheets functionality disabled.")
                    return None
                
                # Parse credentials JSON
                try:
                    credentials_data = json.loads(credentials_json)
                except json.JSONDecodeError as e:
                    _LOGGER.error("Invalid Google credentials JSON format: %s", e)
                    return None
                
                # Create service account credentials
                if "type" in credentials_data and credentials_data["type"] == "service_account":
                    _LOGGER.debug("Using service account credentials")
                    credentials = Credentials.from_service_account_info(
                        credentials_data, scopes=SCOPES
                    )
                else:
                    _LOGGER.error("Only service account credentials are supported")
                    return None
                
                # Build the service with error handling
                try:
                    self._service = await self.hass.async_add_executor_job(
                        build, "sheets", "v4", credentials=credentials
                    )
                    _LOGGER.info("Google Sheets API service initialized successfully")
                except Exception as e:
                    _LOGGER.error("Failed to build Google Sheets API service: %s", e)
                    return None
                self._credentials = credentials
                
                _LOGGER.info("Successfully connected to Google Sheets API using service account")
                
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