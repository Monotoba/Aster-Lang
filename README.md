# Aster Language

Aster is a human-first general-purpose programming language and toolchain.
It combines Python-style readability and indentation-sensitive syntax with
stronger typing, opt-in ownership diagnostics, and a path toward compiled
performance.

This repository contains the reference implementation: interpreter, semantic
analyzer, formatter, REPL, VM, Python transpiler, and standard library.

## Quick start

### Linux / macOS

```bash
cd aster-lang-gpt
bash ./setup-prj.sh
source .venv/bin/activate
pytest
aster --help
```

### Windows PowerShell

```powershell
cd aster-lang-gpt
powershell -ExecutionPolicy Bypass -File .\setup-prj.ps1
.\.venv\Scripts\Activate.ps1
pytest
aster --help
```

## Language at a glance

```aster
use math
use list

fn primes_up_to(limit: Int) -> List:
    mut sieve := list.range(2, limit)
    mut result := []
    while list.len(sieve) > 0:
        p := list.head(sieve)
        result <- list.append(result, p)
        sieve <- list.filter(fn(n) -> Bool: n % p != 0, sieve)
    return result

fn main():
    ps := primes_up_to(50)
    print("primes: " + str(ps))
    print("count:  " + str(list.len(ps)))
```

Key syntax:
- `:=` declares a binding; `<-` mutates one
- `mut` marks a mutable binding
- `fn` for functions and lambdas; `pub fn` to export from a module
- `use math`, `use str as strl` for module imports
- `match` for structural pattern matching
- `&T`, `&mut T`, `*own T` for future ownership types (diagnostics available now)

## Toolchain commands

```bash
aster run <file>                  # interpret a program
aster run --backend vm <file>     # run on the bytecode VM
aster check <file>                # semantic lint (no execution)
aster fmt <file>                  # format source
aster build --backend python <file>  # transpile to Python
aster build --backend vm <file>   # compile to bytecode bundle
aster build --backend c <file>    # C backend stub
aster backends                    # list available backends
aster repl                        # interactive REPL
aster ast <file>                  # dump parsed AST
aster doc <file>                  # generate documentation
aster lock <file>                 # write aster.lock
aster lsp                         # launch Language Server
aster test <dir>                  # run test suite
```

Flags available on `run`, `check`, and `build`:

```bash
--ownership off|warn|deny         # opt-in borrow/ownership diagnostics
--dep NAME=PATH                   # override a manifest dependency path
--search-root PATH                # add a module search root
--lockfile <path>                 # pin resolution to a lockfile
```

## Standard library

Eight native modules ship with the interpreter:

| Module   | Highlights |
|----------|-----------|
| `math`   | trig, exp/log, GCD/LCM, float classification, constants |
| `str`    | split/join, search (find/rfind), slice, pad, parse, format |
| `list`   | map, filter, reduce, sort, zip, enumerate, flatten, unique |
| `io`     | read/write/append files, list\_dir, walk\_dir, mkdir |
| `std`    | type\_of, env, args, assert, exit |
| `random` | rand\_int, rand\_float, choice, shuffle, sample |
| `time`   | now, monotonic, sleep, strftime |
| `linalg` | Vec2/Vec3/Vec4, Mat2/Mat3/Mat4, dot, cross, norm, lerp |

Additional stdlib modules written in Aster itself live in `src/aster_lang/stdlib/`:

| Module | Highlights |
|--------|-----------|
| `path` | join, basename, dirname, stem, extension, with\_extension, normalize, is\_absolute |

See `docs/language/standard-library/` for full reference documentation.

## Tutorials

23 tutorials take you from basics to advanced features:

1–10: bindings, control flow, functions, collections, match, destructuring, modules, lambdas, tooling  
11–20: type aliases, generics, traits, bitwise types, operator precedence, higher-order functions, project layout, debugging type errors, ownership philosophy, borrows  
21–23: FFI/extern, stdlib (math/str/list), io and system modules

Runnable tutorial programs are in `tutorials/programs/` (9 programs covering
fizzbuzz through word counting and FFI math).

## Repository map

```
src/aster_lang/         reference implementation
  stdlib/               Aster-written standard library modules
tests/                  1092 passing unit and integration tests
docs/
  language/             language reference and standard library docs
  toolchain/            interpreter, compiler, VM, formatter, package manager design
grammar/                EBNF grammars (Bottlecaps-compatible)
examples/               standalone Aster programs
tutorials/              23 numbered tutorials + runnable programs
tasks/                  recovery-oriented task tracking
ai/                     AI assistant instructions (Codex, Claude, Gemini, Aider)
```

## Package manager

The Aster package manager design is specified in
`docs/toolchain/PACKAGE-MANAGER-DESIGN.md`. It defines:

- `aster.toml` manifest format with typed author records, platform constraints, and semver dependency specs
- `.apkg` reproducible tar+zstd archive format
- `aster.lock` deterministic lockfile
- `aster pkg` CLI family (`init`, `build`, `check`, `install`, `search`, `submit`, …)
- moderated submission workflow, integrity verification, and error code table (`APKG001`–`APKG018`)

## Development workflow

```bash
pytest                  # run all tests
ruff check .            # lint
mypy src                # type check
```

Commits follow `type(scope): description` convention. See `AGENTS.md` for
AI-assistant workflow notes and `BACKLOG.md` for the current task queue.

## License

GPL-2.0-only. See `LICENSE`.
