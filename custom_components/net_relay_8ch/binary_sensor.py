"""Binary sensors for board inputs."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTR_CHANNEL, CHANNEL_COUNT, DOMAIN
from .coordinator import NetRelayCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up input sensors."""
    coordinator: NetRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        NetRelayInput(coordinator, entry, channel)
        for channel in range(1, CHANNEL_COUNT + 1)
    )


class NetRelayInput(CoordinatorEntity[NetRelayCoordinator], BinarySensorEntity):
    """A single digital input (IH = on / asserted)."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: NetRelayCoordinator, entry: ConfigEntry, channel: int
    ) -> None:
        super().__init__(coordinator)
        self._channel = channel
        host = entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_input_{channel}"
        self._attr_name = coordinator.input_name(channel)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{host}:{entry.data.get('port')}")},
            name=coordinator.device_name,
            manufacturer="Zhen Ming / IoTZone",
            model="8 Channel Network Relay Board",
            configuration_url=f"http://{host}",
        )

    @property
    def is_on(self) -> bool | None:
        """True when input is high (IH)."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.inputs.get(self._channel)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Channel metadata."""
        return {ATTR_CHANNEL: self._channel}
