"""Interactive REPL for the Aster language."""

from __future__ import annotations

import sys

from aster_lang import ast
from aster_lang.interpreter import NIL, Interpreter, InterpreterError, Value
from aster_lang.parser import ParseError, parse_repl_input

_BANNER = """\
Aster REPL  (type 'exit' or Ctrl-D to quit, 'help' for hints)
"""

_HELP = """\
Hints:
  x := 42          bind a variable
  mut x := 0       mutable variable
  x <- 5           mutate x
  fn f(n): ...     define a function
  f(10)            call a function
  match n: ...     match expression
  exit             quit the REPL
"""

_STMT_STARTS = (
    "if",
    "while",
    "for",
    "match",
    "return",
    "break",
    "continue",
    "fn",
    "typealias",
    "use",
    "pub",
)


class ReplSession:
    """Manages a persistent interpreter session for interactive use."""

    def __init__(self) -> None:
        self.interpreter = Interpreter()

        # Patch print to emit directly, not buffer
        def live_print(arg: Value) -> Value:
            print(str(arg))
            return NIL

        from aster_lang.interpreter import BuiltinFunction

        self.interpreter.global_env.define("print", BuiltinFunction("print", live_print))

    def execute(self, source: str) -> str | None:
        """Execute one REPL chunk.

        Returns the string representation of the result if the input was a
        bare expression, or None for declarations/void statements.
        Raises ReplError on parse or runtime errors.
        """
        try:
            items = parse_repl_input(source)
        except ParseError as e:
            raise ReplError(str(e)) from e

        last_value: Value | None = None
        for item in items:
            try:
                if isinstance(item, ast.Decl):
                    self.interpreter.execute_declaration(item)
                elif isinstance(item, ast.ExprStmt):
                    # Bare expression — evaluate and remember result
                    last_value = self.interpreter.evaluate_expr(item.expr)
                else:
                    self.interpreter.execute_statement(item)
            except InterpreterError as e:
                raise ReplError(str(e)) from e
            except Exception as e:
                raise ReplError(f"Internal error: {e}") from e

        if last_value is not None and last_value is not NIL:
            return str(last_value)
        return None


class ReplError(Exception):
    """A recoverable REPL error (parse or runtime)."""


def _is_block_open(lines: list[str]) -> bool:
    """Return True if we are inside an open block (need more input)."""
    # Count logical indentation depth.  A line ending with ':' opens a block.
    depth = 0
    for line in lines:
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if stripped.endswith(":"):
            depth += 1
        elif depth > 0 and indent == 0:
            depth -= 1
    return depth > 0


def _collect_input(prompt: str, continuation: str) -> str | None:
    """Read one logical chunk from stdin.  Returns None on EOF."""
    try:
        first = input(prompt)
    except EOFError:
        return None

    if first.strip() in ("exit", "quit"):
        return None
    if first.strip() == "help":
        print(_HELP, end="")
        return ""

    lines = [first]
    # Keep reading while the block is open
    while _is_block_open(lines):
        try:
            line = input(continuation)
        except EOFError:
            break
        if line == "" and _is_block_open(lines[:-1] if lines else []):
            # Blank line can close the block
            break
        lines.append(line)

    return "\n".join(lines) + "\n"


def run_repl(*, file: object = None) -> None:
    """Run the interactive REPL loop.

    ``file`` is unused (kept for future redirection support).
    """
    _ = file  # reserved for future use
    print(_BANNER, end="")
    session = ReplSession()
    prompt = ">>> "
    continuation = "... "

    while True:
        chunk = _collect_input(prompt, continuation)
        if chunk is None:
            print()  # newline after Ctrl-D
            break
        if not chunk.strip():
            continue
        try:
            result = session.execute(chunk)
            if result is not None:
                print(result)
        except ReplError as e:
            print(f"error: {e}", file=sys.stderr)
