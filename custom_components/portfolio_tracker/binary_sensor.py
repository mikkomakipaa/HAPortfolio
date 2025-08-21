"""Binary sensor platform for Portfolio Tracker integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, BINARY_SENSOR_TYPES
from .portfolio_manager import PortfolioManager

_LOGGER = logging.getLogger(__name__)

BINARY_SENSOR_DESCRIPTIONS: dict[str, BinarySensorEntityDescription] = {
    "data_source_health": BinarySensorEntityDescription(
        key="data_source_health",
        name="Data Source Health",
        icon="mdi:database",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "influxdb_connected": BinarySensorEntityDescription(
        key="influxdb_connected",
        name="InfluxDB Connected",
        icon="mdi:database-check",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "google_sheets_connected": BinarySensorEntityDescription(
        key="google_sheets_connected",
        name="Google Sheets Connected",
        icon="mdi:google",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Portfolio Tracker binary sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    portfolio_manager = hass.data[DOMAIN][config_entry.entry_id]["portfolio_manager"]

    entities = []
    for sensor_key, description in BINARY_SENSOR_DESCRIPTIONS.items():
        entities.append(
            PortfolioBinarySensor(
                coordinator=coordinator,
                portfolio_manager=portfolio_manager,
                description=description,
                config_entry_id=config_entry.entry_id,
            )
        )

    async_add_entities(entities, True)


class PortfolioBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Portfolio Tracker binary sensor."""

    def __init__(
        self,
        coordinator,
        portfolio_manager: PortfolioManager,
        description: BinarySensorEntityDescription,
        config_entry_id: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._portfolio_manager = portfolio_manager
        self._config_entry_id = config_entry_id
        
        # Set unique ID
        self._attr_unique_id = f"{config_entry_id}_{description.key}"
        
        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry_id)},
            "name": "Portfolio Tracker",
            "manufacturer": "Portfolio Tracker",
            "model": "Home Assistant Integration",
            "sw_version": "1.3.0",
        }

    @property
    def is_on(self) -> bool | None:
        """Return True if the binary sensor is on."""
        if not self.coordinator.data:
            return None

        data = self.coordinator.data
        key = self.entity_description.key
        data_sources = data.get("data_sources", {})

        if key == "data_source_health":
            # Overall health - at least InfluxDB should be connected
            return data_sources.get("influxdb_connected", False)
        elif key == "influxdb_connected":
            return data_sources.get("influxdb_connected", False)
        elif key == "google_sheets_connected":
            return data_sources.get("google_sheets_connected", False)

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if not self.coordinator.data:
            return None

        data = self.coordinator.data
        key = self.entity_description.key
        data_sources = data.get("data_sources", {})

        attributes = {}

        if key == "data_source_health":
            attributes.update({
                "influxdb_status": "connected" if data_sources.get("influxdb_connected") else "disconnected",
                "google_sheets_status": "connected" if data_sources.get("google_sheets_connected") else "disconnected",
                "last_successful_update": data.get("last_update"),
                "total_data_sources": len([k for k, v in data_sources.items() if v]),
            })
            
            if data.get("error"):
                attributes["last_error"] = data.get("error")

        elif key == "influxdb_connected":
            attributes.update({
                "connection_status": "connected" if data_sources.get("influxdb_connected") else "disconnected",
                "last_check": data.get("last_update"),
            })

        elif key == "google_sheets_connected":
            attributes.update({
                "connection_status": "connected" if data_sources.get("google_sheets_connected") else "disconnected",
                "last_check": data.get("last_update"),
                "configured": bool(self._portfolio_manager.config.get("google_sheets_id")),
            })

        return attributes if attributes else None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
        )

    @property
    def icon(self) -> str | None:
        """Return the icon for the binary sensor."""
        key = self.entity_description.key
        
        if key == "data_source_health":
            if self.is_on:
                return "mdi:database-check"
            else:
                return "mdi:database-remove"
        elif key == "influxdb_connected":
            if self.is_on:
                return "mdi:database-check"
            else:
                return "mdi:database-off"
        elif key == "google_sheets_connected":
            if self.is_on:
                return "mdi:google"
            else:
                return "mdi:google-spreadsheet"
        
        return self.entity_description.icon