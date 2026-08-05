"""Setup, unload, switch, and pulse service tests for net_relay_8ch."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers import entity_registry as er

from custom_components.net_relay_8ch import SERVICE_PULSE
from custom_components.net_relay_8ch.const import DOMAIN

from .conftest import make_board_state


async def test_setup_creates_entities_and_service(hass, setup_entry):
    assert setup_entry.state is ConfigEntryState.LOADED
    assert hass.services.has_service(DOMAIN, SERVICE_PULSE)

    registry = er.async_get(hass)
    entities = [
        e
        for e in registry.entities.values()
        if e.config_entry_id == setup_entry.entry_id
    ]
    unique_ids = {e.unique_id for e in entities}

    for channel in range(1, 9):
        assert f"relay.local_relay_{channel}" in unique_ids
        assert f"relay.local_input_{channel}" in unique_ids
        assert f"relay.local_pulse_{channel}" in unique_ids
    assert "relay.local_pulse_duration" in unique_ids

    # Channel 2 was on in the mocked board state.
    assert hass.states.get("switch.relay_board_relay_2").state == STATE_ON
    assert hass.states.get("switch.relay_board_relay_1").state == STATE_OFF


async def test_unload_removes_service(hass, setup_entry):
    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert setup_entry.state is ConfigEntryState.NOT_LOADED
    assert not hass.services.has_service(DOMAIN, SERVICE_PULSE)


async def test_switch_turn_on_calls_client(hass, setup_entry, mock_client):
    mock_client.async_get_state.return_value = make_board_state(relays_on={1, 2})
    await hass.services.async_call(
        "switch",
        "turn_on",
        {"entity_id": "switch.relay_board_relay_1"},
        blocking=True,
    )
    mock_client.async_set_relay.assert_awaited_with(1, True)


async def test_pulse_service(hass, setup_entry, mock_client):
    await hass.services.async_call(
        DOMAIN,
        SERVICE_PULSE,
        {"entity_id": "switch.relay_board_relay_2", "duration": 0.25},
        blocking=True,
    )
    mock_client.async_pulse_relay.assert_awaited_with(2, duration=0.25)


async def test_pulse_button(hass, setup_entry, mock_client):
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "button", DOMAIN, "relay.local_pulse_3"
    )
    assert entity_id

    await hass.services.async_call(
        "button",
        "press",
        {"entity_id": entity_id},
        blocking=True,
    )
    mock_client.async_pulse_relay.assert_awaited()
    assert mock_client.async_pulse_relay.await_args.args[0] == 3
