from __future__ import annotations

import argparse
from pathlib import Path

from aster_lang.compiler import compile_source
from aster_lang.formatter import format_source
from aster_lang.interpreter import interpret_source
from aster_lang.repl import run_repl


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aster", description="Aster language scaffold CLI")
    sub = parser.add_subparsers(dest="command", required=False)

    run_p = sub.add_parser("run", help="interpret Aster source")
    run_p.add_argument("path", type=Path)

    fmt_p = sub.add_parser("fmt", help="format Aster source")
    fmt_p.add_argument("path", type=Path)

    build_p = sub.add_parser("build", help="compile Aster source")
    build_p.add_argument("path", type=Path)

    sub.add_parser("repl", help="start interactive REPL")
    sub.add_parser("version", help="show version")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        source = args.path.read_text(encoding="utf-8")
        result = interpret_source(source)
        if result.output:
            print(result.output)
        return 0

    if args.command == "fmt":
        source = args.path.read_text(encoding="utf-8")
        print(format_source(source))
        return 0

    if args.command == "build":
        source = args.path.read_text(encoding="utf-8")
        artifact = compile_source(source)
        print(artifact.summary())
        return 0

    if args.command == "repl":
        run_repl()
        return 0

    if args.command == "version":
        print("aster-lang scaffold 0.1.0")
        return 0

    parser.print_help()
    return 0
