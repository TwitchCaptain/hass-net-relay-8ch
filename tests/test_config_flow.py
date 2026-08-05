"""Tests for the net_relay_8ch config and options flows."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResultType

from custom_components.net_relay_8ch.const import (
    CONF_PROTOCOL,
    CONF_PULSE_SECONDS,
    DOMAIN,
    PROTOCOL_TCP,
)

from .conftest import ENTRY_DATA, make_board_state


def _patch_get_state(side_effect=None):
    return patch(
        "custom_components.net_relay_8ch.config_flow.NetRelayClient.async_get_state",
        new=AsyncMock(return_value=make_board_state(), side_effect=side_effect),
    )


def _patch_detect(protocol=PROTOCOL_TCP, port=1234, side_effect=None):
    return patch(
        "custom_components.net_relay_8ch.config_flow.async_detect_protocol",
        new=AsyncMock(return_value=(protocol, port), side_effect=side_effect),
    )


def _patch_setup():
    return patch(
        "custom_components.net_relay_8ch.async_setup_entry",
        return_value=True,
    )


async def test_user_flow_tcp_creates_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    user_input = {**ENTRY_DATA, CONF_PROTOCOL: PROTOCOL_TCP}
    with _patch_get_state(), _patch_setup():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Relay Board"
    assert result["data"][CONF_HOST] == "relay.local"
    assert result["data"][CONF_PROTOCOL] == PROTOCOL_TCP
    assert result["result"].unique_id == "relay.local:1234"


async def test_user_flow_auto_detect(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    user_input = {
        CONF_HOST: "relay.local",
        CONF_PROTOCOL: "auto",
    }
    with _patch_detect(), _patch_setup():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PROTOCOL] == PROTOCOL_TCP
    assert result["data"]["port"] == 1234


async def test_user_flow_cannot_connect(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with _patch_get_state(side_effect=ConnectionError("down")):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**ENTRY_DATA, CONF_PROTOCOL: PROTOCOL_TCP}
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_aborts_on_duplicate(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    with _patch_get_state():
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {**ENTRY_DATA, CONF_PROTOCOL: PROTOCOL_TCP}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_updates_channel_names(hass, mock_config_entry):
    mock_config_entry.add_to_hass(hass)
    with _patch_setup():
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        result = await hass.config_entries.options.async_init(
            mock_config_entry.entry_id
        )
        assert result["type"] is FlowResultType.FORM

        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                CONF_SCAN_INTERVAL: 10,
                CONF_PULSE_SECONDS: 1.5,
                "relay_name_5": "Garage Door",
                "input_name_1": "Door Sensor",
            },
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_config_entry.options[CONF_SCAN_INTERVAL] == 10
    assert mock_config_entry.options[CONF_PULSE_SECONDS] == 1.5
    assert mock_config_entry.options["channel_names"]["5"] == "Garage Door"
    assert mock_config_entry.options["input_names"]["1"] == "Door Sensor"
