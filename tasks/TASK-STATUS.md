# TASK STATUS

## Active stream
Ownership and references surface syntax, starting with parse/format/type-resolution support for `&T`, `&mut T`, and `*own/*shared/*weak/*raw T` in type annotations.

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

## In progress
- none

## Blocked
- none

## Next recommended task
Backend follow-through: expand the VM backend toward interpreter parity (mutability enforcement, more assignment targets, and destructuring bindings), and then decide whether to integrate the VM as an optional backend for `aster run/build`.

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
