# TASK STATUS

## Active stream
Ownership and references, now including expression-level `&x` / `&mut x` borrowing plus `*expr` deref, and tightening type checking toward backend-ready strictness.

## Completed
- lexer, parser, AST, semantic analyzer, interpreter, formatter, REPL, and Python transpiler
- match statements with literal, wildcard, and binding patterns
- string built-ins and collection basics
- sibling `.aster` module imports through `use mod`, `use mod as alias`, and `use mod: name`
- tuple patterns in match arms, including nested tuple bindings
- list patterns in match arms, including nested list bindings
- record patterns in match arms, including shorthand field bindings
- or-patterns in match arms for non-binding alternatives
- irrefutable binding or-patterns in match arms (e.g. `x | x`) compiled correctly
- structural match arm conditions compiled (list/tuple/record patterns emit real Python conditions)
- structural binding or-patterns (e.g. `[x, 0] | [0, x]`) compiled with nested if/else binding extraction
- trailing rest patterns in tuple and list match arms
- local tuple/list/record destructuring bindings, including trailing list rest capture
- compiler transpiler emits record destructuring bindings using field extraction
- ownership lowering strategy documented in compiler notes
- backend interface layer documented for multi-backend support
- VM build now supports optional compressed binary artifacts
- native backend feasibility study scoped in compiler notes
- CLI and semantic diagnostics for missing modules and cyclic imports
- `pub`-aware exports for imported functions and top-level bindings
- parent package-root lookup for dotted imports
- manifest-configured module search roots via `aster.toml`
- manifest package identity for current-package import prefixes
- manifest `[dependencies]` table with `path`-based local dependency resolution
- `--dep NAME=PATH` and `--search-root PATH` CLI flags on `aster run` to override/extend manifest resolution
- `aster check <file>` CLI command for semantic-only analysis (supports the same `--dep/--search-root` flags)
- `aster build <file>` CLI command now supports the same `--dep/--search-root` flags for consistent import checking
- `aster build <file>` emits runnable Python in `__aster_build__/` (modules compiled under `_aster/` to avoid stdlib name collisions)
- `typealias` declarations registered in the symbol table; `pub typealias` exported and importable across modules; imported aliases usable in type annotations
- AST pretty-printer (`aster_lang.ast_printer.dump`) with `aster ast <file>` CLI subcommand
- continuity docs refreshed to match the current implementation
- ownership/reference type annotation syntax parsed, formatted, and resolved (`&T`, `&mut T`, `*own T`, `*shared T`, `*weak T`, `*raw T`)
- `Fn(...) -> ...` type expressions are parseable (matching formatter + grammar)
- ownership/borrow checking prototype warnings emitted by `aster check` / `aster build` when ownership syntax is used (non-fatal)
- typed HIR debug output (`aster hir <file>`) to support upcoming backend work
- experimental bytecode VM backend (`aster vm <file>`) for a small subset of the language
- VM backend now supports `if/else` and `while` (still missing `match`, `for`, destructuring, break/continue)
- VM backend now supports list/tuple/record literals plus indexing and record member access
- VM backend now supports `match` for wildcard, binding, literal, literal-or, plus tuple/list/record patterns with trailing rest and structural or-patterns
- documented the experimental VM backend (`docs/toolchain/VM.md`)
- VM backend now supports `use` imports across `.aster` modules (sibling/manifest/dependency resolution)
- VM backend now supports `for` loops over list/tuple/range plus `break`/`continue`
- assignment to member/index lvalues implemented for both interpreter and VM (identifier receivers only)
- VM backend now supports short-circuit `and` / `or`
- lambda expressions (closures) supported across parser, semantic analysis, interpreter, formatter, and VM backend
- trait/impl surface syntax parsed and formatted; semantic prototype validates `impl Trait for Type` method presence/arity
- generic function type parameters parsed/formatted; semantic resolves type parameters as type variables and validates simple trait bounds
- trait bounds in generics validate against imported traits (named and qualified namespace imports)
- `impl` trait validation supports qualified imported traits (e.g. `impl traits.Show for Int:` after `use traits`)
- semantic analysis records generic type parameters and their trait-bound strings on declarations for later phases (ownership)
- semantic analysis instantiates generic function calls and generic type aliases (prototype substitution) to keep `aster check/build` usable without ownership
- semantic analysis now accepts `String + String` and infers best-effort return types for block lambdas (helps higher-order code type-check)
- parser now supports typed non-`mut` local bindings (`x: Int := 1`), matching the documented surface syntax
- fixed-width unsigned integer types added (`Nibble`/`Byte`/`Word`/`DWord`/`QWord`) with cast builtins and bitwise operators (`& | ^ ~ << >>`) across lexer/parser/formatter/semantic/interpreter/VM
- ownership/borrow surface diagnostics are now opt-in via `aster check/build --ownership off|warn|deny` (default: off)
- expression-level borrow `&x` / `&mut x` and deref `*expr` implemented across semantics, interpreter, and VM backend; `&mut` parameters can mutate caller bindings
- VM backend now supports borrowed member/index targets for `&mut r.x` and `&mut xs[i]`
- nested identifier-rooted member/index borrow and assignment targets now work across semantics, interpreter, and VM (`r.inner.x`, `r.items[0]`, `&mut r.inner.x`)
- computed-root member/index borrow and assignment targets now work across parser, semantics, interpreter, formatter, and VM (`&mut {x: 1}.x`, `&mut [1, 2][0]`, `{x: 1}.x <- 7`)
- `aster run --backend vm` now routes the standard run command through the experimental VM backend while preserving `--dep/--search-root`
- `aster build --backend vm` now emits a runnable Python launcher, a serialized `*.asterbc.json` bytecode artifact, and a minimal bundled VM runtime subset
- `vm.py` now reuses `vm_runtime.py` as the single runtime source of truth instead of maintaining a duplicate VM implementation
- serialized VM bytecode artifacts now carry explicit format/version markers and the loader rejects incompatible artifacts clearly
- serialized VM bytecode artifacts now also carry SHA-256 integrity metadata and the loader rejects tampered artifacts before decode
- VM artifact loading now has an explicit supported-version window and reports too-old vs too-new schema versions separately
- VM artifacts can optionally include an HMAC-SHA256 signature when `ASTER_VM_SIGNING_KEY` is provided; the loader verifies it before decode
- VM `max`/`min` now match interpreter arity and integer-only behavior
- VM `print` now matches interpreter arity (single argument) and error messaging
- VM `int()` now mirrors interpreter conversions and errors (Bool/String/Int handling)
- VM `len()` now matches interpreter support (String/List/Tuple only)
- VM `ascii_bytes` output and errors now have parity coverage
- `unicode_bytes` builtin added across semantics, interpreter, and VM (UTF-8 bytes)
- fixed-width equality (`byte(255) == 255`) now has explicit interpreter/VM parity coverage
- VM equality now uses deep structural comparison for lists/tuples/records
- record `len()` now matches interpreter/VM behavior (records supported)
- VM `range()` now explicitly rejects Bool inputs, matching interpreter behavior
- VM error messages for `len()`/`range()` now match interpreter wording
- VM `len()` error messages now use interpreter type names (e.g. `IntValue`)
- VM `unicode_bytes` now masks output bytes (Byte-like ints) to match `ascii_bytes` semantics
- semantic errors for `ord`/`ascii_bytes`/`unicode_bytes` now match interpreter wording (`expects String`)
- record string indexing (`r["x"]`) now works in both interpreter and VM
- VM now rejects `&mut` borrows of immutable bindings and assignment through immutable references
- VM now enforces `mut` on globals and captured variables (assign and `&mut` require `mut`)
- VM index errors now match interpreter wording (`Cannot index <Type> with <Type>`)
- VM member-access errors now match interpreter wording (non-record member and missing field)
- VM index assignment errors now match interpreter wording (`Unsupported index reference assignment`)
- VM index reference errors now match interpreter wording (`Index reference requires Int or String index`)
- VM module member errors now match interpreter wording (missing export vs non-module member access)
- VM member assignment errors now match interpreter wording (`Cannot access member of <Type>`)
- VM index assignment now validates index type like interpreter (`Index reference requires Int or String index`)
- VM index assignment base errors now match interpreter wording (`Unsupported index reference assignment`)
- fixed-width numeric comparison parity now covered in interpreter and VM tests
- VM unsupported assignment target wording now matches interpreter
- `aster check/build --types loose|strict` added to optionally reject unknown-typed arithmetic/bitwise uses in strict mode
- added a beginner tutorial track: 20 tutorials plus 6 progressively more complex runnable programs under `tutorials/` and `tutorials/programs/`

