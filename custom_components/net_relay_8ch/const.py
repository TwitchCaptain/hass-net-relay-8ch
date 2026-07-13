"""Constants for the 8 Channel Network Relay Board integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "net_relay_8ch"
DEFAULT_NAME: Final = "Relay Board"
DEFAULT_TCP_PORT: Final = 1234
DEFAULT_HTTP_PORT: Final = 80
DEFAULT_SCAN_INTERVAL: Final = timedelta(seconds=5)
DEFAULT_TIMEOUT: Final = 4.0
DEFAULT_PULSE_SECONDS: Final = 0.5
DEFAULT_HTTP_USER: Final = "admin"
DEFAULT_HTTP_PASSWORD: Final = "12345678"
CHANNEL_COUNT: Final = 8

PROTOCOL_TCP: Final = "tcp"
PROTOCOL_HTTP: Final = "http"

CONF_PROTOCOL: Final = "protocol"
CONF_USERNAME: Final = "username"
CONF_PASSWORD: Final = "password"
CONF_PULSE_SECONDS: Final = "pulse_seconds"
CONF_CHANNEL_NAMES: Final = "channel_names"
CONF_INPUT_NAMES: Final = "input_names"

ATTR_CHANNEL: Final = "channel"
