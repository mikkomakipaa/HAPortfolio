"""Google API integration using Home Assistant's Application Credentials."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components.application_credentials import (
    AuthenticatedConnection,
    async_import_client_credential,
)
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


class GoogleSheetsAPI:
    """Google Sheets API client using HA's Application Credentials."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the Google Sheets API client."""
        self.hass = hass
        self.config_entry = config_entry
        self._service = None
        self._auth_implementation = None

    async def async_get_service(self):
        """Get or create the Google Sheets service using Application Credentials."""
        if self._service is None:
            try:
                # Get OAuth2 implementation for this config entry
                implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
                    self.hass, self.config_entry
                )
                
                if not implementation:
                    _LOGGER.error("No OAuth2 implementation found. Please configure Application Credentials.")
                    return None
                
                # Get OAuth2 session
                session = config_entry_oauth2_flow.OAuth2Session(
                    self.hass, self.config_entry, implementation
                )
                
                # Check if we have valid credentials
                if not session.valid_token:
                    _LOGGER.warning("OAuth2 token not valid. Please re-authenticate.")
                    return None
                
                # Create Google credentials from OAuth2 session
                credentials = Credentials(
                    token=session.token["access_token"],
                    refresh_token=session.token.get("refresh_token"),
                    client_id=implementation.client_id,
                    client_secret=implementation.client_secret,
                    token_uri="https://oauth2.googleapis.com/token",
                    scopes=SCOPES,
                )
                
                # Build the service
                self._service = build("sheets", "v4", credentials=credentials)
                _LOGGER.info("Successfully connected to Google Sheets API using Application Credentials")
                
            except RefreshError as e:
                _LOGGER.error(f"Failed to refresh Google API credentials: {e}")
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