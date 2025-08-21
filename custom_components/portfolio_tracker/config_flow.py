"""Config flow for Portfolio Tracker integration - InfluxDB v1 for HA Add-on."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
# OAuth2 flow will be added in future version
# from homeassistant.helpers import config_entry_oauth2_flow

from .const import (
    DOMAIN,
    CONF_INFLUXDB_URL,
    CONF_INFLUXDB_USERNAME,
    CONF_INFLUXDB_PASSWORD,
    CONF_INFLUXDB_DATABASE,
    CONF_GOOGLE_SHEETS_ID,
    CONF_GOOGLE_CREDENTIALS_JSON,
    CONF_UPDATE_INTERVAL,
    CONF_AUTO_SYNC_SHEETS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_INFLUXDB_URL,
)
from .utils import parse_influxdb_url

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_INFLUXDB_URL, default=DEFAULT_INFLUXDB_URL): str,
        vol.Required(CONF_INFLUXDB_USERNAME): str,
        vol.Required(CONF_INFLUXDB_PASSWORD): str,
        vol.Optional(CONF_INFLUXDB_DATABASE, default="portfolio"): str,
        vol.Optional(CONF_GOOGLE_SHEETS_ID, description="Google Sheets document ID"): str,
        vol.Optional(CONF_GOOGLE_CREDENTIALS_JSON, description="Google Service Account JSON credentials"): str,
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=5, max=1440)
        ),
        vol.Optional(CONF_AUTO_SYNC_SHEETS, default=True): bool,
    }
)


def _test_google_credentials(credentials_json: str) -> bool:
    """Test Google service account credentials."""
    if not credentials_json:
        return True  # Optional
    
    try:
        import json
        from google.oauth2.service_account import Credentials
        
        # Parse JSON
        credentials_data = json.loads(credentials_json)
        
        # Check if it's a service account
        if credentials_data.get("type") != "service_account":
            raise ValueError("Only service account credentials are supported")
        
        # Try to create credentials
        Credentials.from_service_account_info(
            credentials_data, 
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        
        return True
        
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        _LOGGER.debug("Google credentials validation failed: %s", e)
        return False
    except Exception as e:
        _LOGGER.debug("Google credentials test failed: %s", e)
        return False


def _test_influxdb_connection(data: dict[str, Any]) -> dict[str, Any]:
    """Test InfluxDB connection (sync function for executor)."""
    # Import here to avoid dependency issues
    try:
        from influxdb import InfluxDBClient
    except ImportError as err:
        raise CannotConnect("InfluxDB v1 client not available") from err

    # Extract connection info
    username = data[CONF_INFLUXDB_USERNAME].strip()
    password = data[CONF_INFLUXDB_PASSWORD].strip()
    database = data.get(CONF_INFLUXDB_DATABASE, "portfolio").strip()
    
    if not (username and password):
        raise InvalidAuth("Username and password are required")

    # Parse URL to get host and port
    url = data[CONF_INFLUXDB_URL]
    try:
        host, port, ssl = parse_influxdb_url(url)
    except ValueError as err:
        raise CannotConnect(str(err)) from err

    # Test the connection
    try:
        client = InfluxDBClient(
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            ssl=ssl,
            timeout=30
        )
        
        # Test connection by pinging
        client.ping()
        _LOGGER.info("InfluxDB v1 connection test successful")
        
        # Test database access
        try:
            databases = client.get_list_database()
            db_names = [db['name'] for db in databases]
            if database not in db_names:
                _LOGGER.warning("Database '%s' not found. Available: %s", database, db_names)
        except Exception as e:
            _LOGGER.warning("Could not list databases: %s", e)
        
        client.close()
        
    except Exception as exc:
        _LOGGER.exception("Connection validation failed")
        if "authentication" in str(exc).lower() or "unauthorized" in str(exc).lower():
            raise InvalidAuth("Invalid username or password") from exc
        elif "connection" in str(exc).lower():
            raise CannotConnect("Cannot connect to InfluxDB server") from exc
        else:
            raise CannotConnect(f"InfluxDB connection failed: {exc}") from exc

    # Return info that you want to store in the config entry.
    return {"title": f"Portfolio Tracker ({host}:{port})"}


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    # Test InfluxDB connection
    influx_result = await hass.async_add_executor_job(_test_influxdb_connection, data)
    
    # Test Google credentials if provided
    google_credentials = data.get(CONF_GOOGLE_CREDENTIALS_JSON)
    if google_credentials:
        google_valid = await hass.async_add_executor_job(_test_google_credentials, google_credentials)
        if not google_valid:
            raise InvalidAuth("Invalid Google service account credentials")
    
    return influx_result


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Portfolio Tracker."""

    VERSION = 1
    # CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL  # Deprecated in newer HA versions

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", 
            data_schema=STEP_USER_DATA_SCHEMA, 
            errors=errors,
            description_placeholders={
                "influxdb_version": "InfluxDB v1 with username/password (compatible with HA Add-on)"
            }
        )


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Portfolio Tracker."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL, 
                        self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    )
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440)),
                vol.Optional(
                    CONF_GOOGLE_SHEETS_ID,
                    default=self.config_entry.options.get(
                        CONF_GOOGLE_SHEETS_ID,
                        self.config_entry.data.get(CONF_GOOGLE_SHEETS_ID, "")
                    ),
                    description="Google Sheets document ID"
                ): str,
                vol.Optional(
                    CONF_GOOGLE_CREDENTIALS_JSON,
                    default=self.config_entry.options.get(
                        CONF_GOOGLE_CREDENTIALS_JSON,
                        self.config_entry.data.get(CONF_GOOGLE_CREDENTIALS_JSON, "")
                    ),
                    description="Google Service Account JSON credentials"
                ): str,
            }),
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""