"""Number entity for configurable pulse duration (issue #10)."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PULSE_SECONDS, DOMAIN
from .coordinator import NetRelayCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up pulse duration number."""
    coordinator: NetRelayCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([NetRelayPulseDuration(coordinator, entry)])


class NetRelayPulseDuration(CoordinatorEntity[NetRelayCoordinator], NumberEntity):
    """Software pulse length applied by pulse buttons / service."""

    _attr_has_entity_name = True
    _attr_name = "Pulse duration"
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_native_min_value = 0.05
    _attr_native_max_value = 30.0
    _attr_native_step = 0.05
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:timer-outline"

    def __init__(
        self, coordinator: NetRelayCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        host = entry.data[CONF_HOST]
        self._attr_unique_id = f"{host}_pulse_duration"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{host}:{entry.data.get('port')}")},
            name=coordinator.device_name,
            manufacturer="Zhen Ming / IoTZone",
            model="8 Channel Network Relay Board",
            configuration_url=f"http://{host}",
        )

    @property
    def native_value(self) -> float:
        """Current pulse seconds."""
        return self.coordinator.pulse_seconds

    async def async_set_native_value(self, value: float) -> None:
        """Persist pulse duration into options."""
        options = {**self._entry.options, CONF_PULSE_SECONDS: float(value)}
        self.hass.config_entries.async_update_entry(self._entry, options=options)
        # Do not reload whole integration for a number tweak — coordinator reads options live
        self.async_write_ha_state()
