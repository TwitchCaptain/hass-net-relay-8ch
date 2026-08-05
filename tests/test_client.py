"""Unit tests for DUMP/JSON parsers (Indigo #11 defensive parsing)."""

from __future__ import annotations

from custom_components.net_relay_8ch.client import parse_http_state, parse_tcp_dump


def test_parse_tcp_dump_happy_path():
    payload = """
relayoff 1
relayon 2
relayoff 3
relayoff 4
relayoff 5
relayoff 6
relayoff 7
relayoff 8
IL 1
IH 2
IL 3
IL 4
IL 5
IL 6
IL 7
IL 8
OK
"""
    state = parse_tcp_dump(payload)
    assert state.relays[1] is False
    assert state.relays[2] is True
    assert state.inputs[1] is False
    assert state.inputs[2] is True


def test_parse_tcp_dump_missing_tokens_default_off():
    """Missing channel tokens must not crash and should default off/low."""
    state = parse_tcp_dump("OK\r\n")
    assert state.relays == {i: False for i in range(1, 9)}
    assert state.inputs == {i: False for i in range(1, 9)}


def test_parse_tcp_dump_junk_does_not_raise():
    state = parse_tcp_dump("relayon \nIL \nIH abc\nOK")
    assert set(state.relays) == set(range(1, 9))
    assert set(state.inputs) == set(range(1, 9))


def test_parse_http_state():
    state = parse_http_state({"input": "01000000", "output": "10000000"})
    assert state.relays[1] is True
    assert state.relays[2] is False
    assert state.inputs[1] is False
    assert state.inputs[2] is True


def test_parse_http_state_short_strings():
    state = parse_http_state({"input": "1", "output": ""})
    assert state.relays[1] is False
    assert state.inputs[1] is True
    assert state.inputs[8] is False
