"""Sensor platform for Portfolio Tracker integration."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_DOLLAR, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_TYPES
from .portfolio_manager import PortfolioManager

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    "portfolio_value": SensorEntityDescription(
        key="portfolio_value",
        name="Portfolio Value",
        icon="mdi:currency-usd",
        native_unit_of_measurement=CURRENCY_DOLLAR,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "daily_change": SensorEntityDescription(
        key="daily_change",
        name="Daily Change",
        icon="mdi:trending-up",
        native_unit_of_measurement=CURRENCY_DOLLAR,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "daily_change_percent": SensorEntityDescription(
        key="daily_change_percent",
        name="Daily Change Percent",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "total_positions": SensorEntityDescription(
        key="total_positions",
        name="Total Positions",
        icon="mdi:format-list-numbered",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "last_update": SensorEntityDescription(
        key="last_update",
        name="Last Update",
        icon="mdi:clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Portfolio Tracker sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    portfolio_manager = hass.data[DOMAIN][config_entry.entry_id]["portfolio_manager"]

    entities = []
    for sensor_key, description in SENSOR_DESCRIPTIONS.items():
        entities.append(
            PortfolioSensor(
                coordinator=coordinator,
                portfolio_manager=portfolio_manager,
                description=description,
                config_entry_id=config_entry.entry_id,
            )
        )

    async_add_entities(entities, True)


class PortfolioSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Portfolio Tracker sensor."""

    def __init__(
        self,
        coordinator,
        portfolio_manager: PortfolioManager,
        description: SensorEntityDescription,
        config_entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._portfolio_manager = portfolio_manager
        self._config_entry_id = config_entry_id
        
        # Set unique ID using standardized format
        self._attr_unique_id = f"{DOMAIN}_{config_entry_id}_{description.key}"
        
        # Set device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry_id)},
            "name": "Portfolio Tracker",
            "manufacturer": "Portfolio Tracker",
            "model": "Home Assistant Integration",
            "sw_version": "0.1.0",
        }

    @property
    def native_value(self) -> Any:
        """Return the native value of the sensor."""
        if not self.coordinator.data:
            return None

        data = self.coordinator.data
        key = self.entity_description.key

        if key == "portfolio_value":
            return data.get("portfolio_value", 0.0)
        elif key == "daily_change":
            return data.get("daily_change", 0.0)
        elif key == "daily_change_percent":
            return data.get("daily_change_percent", 0.0)
        elif key == "total_positions":
            return len(data.get("positions", []))
        elif key == "last_update":
            last_update = data.get("last_update")
            if last_update:
                if isinstance(last_update, str):
                    try:
                        # Parse ISO string and ensure timezone info
                        dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                        # If timezone naive, assume UTC
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=ZoneInfo('UTC'))
                        return dt
                    except (ValueError, ImportError):
                        # Fallback for older Python without zoneinfo
                        try:
                            from datetime import timezone
                            dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            return dt
                        except ValueError:
                            return None
                elif isinstance(last_update, datetime):
                    # Ensure timezone info is present
                    if last_update.tzinfo is None:
                        try:
                            last_update = last_update.replace(tzinfo=ZoneInfo('UTC'))
                        except ImportError:
                            from datetime import timezone
                            last_update = last_update.replace(tzinfo=timezone.utc)
                    return last_update
            return None

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if not self.coordinator.data:
            return None

        data = self.coordinator.data
        key = self.entity_description.key

        attributes = {}

        if key == "portfolio_value":
            attributes.update({
                "positions_count": len(data.get("positions", [])),
                "data_sources": data.get("data_sources", {}),
            })
            
            # Add top positions if available
            positions = data.get("positions", [])
            if positions:
                top_positions = sorted(positions, key=lambda x: x.get("value", 0), reverse=True)[:5]
                attributes["top_positions"] = [
                    {
                        "symbol": pos.get("symbol"),
                        "value": pos.get("value"),
                        "change": pos.get("change"),
                    }
                    for pos in top_positions
                ]

        elif key == "daily_change":
            attributes.update({
                "change_percent": data.get("daily_change_percent", 0.0),
                "previous_value": data.get("previous_value", 0.0),
            })

        elif key == "total_positions":
            positions = data.get("positions", [])
            if positions:
                attributes.update({
                    "positions": [
                        {
                            "symbol": pos.get("symbol"),
                            "quantity": pos.get("quantity"),
                            "value": pos.get("value"),
                            "change": pos.get("change"),
                        }
                        for pos in positions
                    ]
                })

        elif key == "last_update":
            attributes.update({
                "data_sources": data.get("data_sources", {}),
                "update_success": not data.get("error"),
            })
            
            if data.get("error"):
                attributes["error"] = data.get("error")

        return attributes if attributes else None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and not self.coordinator.data.get("error")
        )

    @property
    def icon(self) -> str | None:
        """Return the icon for the sensor."""
        if self.entity_description.key == "daily_change":
            # Change icon based on positive/negative change
            if self.native_value and self.native_value > 0:
                return "mdi:trending-up"
            elif self.native_value and self.native_value < 0:
                return "mdi:trending-down"
            else:
                return "mdi:trending-neutral"
        
        return self.entity_description.icon