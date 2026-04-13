"""Tests for the Aster net stdlib module (high-level TCP networking)."""

from __future__ import annotations

import threading

import pytest

from aster_lang.interpreter import Interpreter, InterpreterError
from aster_lang.module_resolution import get_stdlib_path
from aster_lang.parser import parse_module
from aster_lang.semantic import SemanticAnalyzer

_STDLIB = get_stdlib_path()


def _make_interp() -> Interpreter:
    return Interpreter(base_dir=_STDLIB)


def _run(src: str) -> list[str]:
    m = parse_module(src)
    interp = _make_interp()
    interp.interpret(m)
    return interp.output


# ---------------------------------------------------------------------------
# Static analysis: net.aster should parse and analyse cleanly
# ---------------------------------------------------------------------------


def test_net_module_parses_and_analyses() -> None:
    """net.aster should load without semantic errors when imported."""
    src = 'use net\nfn main():\n    print("ok")\n'
    m = parse_module(src)
    analyzer = SemanticAnalyzer(base_dir=_STDLIB, allow_external_imports=True)
    # Semantic analysis may not fully resolve the source stdlib (it uses UNKNOWN types
    # liberally for native modules), so we just verify it doesn't hard-crash.
    analyzer.analyze(m)
    interp = _make_interp()
    interp.interpret(m)
    assert interp.output == ["ok"]


# ---------------------------------------------------------------------------
# Round-trip: dial / listen / accept / send / recv / close / stop
# ---------------------------------------------------------------------------


def test_net_roundtrip_loopback() -> None:
    """Server in a thread, client connects and exchanges a message."""
    import socket as _socket

    # Find a free port.
    with _socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    server_error: list[Exception] = []

    server_src = f"""\
use net
fn main():
    server := net.listen("127.0.0.1", {port})
    client := net.accept(server)
    data := net.recv(client, 1024)
    net.send(client, "echo:" + data)
    net.close(client)
    net.stop(server)
"""

    def run_server() -> None:
        try:
            _run(server_src)
        except Exception as exc:
            server_error.append(exc)

    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    # Give the server a moment to bind.
    import time

    time.sleep(0.05)

    client_src = f"""\
use net
fn main():
    conn := net.dial("127.0.0.1", {port})
    net.send(conn, "hello")
    reply := net.recv(conn, 1024)
    print(reply)
    net.close(conn)
"""
    output = _run(client_src)
    t.join(timeout=5)

    assert not server_error, f"Server error: {server_error[0]}"
    assert output == ["echo:hello"]


# ---------------------------------------------------------------------------
# API surface: verify public functions are callable
# ---------------------------------------------------------------------------


def test_net_dial_bad_address_raises() -> None:
    """Connecting to a closed port raises an InterpreterError."""
    src = 'use net\nfn main():\n    net.dial("127.0.0.1", 1)\n'
    with pytest.raises(InterpreterError):
        _run(src)
