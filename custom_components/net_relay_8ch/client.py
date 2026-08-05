"""TCP and HTTP clients for Zhen Ming / IoTZone 8-channel relay boards."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CHANNEL_COUNT,
    DEFAULT_HTTP_PASSWORD,
    DEFAULT_HTTP_USER,
    DEFAULT_TIMEOUT,
    PROTOCOL_HTTP,
    PROTOCOL_TCP,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class BoardState:
    """Parsed relay and input states."""

    relays: dict[int, bool] = field(default_factory=dict)
    inputs: dict[int, bool] = field(default_factory=dict)
    raw: str = ""


def _safe_channel(value: Any) -> int | None:
    """Return channel 1-8 or None (never raise on empty/bad values)."""
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        channel = int(text)
    except (TypeError, ValueError):
        return None
    if 1 <= channel <= CHANNEL_COUNT:
        return channel
    return None


def parse_tcp_dump(payload: str) -> BoardState:
    """Parse a DUMP response robustly (issue #11 — no crashes on junk)."""
    state = BoardState(raw=payload)
    text = payload.upper()

    for channel in range(1, CHANNEL_COUNT + 1):
        # Explicit tokens win; missing tokens default off/low after a successful dump.
        if re.search(rf"RELAYON\s+{channel}\b", text):
            state.relays[channel] = True
        elif re.search(rf"RELAYOFF\s+{channel}\b", text):
            state.relays[channel] = False
        else:
            state.relays[channel] = False

        if re.search(rf"\bIH\s+{channel}\b", text):
            state.inputs[channel] = True
        elif re.search(rf"\bIL\s+{channel}\b", text):
            state.inputs[channel] = False
        else:
            state.inputs[channel] = False
    return state


def parse_http_state(payload: dict[str, Any]) -> BoardState:
    """Parse state.cgi JSON: {"input":"...","output":"..."} with 0/1 chars."""
    state = BoardState(raw=str(payload))
    outputs = str(payload.get("output", ""))
    inputs = str(payload.get("input", ""))
    for channel in range(1, CHANNEL_COUNT + 1):
        if len(outputs) >= channel:
            state.relays[channel] = outputs[channel - 1] == "1"
        else:
            state.relays[channel] = False
        if len(inputs) >= channel:
            state.inputs[channel] = inputs[channel - 1] == "1"
        else:
            state.inputs[channel] = False
    return state


class NetRelayClient:
    """Async client supporting classic TCP (ZM) and HTTP (v5.8+) firmwares."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        protocol: str,
        port: int,
        username: str = DEFAULT_HTTP_USER,
        password: str = DEFAULT_HTTP_PASSWORD,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.hass = hass
        self.host = host
        self.protocol = protocol
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self._lock = asyncio.Lock()

    async def async_get_state(self) -> BoardState:
        """Poll board state."""
        if self.protocol == PROTOCOL_HTTP:
            return await self._http_get_state()
        return await self._tcp_dump()

    async def async_set_relay(self, channel: int, on: bool) -> None:
        """Turn a relay on or off."""
        channel = _safe_channel(channel)
        if channel is None:
            raise ValueError("Relay channel must be an integer 1-8")
        if self.protocol == PROTOCOL_HTTP:
            await self._http_set_relay(channel, on)
        else:
            cmd = f"{'L' if on else 'D'}{channel}"
            await self._tcp_command(cmd)

    async def async_pulse_relay(self, channel: int, duration: float | None = None) -> None:
        """Pulse a relay.

        If duration is set (>0), use a software pulse (on → sleep → off) so pulse
        length is configurable across firmwares (issue #10).
        Otherwise use the board's native pulse command.
        """
        channel = _safe_channel(channel)
        if channel is None:
            raise ValueError("Relay channel must be an integer 1-8")

        if duration is not None and duration > 0:
            await self.async_set_relay(channel, True)
            await asyncio.sleep(duration)
            await self.async_set_relay(channel, False)
            return

        if self.protocol == PROTOCOL_HTTP:
            await self._http_pulse(channel)
        else:
            await self._tcp_command(f"P{channel}")

    async def _tcp_dump(self) -> BoardState:
        async with self._lock:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            try:
                writer.write(b"DUMP\r\n")
                await writer.drain()
                chunks: list[bytes] = []
                while True:
                    try:
                        chunk = await asyncio.wait_for(reader.read(4096), timeout=self.timeout)
                    except asyncio.TimeoutError:
                        break
                    if not chunk:
                        break
                    chunks.append(chunk)
                    joined = b"".join(chunks)
                    if b"OK" in joined.upper():
                        break
                payload = b"".join(chunks).decode("latin-1", errors="replace")
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:  # noqa: BLE001, S110
                    pass
        if not payload.strip():
            raise ConnectionError(f"Empty DUMP from {self.host}:{self.port}")
        return parse_tcp_dump(payload)

    async def _tcp_command(self, command: str) -> None:
        async with self._lock:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
            try:
                writer.write(f"{command}\r\n".encode())
                await writer.drain()
                # Some firmwares reply; don't require it.
                try:
                    await asyncio.wait_for(reader.read(256), timeout=0.3)
                except asyncio.TimeoutError:
                    pass
            finally:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:  # noqa: BLE001, S110
                    pass

    def _http_auth(self) -> aiohttp.BasicAuth:
        return aiohttp.BasicAuth(self.username, self.password)

    async def _http_get_state(self) -> BoardState:
        session = async_get_clientsession(self.hass)
        url = f"http://{self.host}:{self.port}/state.cgi"
        async with session.get(
            url, auth=self._http_auth(), timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as resp:
            resp.raise_for_status()
            # Some boards return JSON; some return text that is JSON-ish
            try:
                data = await resp.json(content_type=None)
            except Exception:  # noqa: BLE001
                text = await resp.text()
                import json

                data = json.loads(text)
        if not isinstance(data, dict):
            raise ConnectionError(f"Unexpected state.cgi payload from {self.host}")
        return parse_http_state(data)

    async def _http_set_relay(self, channel: int, on: bool) -> None:
        session = async_get_clientsession(self.hass)
        # Modern CGI (v5.8 / turgu1 / mgx0)
        action = "relayon" if on else "relayoff"
        value = "on" if on else "off"
        url = f"http://{self.host}:{self.port}/relay.cgi?{action}{channel}={value}"
        try:
            async with session.get(
                url,
                auth=self._http_auth(),
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status < 400:
                    return
                _LOGGER.debug("relay.cgi returned %s, trying relay_en.cgi", resp.status)
        except aiohttp.ClientError as err:
            _LOGGER.debug("relay.cgi failed (%s), trying relay_en.cgi", err)

        # Older HTTP POST style (Domoticz / saida)
        post_url = f"http://{self.host}:{self.port}/relay_en.cgi"
        key = f"saida{channel}{'on' if on else 'off'}"
        data = {key: "on" if on else "off"}
        async with session.post(
            post_url,
            data=data,
            auth=self._http_auth(),
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        ) as resp:
            resp.raise_for_status()

    async def _http_pulse(self, channel: int) -> None:
        session = async_get_clientsession(self.hass)
        url = f"http://{self.host}:{self.port}/relay.cgi?pulse{channel}=pulse"
        try:
            async with session.get(
                url,
                auth=self._http_auth(),
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status < 400:
                    return
        except aiohttp.ClientError:
            pass
        post_url = f"http://{self.host}:{self.port}/relay_en.cgi"
        data = {f"saida{channel}pluse": "pluse"}  # firmware typo is intentional
        async with session.post(
            post_url,
            data=data,
            auth=self._http_auth(),
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        ) as resp:
            resp.raise_for_status()


async def async_detect_protocol(
    hass: HomeAssistant,
    host: str,
    tcp_port: int = 1234,
    http_port: int = 80,
    username: str = DEFAULT_HTTP_USER,
    password: str = DEFAULT_HTTP_PASSWORD,
) -> tuple[str, int]:
    """Try TCP then HTTP; return (protocol, port)."""
    tcp = NetRelayClient(hass, host, PROTOCOL_TCP, tcp_port)
    try:
        await tcp.async_get_state()
        return PROTOCOL_TCP, tcp_port
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("TCP probe failed for %s:%s: %s", host, tcp_port, err)

    http = NetRelayClient(
        hass, host, PROTOCOL_HTTP, http_port, username=username, password=password
    )
    await http.async_get_state()
    return PROTOCOL_HTTP, http_port
