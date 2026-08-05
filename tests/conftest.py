"""Shared fixtures for net_relay_8ch component tests."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.net_relay_8ch.client import BoardState
from custom_components.net_relay_8ch.const import (
    CONF_PROTOCOL,
    CONF_PULSE_SECONDS,
    DOMAIN,
    PROTOCOL_TCP,
)


# pytest-homeassistant-custom-component 0.13.x defines `enable_event_loop_debug`
# as a plain `@pytest.fixture(autouse=True)` async generator, which pytest 9
# rejects. Override it locally until the upstream plugin handles pytest 9.
@pytest_asyncio.fixture(autouse=True)
async def enable_event_loop_debug() -> None:
    """Enable event loop debug mode."""
    asyncio.get_running_loop().set_debug(True)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let the HA test harness discover custom_components/net_relay_8ch."""
    return


ENTRY_DATA: dict[str, Any] = {
    CONF_HOST: "relay.local",
    CONF_NAME: "Relay Board",
    CONF_PROTOCOL: PROTOCOL_TCP,
    CONF_PORT: 1234,
    CONF_SCAN_INTERVAL: 5,
    CONF_PULSE_SECONDS: 0.5,
    CONF_USERNAME: "admin",
    CONF_PASSWORD: "12345678",
}


def make_board_state(
    relays_on: set[int] | None = None,
    inputs_high: set[int] | None = None,
) -> BoardState:
    """Build a BoardState with optional channels asserted."""
    relays_on = relays_on or set()
    inputs_high = inputs_high or set()
    return BoardState(
        relays={i: i in relays_on for i in range(1, 9)},
        inputs={i: i in inputs_high for i in range(1, 9)},
        raw="OK",
    )


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Config entry with typical user input."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Relay Board",
        data=ENTRY_DATA,
        unique_id="relay.local:1234",
    )


@pytest.fixture
def mock_client() -> MagicMock:
    """Mock NetRelayClient for setup/service tests."""
    client = MagicMock()
    client.host = ENTRY_DATA[CONF_HOST]
    client.protocol = PROTOCOL_TCP
    client.port = ENTRY_DATA[CONF_PORT]
    client.async_get_state = AsyncMock(return_value=make_board_state(relays_on={2}))
    client.async_set_relay = AsyncMock()
    client.async_pulse_relay = AsyncMock()
    return client


@pytest.fixture
async def setup_entry(hass, mock_config_entry, mock_client) -> MockConfigEntry:
    """Set the integration up fully against the mocked client."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.net_relay_8ch.NetRelayClient",
        return_value=mock_client,
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    return mock_config_entry