## In progress
- native backend feasibility study (C-first spike plan, IR mapping, runtime stub/ABI sketch)
- caching/incremental compilation notes drafted
- caching/incremental next-actions checklist added
- native backend feasibility notes doc created
- native backend feasibility next-actions checklist added
- native backend feasibility checklist added to NEXT-STEPS
- native backend feasibility open-questions expanded
- native backend feasibility checklist updated with debug-output decision
- placeholder C backend adapter registered (not implemented yet)
- build docs updated to mention the placeholder `c` backend
- README updated for placeholder `c` backend
- backend registry validation tests cover None format
- backend registry now errors with available backends on unknown names
- backend registry tests cover available-backend listing in errors
- native backend feasibility status clarified (scoped, spike not started)
- placeholder C backend now emits a stub `.c` file
- native backend notes updated with C stub output detail
- user-facing docs mention the C stub output
- user docs highlight REPL/VM learning flow vs backend builds
- user guide now mentions `aster vm` direct VM command
- CLI test added for `aster vm`
- backend adapter follow-ups added to NEXT-STEPS
- backend adapter `aster backends` follow-up added
- `aster backends` command implemented and documented
- VM artifact format option documented in user guides
- backend registry tests added for adapter scaffolding
- backend registry validates artifact formats
- developer guide updated with backend interface modules

## Blocked
- none

## Next recommended task
Backend follow-through: expand the VM backend toward interpreter parity and decide the next artifact step beyond schema/integrity/signing checks, such as compression or a binary encoding.
Note: keep JSON VM artifacts for now and check back with the user before changing formats.

## Risks
- imported module symbols use lightweight semantic export inference, not full cross-module type checking
- comment-preserving formatting still needs CST/trivia-aware work
- list pattern arity diagnostics currently rely on literal-backed subject length inference rather than full shape typing
- record pattern diagnostics currently rely on literal-backed subject field inference rather than full record typing
- export visibility covers functions, top-level bindings, and type aliases; qualified type names (e.g. `mod.Vec` and `alias.Vec`) are resolvable in type annotations via namespace imports
- nested or mixed structural or-patterns (or-patterns inside tuple/list elements) are not yet tested in the compiler
- rest patterns are currently limited to a single trailing `*name` in tuple/list patterns
- type annotations on destructuring `mut` bindings are now a parse error (grammar-level rejection; only simple `mut name: Type := expr` is valid)
- dependencies are path-only (no version constraint, registry, or lock file)
- lockfile support exists (`aster lock`), but version constraints/registry support are still not implemented
- package identity currently only supports the current package prefix, not published package resolution

## Notes
Keep examples small and executable.
Keep docs synchronized with implementation.
