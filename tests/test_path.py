"""Tests for the Aster standard path library."""

from __future__ import annotations

from aster_lang.interpreter import Interpreter
from aster_lang.module_resolution import get_stdlib_path
from aster_lang.parser import parse_module

_STDLIB = get_stdlib_path()


def _run(snippet: str) -> str:
    """Run an Aster expression via path module; return printed string."""
    src = f"use path\nfn main():\n    print({snippet})\n"
    m = parse_module(src)
    interp = Interpreter(base_dir=_STDLIB)
    interp.interpret(m)
    return interp.output[0]


def _run_bool(snippet: str) -> bool:
    """Evaluate a Bool expression; return True/False."""
    src = (
        f"use path\n"
        f"fn main():\n"
        f"    if {snippet}:\n"
        f'        print("true")\n'
        f"    else:\n"
        f'        print("false")\n'
    )
    m = parse_module(src)
    interp = Interpreter(base_dir=_STDLIB)
    interp.interpret(m)
    return interp.output[0] == "true"


# ---------------------------------------------------------------------------
# Separators
# ---------------------------------------------------------------------------


def test_sep() -> None:
    assert _run("path.sep()") == "/"


def test_ext_sep() -> None:
    assert _run("path.ext_sep()") == "."


# ---------------------------------------------------------------------------
# Joining and splitting
# ---------------------------------------------------------------------------


def test_join() -> None:
    assert _run('path.join("/a/b", "c/d")') == "/a/b/c/d"
    assert _run('path.join("/a/b/", "/c/d")') == "/a/b/c/d"
    assert _run('path.join("/a/b/", "c/d")') == "/a/b/c/d"
    assert _run('path.join("", "c/d")') == "c/d"
    assert _run('path.join("/a", "")') == "/a"


# ---------------------------------------------------------------------------
# Component extraction
# ---------------------------------------------------------------------------


def test_basename() -> None:
    assert _run('path.basename("/a/b/c.txt")') == "c.txt"
    assert _run('path.basename("c.txt")') == "c.txt"
    assert _run('path.basename("/a/b/c")') == "c"


def test_dirname() -> None:
    assert _run('path.dirname("/a/b/c.txt")') == "/a/b"
    assert _run('path.dirname("/a")') == "/"
    assert _run('path.dirname("a/b")') == "a"
    assert _run('path.dirname("a")') == ""


def test_stem() -> None:
    assert _run('path.stem("/a/b/c.txt")') == "c"
    assert _run('path.stem("c")') == "c"
    assert _run('path.stem("archive.tar.gz")') == "archive.tar"


def test_extension() -> None:
    assert _run('path.extension("/a/b/c.txt")') == ".txt"
    assert _run('path.extension("c")') == ""
    assert _run('path.extension("archive.tar.gz")') == ".gz"


def test_with_extension() -> None:
    assert _run('path.with_extension("/a/b/c.txt", ".md")') == "/a/b/c.md"
    assert _run('path.with_extension("/a/b/c.txt", "md")') == "/a/b/c.md"
    assert _run('path.with_extension("c", ".py")') == "c.py"


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------


def test_is_absolute() -> None:
    assert _run_bool('path.is_absolute("/a/b")') is True
    assert _run_bool('path.is_absolute("a/b")') is False
    assert _run_bool('path.is_absolute("")') is False


def test_is_relative() -> None:
    assert _run_bool('path.is_relative("a/b")') is True
    assert _run_bool('path.is_relative("/a/b")') is False


def test_has_extension() -> None:
    assert _run_bool('path.has_extension("file.txt")') is True
    assert _run_bool('path.has_extension("file")') is False
    assert _run_bool('path.has_extension("/a/b/c.py")') is True


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


def test_normalize() -> None:
    assert _run('path.normalize("/a/b/")') == "/a/b"
    assert _run('path.normalize("/a/b")') == "/a/b"
    assert _run('path.normalize("")') == "."
