"""Tests for the Aster native socket module."""

from __future__ import annotations

import pytest

from aster_lang.interpreter import Interpreter, InterpreterError
from aster_lang.native_modules import NATIVE_MODULE_SYMBOLS, NATIVE_MODULES
from aster_lang.parser import parse_module


def run(source: str) -> list[str]:
    """Parse and run an Aster snippet; return captured output lines."""
    m = parse_module(source)
    interp = Interpreter()
    interp.interpret(m)
    return interp.output


class TestSocketRegistry:
    def test_socket_registered(self) -> None:
        assert "socket" in NATIVE_MODULES

    def test_socket_symbols_registered(self) -> None:
        assert "socket" in NATIVE_MODULE_SYMBOLS
        assert "create" in NATIVE_MODULE_SYMBOLS["socket"]
        assert "AF_INET" in NATIVE_MODULE_SYMBOLS["socket"]


class TestSocketFunctions:
    def test_gethostname(self) -> None:
        src = "use socket\nfn main():\n    print(socket.gethostname())\n"
        output = run(src)
        assert len(output) == 1
        assert len(output[0]) > 0

    def test_gethostbyname_localhost(self) -> None:
        src = 'use socket\nfn main():\n    print(socket.gethostbyname("localhost"))\n'
        output = run(src)
        assert output == ["127.0.0.1"]

    def test_create_and_close(self) -> None:
        src = (
            "use socket\nfn main():\n"
            "    sock := socket.create(socket.AF_INET, socket.SOCK_STREAM)\n"
            "    print(str(sock))\n"
            "    socket.close(sock)\n"
        )
        output = run(src)
        assert len(output) == 1
        assert int(output[0]) > 0

    def test_invalid_socket_id(self) -> None:
        src = "use socket\nfn main():\n    socket.close(9999)\n"
        # socket.close should handle invalid ID gracefully (as implemented)
        assert run(src) == []

    def test_bind_invalid_id(self) -> None:
        src = 'use socket\nfn main():\n    socket.bind(9999, "127.0.0.1", 8080)\n'
        with pytest.raises(InterpreterError, match="invalid socket ID"):
            run(src)
