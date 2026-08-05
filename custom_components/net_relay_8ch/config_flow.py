"""Config flow for 8 Channel Network Relay Board."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .client import NetRelayClient, async_detect_protocol
from .const import (
    CONF_PROTOCOL,
    CONF_PULSE_SECONDS,
    DEFAULT_HTTP_PASSWORD,
    DEFAULT_HTTP_PORT,
    DEFAULT_HTTP_USER,
    DEFAULT_NAME,
    DEFAULT_PULSE_SECONDS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TCP_PORT,
    DOMAIN,
    PROTOCOL_HTTP,
    PROTOCOL_TCP,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            protocol = user_input.get(CONF_PROTOCOL, "auto")
            port = user_input.get(CONF_PORT)
            username = user_input.get(CONF_USERNAME, DEFAULT_HTTP_USER)
            password = user_input.get(CONF_PASSWORD, DEFAULT_HTTP_PASSWORD)

            try:
                if protocol == "auto":
                    protocol, detected_port = await async_detect_protocol(
                        self.hass,
                        host,
                        tcp_port=int(port) if port else DEFAULT_TCP_PORT,
                        http_port=DEFAULT_HTTP_PORT,
                        username=username,
                        password=password,
                    )
                    port = detected_port
                else:
                    if not port:
                        port = (
                            DEFAULT_HTTP_PORT
                            if protocol == PROTOCOL_HTTP
                            else DEFAULT_TCP_PORT
                        )
                    client = NetRelayClient(
                        self.hass,
                        host=host,
                        protocol=protocol,
                        port=int(port),
                        username=username,
                        password=password,
                    )
                    await client.async_get_state()
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()

                data = {
                    CONF_HOST: host,
                    CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME),
                    CONF_PROTOCOL: protocol,
                    CONF_PORT: int(port),
                    CONF_SCAN_INTERVAL: user_input.get(
                        CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds())
                    ),
                    CONF_PULSE_SECONDS: user_input.get(
                        CONF_PULSE_SECONDS, DEFAULT_PULSE_SECONDS
                    ),
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                }
                # Optional known channel names for this house can be set in options
                title = data[CONF_NAME]
                return self.async_create_entry(title=title, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Optional(CONF_PROTOCOL, default="auto"): vol.In(
                    {
                        "auto": "Auto-detect (TCP then HTTP)",
                        PROTOCOL_TCP: "TCP / ZM protocol (classic, port 1234)",
                        PROTOCOL_HTTP: "HTTP CGI (v5.8+ firmware, port 80)",
                    }
                ),
                vol.Optional(CONF_PORT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Optional(
                    CONF_SCAN_INTERVAL, default=int(DEFAULT_SCAN_INTERVAL.total_seconds())
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                vol.Optional(
                    CONF_PULSE_SECONDS, default=DEFAULT_PULSE_SECONDS
                ): vol.All(vol.Coerce(float), vol.Range(min=0.05, max=30)),
                vol.Optional(CONF_USERNAME, default=DEFAULT_HTTP_USER): str,
                vol.Optional(CONF_PASSWORD, default=DEFAULT_HTTP_PASSWORD): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage options including channel names and pulse duration."""
        if user_input is not None:
            channel_names = {}
            input_names = {}
            for i in range(1, 9):
                rname = (user_input.get(f"relay_name_{i}") or "").strip()
                iname = (user_input.get(f"input_name_{i}") or "").strip()
                if rname:
                    channel_names[str(i)] = rname
                if iname:
                    input_names[str(i)] = iname
            return self.async_create_entry(
                title="",
                data={
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    CONF_PULSE_SECONDS: user_input[CONF_PULSE_SECONDS],
                    "channel_names": channel_names,
                    "input_names": input_names,
                },
            )

        current = {**self.config_entry.data, **self.config_entry.options}
        names = current.get("channel_names") or {}
        inames = current.get("input_names") or {}
        fields: dict[Any, Any] = {
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=current.get(
                    CONF_SCAN_INTERVAL, int(DEFAULT_SCAN_INTERVAL.total_seconds())
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
            vol.Optional(
                CONF_PULSE_SECONDS,
                default=current.get(CONF_PULSE_SECONDS, DEFAULT_PULSE_SECONDS),
            ): vol.All(vol.Coerce(float), vol.Range(min=0.05, max=30)),
        }
        for i in range(1, 9):
            fields[vol.Optional(f"relay_name_{i}", default=names.get(str(i), ""))] = str
            fields[vol.Optional(f"input_name_{i}", default=inames.get(str(i), ""))] = str
        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields))
