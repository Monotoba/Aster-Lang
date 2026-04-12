# User Guide

This project currently provides a language and toolchain design package plus a starter implementation scaffold.

## Intended future tools

- `aster run file.aster` — run a program (`--backend interpreter|vm`)
- `aster check file.aster` — parse and type-check (`--ownership off|warn|deny`)
- `aster fmt file.aster` — format source
- `aster build file.aster` — build artifacts (`--backend python|vm|c`, `--ownership off|warn|deny`, `--vm-artifact-format json|binary`; `c` is a placeholder that emits a stub `.c` file)
- `aster repl` — interactive shell
- `aster rr grammar/aster-full.ebnf` — grammar workflow helper

## Current scaffold command

```bash
python -m aster_lang --help
```

## Current project purpose

Use this repository to:
- evolve the language spec
- implement the parser and runtime
- keep docs and examples aligned
- maintain disciplined development practices
