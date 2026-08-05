"""The 8 Channel Network Relay Board integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .client import NetRelayClient
from .const import (
    ATTR_CHANNEL,
    CONF_PROTOCOL,
    DEFAULT_HTTP_PASSWORD,
    DEFAULT_HTTP_USER,
    DEFAULT_TCP_PORT,
    DOMAIN,
    PROTOCOL_TCP,
)
from .coordinator import NetRelayCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SWITCH,
]

SERVICE_PULSE = "pulse"
SERVICE_PULSE_SCHEMA = vol.Schema(
    {
        vol.Required("entity_id"): cv.entity_ids,
        vol.Optional("duration"): vol.All(
            vol.Coerce(float), vol.Range(min=0.05, max=60)
        ),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    client = NetRelayClient(
        hass,
        host=entry.data[CONF_HOST],
        protocol=entry.data.get(CONF_PROTOCOL, PROTOCOL_TCP),
        port=entry.data.get(CONF_PORT, DEFAULT_TCP_PORT),
        username=entry.data.get(CONF_USERNAME, DEFAULT_HTTP_USER),
        password=entry.data.get(CONF_PASSWORD, DEFAULT_HTTP_PASSWORD),
    )
    coordinator = NetRelayCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    async def async_handle_pulse(call: ServiceCall) -> None:
        registry = er.async_get(hass)
        duration = call.data.get("duration")
        for entity_id in call.data["entity_id"]:
            state = hass.states.get(entity_id)
            if state is None:
                continue
            channel = state.attributes.get(ATTR_CHANNEL)
            if channel is None:
                continue
            ent = registry.async_get(entity_id)
            target: NetRelayCoordinator | None = None
            if ent and ent.config_entry_id:
                target = hass.data[DOMAIN].get(ent.config_entry_id)
            if target is None:
                host = state.attributes.get("host")
                for coord in hass.data[DOMAIN].values():
                    if coord.entry.data[CONF_HOST] == host:
                        target = coord
                        break
            if target is None:
                continue
            await target.async_pulse_relay(int(channel), duration=duration)

    if not hass.services.has_service(DOMAIN, SERVICE_PULSE):
        hass.services.async_register(
            DOMAIN, SERVICE_PULSE, async_handle_pulse, schema=SERVICE_PULSE_SCHEMA
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    if not hass.data.get(DOMAIN) and hass.services.has_service(DOMAIN, SERVICE_PULSE):
        hass.services.async_remove(DOMAIN, SERVICE_PULSE)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
