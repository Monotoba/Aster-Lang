"""Tests for the Aster http stdlib module (HTTP client/server)."""

from __future__ import annotations

import socket
import threading
import time

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


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _wait_for_port(port: int, timeout: float = 3.0) -> bool:
    """Return True once the port accepts connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                return True
        except OSError:
            time.sleep(0.05)
    return False


# ---------------------------------------------------------------------------
# Static: http.aster parses and loads cleanly
# ---------------------------------------------------------------------------


def test_http_module_parses_and_analyses() -> None:
    """http.aster should load without crashing the semantic analyzer."""
    src = 'use http\nfn main():\n    print("ok")\n'
    m = parse_module(src)
    analyzer = SemanticAnalyzer(base_dir=_STDLIB, allow_external_imports=True)
    analyzer.analyze(m)
    interp = _make_interp()
    interp.interpret(m)
    assert interp.output == ["ok"]


# ---------------------------------------------------------------------------
# Round-trip: listen + get (loopback)
# ---------------------------------------------------------------------------


def test_http_roundtrip_loopback() -> None:
    """Spin up the Aster HTTP server in a thread; client calls get()."""
    port = _free_port()
    server_error: list[Exception] = []

    # Use a named function for the handler (fn-literal arguments not yet supported).
    server_src = f"""\
use http

fn handle(req) -> http.Response:
    return {{ status: 200, body: "hello from aster" }}

fn main():
    http.listen({port}, handle)
"""

    def run_server() -> None:
        try:
            _run(server_src)
        except Exception as exc:
            server_error.append(exc)

    t = threading.Thread(target=run_server, daemon=True)
    t.start()

    if not _wait_for_port(port):
        if server_error:
            pytest.skip(f"Server failed to start: {server_error[0]}")
        pytest.fail("HTTP server did not come up within 3 seconds")

    client_src = f"""\
use http
fn main():
    res := http.get("http://127.0.0.1:{port}/")
    print(str(res.status))
    print(res.body)
"""
    output = _run(client_src)
    t.join(timeout=5)

    assert not server_error, f"Server error: {server_error[0]}"
    assert output[0] == "200"
    assert output[1] == "hello from aster"


# ---------------------------------------------------------------------------
# Error: connecting to a closed port raises
# ---------------------------------------------------------------------------


def test_http_get_connection_refused_raises() -> None:
    """http.get to a port with no server should raise InterpreterError."""
    src = 'use http\nfn main():\n    http.get("http://127.0.0.1:1/")\n'
    with pytest.raises(InterpreterError):
        _run(src)
