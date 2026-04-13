# TASK STATUS

## Active stream
Stdlib and tooling polish — path/net/http stdlib tests and bug fixes, bench runner.

## Completed
- lexer, parser, AST, semantic analyzer, interpreter, formatter, REPL, and Python transpiler
- match statements with all pattern forms (literal, wildcard, binding, tuple, list, record, or-patterns, trailing rest)
- local destructuring bindings (tuple, list, record), including trailing list rest capture
- or-pattern variants: non-binding, binding, structural, structural binding or-patterns with nested-if extraction
- string built-ins and collection basics; `ord`, `ascii_bytes`, `unicode_bytes`
- fixed-width unsigned integers: `Nibble`/`Byte`/`Word`/`DWord`/`QWord` with cast builtins and bitwise operators
- sibling `.aster` module imports (`use mod`, `use mod as alias`, `use mod: name`)
- `pub`-aware exports for imported top-level functions, bindings, and type aliases
- parent package-root lookup for dotted imports
- manifest-configured module search roots via `aster.toml`
- manifest `[dependencies]` table with path-based local dependency resolution
- `--dep NAME=PATH` and `--search-root PATH` CLI flags across `run`/`check`/`build`/`test`/`bench`
- manifest package identity (`[package].name`) for current-package import prefixes
- `typealias` declarations registered in symbol table; `pub typealias` exported/importable
- qualified type names (`mod.Vec`, `alias.Vec`) resolvable in type annotations
- typed non-`mut` local bindings (`x: Int := 1`)
- `Fn(...) -> ...` type expressions parsed, formatted, and validated
- ownership/borrow surface syntax parsed and formatted: `&T`, `&mut T`, `*own T`, etc.
- ownership/borrow checking prototype (opt-in: `--ownership off|warn|deny`; default off)
- expression-level borrow `&x` / `&mut x` and deref `*expr` across semantics, interpreter, VM
- `&mut` parameter mutation of caller bindings, including nested and computed targets
- trait/impl surface syntax parsed and formatted; `impl Trait for Type` validates method presence and arity
- generic function type parameters with trait bounds; call-site trait method resolution
- trait bounds validated against imported traits (named and qualified namespace imports)
- effect tracking prototype (`effect Name`, `!name` annotations)
- ownership/borrow checking prototype: move semantics, use-after-move, conflict detection
- lambda expressions (closures) across parser, semantic, interpreter, formatter, VM
- AST pretty-printer (`aster ast <file>`)
- typed HIR debug output (`aster hir <file>`)
- experimental bytecode VM backend (`aster vm <file>` / `aster build --backend vm`)
- VM: full language coverage (match, closures, imports, borrows, for/while, break/continue)
- VM: module imports across `.aster` sibling files and manifest/dependency resolution
- VM: short-circuit `and`/`or`; list/tuple/record literals and indexing; member access and assignment
- VM build artifacts: serialized `*.asterbc.json` with format/version/SHA-256 and optional HMAC; binary encoding
- placeholder C backend adapter (emits stub `.c` file; full implementation deferred)
- incremental build cache (`aster build --cache`; SHA-256 keyed; Python and VM backends)
- `aster check/build --types loose|strict` for optional strict unknown-type rejection
- `aster backends` command to list available build backends
- `aster run --backend vm` routes standard run path through VM
- `aster build --out-dir DIR` / `--clean` build output controls
- lockfile support (`aster lock`, `aster check/build --lockfile`)
- `aster test` — discovers `test_*.aster`, runs `fn test_*()`, reports pass/fail
- `aster bench` — discovers `bench_*.aster`, runs `fn bench_*()`, reports mean/min/max timing
- `aster doc` — extracts `##` doc comments from `pub` declarations, emits Markdown
- error index — `docs/ERROR-INDEX.md`: 55 named errors (PAR/SEM/INT/VM/MOD/LCK/CLI)
- `aster pkg` — package manager: `init`, `check`, `build`, `list`; semver-aware manifest
- native stdlib: `math`, `str`, `std`, `list`, `io`, `random`, `time`, `linalg`, `socket`
- source-based stdlib: `net` (TCP client/server), `http` (HTTP/1.1 client/server), `path` (path manipulation)
- `str.lstrip`/`str.rstrip` extended to accept optional `chars` argument
- `FloatValue` runtime type and `FloatType` semantic type; used by `math` module returns
- 20 beginner tutorials (`tutorials/`) and 13 runnable programs (`examples/programs/`)
- standard library reference docs (one page per module including `path`)

## In progress
- float literal syntax (parser/lexer for `1.5`, `3.14e-2`, etc.) — not yet started
- C backend implementation (AsterValue runtime, codegen, `cc` harness) — spike scoped; not started

## Blocked
- none

## Next recommended task
Float literal syntax: extend the lexer to emit a `FLOAT` token, the parser to produce
`FloatLiteral` AST nodes, and the interpreter/VM/semantic to use `FloatType` and `FloatValue`.

## Risks
- `str.lstrip`/`rstrip` chars stripping uses Python semantics (strips any char in the set, not the literal prefix/suffix)
- inline `fn` literal expressions as call arguments are not yet parsed (use named functions instead)
- float literals not yet in the language grammar (floats reachable only via native module return values)
- comment-preserving formatting needs CST/trivia-aware implementation
- nested/mixed structural or-patterns inside tuple/list elements not yet tested in the compiler
- rest patterns limited to a single trailing `*name` in tuple/list patterns
- `aster pkg` is path-only; no version constraints, registry, or lock file enforcement
- VM artifacts fixed at schema version 1; migration path not yet designed
