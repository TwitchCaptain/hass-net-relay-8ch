"""Pulse buttons for each relay channel."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CHANNEL_COUNT, DOMAIN
from .coordinator import NetRelayCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up pulse buttons."""
    coordinator: NetRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NetRelayPulseButton(coordinator, entry, channel)
        for channel in range(1, CHANNEL_COUNT + 1)
    )


class NetRelayPulseButton(CoordinatorEntity[NetRelayCoordinator], ButtonEntity):
    """Pulse a relay for the configured duration."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:flash"

    def __init__(
        self, coordinator: NetRelayCoordinator, entry: ConfigEntry, channel: int
    ) -> None:
        super().__init__(coordinator)
        self._channel = channel
        host = entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_pulse_{channel}"
        self._attr_name = f"Pulse {coordinator.channel_name(channel)}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{host}:{entry.data.get('port')}")},
            name=coordinator.device_name,
            manufacturer="Zhen Ming / IoTZone",
            model="8 Channel Network Relay Board",
            configuration_url=f"http://{host}",
        )

    async def async_press(self) -> None:
        """Send a pulse."""
        await self.coordinator.async_pulse_relay(self._channel)
