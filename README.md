# Home Assistant — 8 Channel Network Relay Board

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Custom Home Assistant integration for the cheap eBay / AliExpress **8-channel Ethernet relay boards** (Zhen Ming / IoTZone, RELAY-NET V5.x).

Spiritual successor to the Indigo plugin
[`indigo-8channel-relay`](https://github.com/davidnewhall/indigo-8channel-relay)
(also see the HTTP spinoff [`indigo-simple-8channel-relay`](https://github.com/turgu1/indigo-simple-8channel-relay)).

## What you get

One HA **device** with:

| Entity | Count | Purpose |
|--------|-------|---------|
| Switches | 8 | Relay channels (on/off) |
| Binary sensors | 8 | Dry-contact / digital inputs (`IH` / `IL`) |
| Pulse buttons | 8 | Momentary energize (garage doors, etc.) |
| Number | 1 | Configurable pulse duration |

Plus service `net_relay_8ch.pulse` for automations.

## Built-in fixes for the Indigo issues

| Issue | Improvement in this integration |
|-------|----------------------------------|
| [#13 Python 3](https://github.com/davidnewhall/indigo-8channel-relay/issues/13) | Native HA / Python 3 |
| [#12 Other firmware](https://github.com/davidnewhall/indigo-8channel-relay/issues/12) | Dual protocol: classic **TCP/ZM** *and* **HTTP CGI** (v5.8+) with auto-detect |
| [#11 Log errors on empty channel](https://github.com/davidnewhall/indigo-8channel-relay/issues/11) | Defensive DUMP/JSON parsing — never `int("")` |
| [#10 Feature requests](https://github.com/davidnewhall/indigo-8channel-relay/issues/10) | Configurable **port** + **pulse duration** (number entity + service override) |

## Protocols

### TCP / ZM (classic, usually port `1234`)

```
DUMP\r\n          # status of all relays + inputs
L5\r\n            # relay 5 on
D5\r\n            # relay 5 off
P5\r\n            # native board pulse
```

Verified against a live board returning:

```
relayoff 1 … relayoff 8
IL 1 … IL 8
OK
```

### HTTP CGI (v5.8+ firmware, usually port `80`)

- Status: `GET /state.cgi` → JSON `{"input":"00000000","output":"00000000"}`
- On/off: `GET /relay.cgi?relayonN=on` / `relayoffN=off`
- Pulse: `GET /relay.cgi?pulseN=pulse`
- Fallback: `POST /relay_en.cgi` with `saidaNon=on` / `saidaNpluse=pluse`

Default HTTP auth is often `admin` / `12345678`.

## Install

1. Copy `custom_components/net_relay_8ch` into HA `config/custom_components/`.
2. Restart Home Assistant.
3. **Settings → Devices & services → Add integration → 8 Channel Network Relay Board**
4. Enter host; leave protocol on **Auto-detect** unless you know better.

### HACS

Add `https://github.com/TwitchCaptain/hass-net-relay-8ch` as a custom integration repository.

## Tips

- **Garage door openers** should use the **Pulse** button (or `net_relay_8ch.pulse`), not leave the relay latched on.
- Set friendly names under **Configure** (options) — e.g. “Big Garage Door Opener” on relay 5.
- Software pulse (on → wait → off) is used whenever pulse duration &gt; 0 so timing is consistent across firmwares.

## Related

- Indigo (TCP): https://github.com/davidnewhall/indigo-8channel-relay
- Indigo (HTTP / Py3): https://github.com/turgu1/indigo-simple-8channel-relay
- Domoticz RelayNet reference: TCP + optional HTTP POST
- Board reverse notes: https://github.com/mgx0/ZMRN0808-V5

## License

[MIT](LICENSE) © 2026 [Go Lift Technologies LLC](https://golift.io)
