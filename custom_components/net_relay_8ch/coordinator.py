"""DataUpdateCoordinator for the network relay board."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import BoardState, NetRelayClient
from .const import (
    CONF_PULSE_SECONDS,
    DEFAULT_PULSE_SECONDS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class NetRelayCoordinator(DataUpdateCoordinator[BoardState]):
    """Poll the relay board."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: NetRelayClient
    ) -> None:
        self.client = client
        self.entry = entry
        interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL.total_seconds()),
        )
        try:
            update_interval = timedelta(seconds=int(interval))
        except (TypeError, ValueError):
            update_interval = DEFAULT_SCAN_INTERVAL
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.data[CONF_HOST]}",
            update_interval=update_interval,
            config_entry=entry,
        )

    @property
    def pulse_seconds(self) -> float:
        """Configured software pulse duration."""
        value = self.entry.options.get(
            CONF_PULSE_SECONDS,
            self.entry.data.get(CONF_PULSE_SECONDS, DEFAULT_PULSE_SECONDS),
        )
        try:
            return float(value)
        except (TypeError, ValueError):
            return DEFAULT_PULSE_SECONDS

    @property
    def device_name(self) -> str:
        """Friendly device name."""
        return self.entry.data.get(CONF_NAME) or self.entry.title or "Relay Board"

    def channel_name(self, channel: int) -> str:
        """Optional per-channel display name from options."""
        names = self.entry.options.get("channel_names") or self.entry.data.get(
            "channel_names"
        ) or {}
        return names.get(str(channel)) or names.get(channel) or f"Relay {channel}"

    def input_name(self, channel: int) -> str:
        """Optional per-input display name from options."""
        names = self.entry.options.get("input_names") or self.entry.data.get(
            "input_names"
        ) or {}
        return names.get(str(channel)) or names.get(channel) or f"Input {channel}"

    async def _async_update_data(self) -> BoardState:
        try:
            return await self.client.async_get_state()
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(
                f"Error communicating with relay board {self.entry.data[CONF_HOST]}:{self.entry.data.get(CONF_PORT)}: {err}"
            ) from err

    async def async_set_relay(self, channel: int, on: bool) -> None:
        """Set relay and refresh."""
        await self.client.async_set_relay(channel, on)
        await self.async_request_refresh()

    async def async_pulse_relay(self, channel: int, duration: float | None = None) -> None:
        """Pulse relay using configured or override duration."""
        seconds = self.pulse_seconds if duration is None else duration
        await self.client.async_pulse_relay(channel, duration=seconds)
        await self.async_request_refresh()
