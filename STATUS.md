# STATUS

## Repository status

Phases 2–9 are complete. The language can parse, format, analyze, execute,
compile, and interact via the REPL and LSP, with a full standard library and tooling suite.

## Test count

**1092 passing tests** covering parser, semantics, interpreter, formatter, CLI,
compiler, REPL, AST printer, typed HIR, experimental bytecode VM, caching layer,
test runner, bench runner, doc generator, language server, and all native + source-based stdlib modules.

## What exists

### Core pipeline
- **Complete lexer** — indentation-aware (INDENT/DEDENT), all token kinds, source locations
- **Complete parser** — Pratt expression parsing, all declarations/statements/expressions,
  type annotations, destructuring, match patterns, lambda expressions, record type aliases
- **Comprehensive AST** — all node types
- **Complete semantic analyzer** — symbol tables, type inference, ownership/borrow prototype,
  trait/impl validation, generic type parameters, call-site trait method resolution,
  effect tracking prototype
- **Complete interpreter** — runtime value model, closures, match, destructuring,
  borrow/deref, module imports, `&mut` parameter mutation
- **Complete formatter** — canonical 4-space indentation, idempotent
- **Interactive REPL** (`aster repl`)
- **AST pretty-printer** (`aster ast <file>`)
- **Typed HIR debug output** (`aster hir <file>`)

### Build and backends
- **Python transpiler backend** — `aster build --backend python`; emits a runnable
  `__aster_build__/` directory with compiled modules under `_aster/`
- **Experimental VM backend** — `aster vm <file>` / `aster build --backend vm`;
  bytecode VM with full language coverage including match, closures, imports, borrows
- **VM artifacts** — serialized `*.asterbc.json` with format/version/SHA-256 integrity
  and optional HMAC signing; optional compressed binary encoding
- **Native C backend** — `aster build --backend c`; compiles Aster to native executables
  via MIR -> C codegen and GCC/system compiler. Supports arithmetic, string concatenation,
  structural pattern matching, dynamic lists, and records.
- **Incremental build cache** — `aster build --cache`; SHA-256 keyed, per-backend

### Module system
- Sibling `.aster` file imports, `use mod`, `use mod as alias`, `use mod: name`
- Manifest-configured search roots via `aster.toml` (`[modules].search_roots`)
- `[dependencies]` table with path-based local dependency resolution
- `--dep NAME=PATH` and `--search-root PATH` CLI flags
- Package naming (`[package].name`) and parent-directory dotted import resolution
- Lockfile support (`aster lock` / `aster build --lockfile`)

### Tooling
- **`aster test`** — discovers `test_*.aster`, runs `fn test_*()`, reports pass/fail
- **`aster bench`** — discovers `bench_*.aster`, runs `fn bench_*()`, reports mean/min/max
- **`aster doc`** — extracts `##` doc comments from `pub` declarations, emits Markdown
- **Error index** — `docs/ERROR-INDEX.md`: 55 named errors (PAR/SEM/INT/VM/MOD/LCK/CLI)
- **`aster pkg`** — package manager (`init`, `check`, `build`, `list`)
- **Language Server (LSP)** — supports diagnostics, hover, go-to-definition, formatting, and completion
- **VS Code Extension** — provides syntax highlighting and LSP integration for `.aster` files

### Standard library

**Native modules** (backed by Python stdlib, no `.aster` files needed):

| Module | Description |
|--------|-------------|
| `math` | Trig, exp/log, gcd/lcm, sign/clamp, constants, is_nan/is_inf |
| `str` | Inspection, transformation, split/join, search, to_int/to_float |
| `std` | type_of, panic, todo, input, exit, env, args, assert |
| `list` | map/filter/reduce, sort, aggregate, range, zip/enumerate/unique |
| `io` | read/write/append files, list_dir, mkdir, delete, print_err |
| `random` | random, rand_int, rand_float, choice, shuffle, sample, seed |
| `time` | now, now_ms, monotonic, sleep, strftime, clock |
| `linalg` | Vectors and matrices |
| `socket` | Raw TCP/UDP socket operations |

**Source-based stdlib** (`.aster` files in `src/aster_lang/stdlib/`):

| Module | Description |
|--------|-------------|
| `net` | High-level TCP client/server built on `socket` |
| `http` | HTTP/1.1 client and server built on `net` |
| `path` | String-based path manipulation (no filesystem I/O) |

### Language features
- Fixed-width unsigned integers: `Nibble`/`Byte`/`Word`/`DWord`/`QWord` with bitwise ops
- `FloatValue` runtime type and `FloatType` semantic type (used by `math` module)
- Ownership/borrow prototype: `&T`, `&mut T`, `*own T`, `*shared T`, `*weak T`, `*raw T`
- Trait/impl surface syntax; `impl Trait for Type` validates method presence and arity
- Generic function type parameters with trait bounds
- Effect tracking prototype (`effect Name`, `!name` call-site annotations)
- Lambda expressions (closures) across all pipeline stages
- Typed local bindings (`x: Int := 1`), destructuring, or-patterns

### Documentation and examples
- 20 beginner tutorials in `tutorials/`
- 13 progressively complex runnable programs in `examples/programs/`
- Language reference, ownership guide, FFI guide, toolchain docs
- Standard library reference docs (one page per module)
- Railroad diagrams for the language grammar

## What does not yet exist
- Float literal syntax in the parser/lexer (floats reachable only via native module returns)
- Comment-preserving formatting (needs CST/trivia-aware work)
- Full C backend feature parity (closures, lists, records, and FFI pending)
- Non-trailing rest patterns; nested mixed structural or-patterns
- Version-constrained package registry (`aster pkg` currently path-only)

## Current recommendation

The toolchain is feature-complete for most use cases. Immediate next steps depend on goals:
- **Float literals** — extend lexer/parser for `1.5`, `3.14e-2`, etc.
- **C backend expansion** — implement closures and collections in the native runtime.
- **LSP enhancements** — find references, rename, and semantic tokens
