# STATUS

## Repository status
Phases 2–5 are largely complete. The language can parse, format, analyze, execute, and interact via the REPL, with file-based module imports, manifest-configured module roots and dependency mapping, package naming, parent package-root lookup, `pub`-aware exports for functions/bindings/type aliases, local destructuring bindings, binding or-patterns, structural match arm compilation, qualified type names in annotations, and an AST pretty-printer.

## Next focus (short)
- Decide the comment-preserving formatter strategy (CST/trivia model) and begin implementation.
- Continue VM parity work (mutability enforcement, destructuring bindings, remaining runtime gaps).
- Keep JSON VM artifacts for now; revisit compression/binary encoding later (check back before changing formats).

## What exists
- project layout and setup scripts
- Python package skeleton with CLI (`run`, `fmt`, `check`, `build`, `ast`, `repl`, `version`)
- **Complete lexer** with indentation handling (INDENT/DEDENT tokens)
- **Complete parser** with Pratt parsing for expressions; type annotations on destructuring bindings rejected at parse level
- **Comprehensive AST** with all node types (declarations, statements, expressions, types)
- **Complete semantic analyzer** with symbol tables and type checking
- **Complete interpreter** with runtime execution engine
- **Complete formatter** with idempotent canonical output
- **Match statement** with literal, wildcard, binding, tuple, list, record, or-patterns (including binding or-patterns), and trailing rest patterns
- **Local destructuring bindings** for tuples, lists, and records
- **Basic module imports** for sibling `.aster` files via `use mod`, `use mod as alias`, and `use mod: name`
- **Manifest-configured module roots** via `aster.toml` (`[modules].search_roots`)
- **Manifest `[dependencies]`** table with local path entries; `--dep NAME=PATH` and `--search-root PATH` CLI overrides on `run`/`check`/`build`
- **Manifest package naming** via `[package].name`
- **Parent package-root lookup** for dotted imports such as `use lib.helpers`
- **`pub`-aware exports** for imported top-level functions, bindings, and type aliases
- **`typealias` declarations** registered in symbol table; `pub typealias` exported and importable; qualified type names (`mod.Vec`, `alias.Vec`) usable in annotations
- **AST pretty-printer** (`aster ast <file>`) for debugging parse output
- **Interactive REPL** (`aster repl`) with persistent state and multi-line input
- **Selectable run backend**: `aster run --backend interpreter|vm <file>`
- **Selectable build backend**: `aster build --backend python|vm <file>`
- **VM build artifacts**: `aster build --backend vm` emits a runnable launcher plus a serialized, versioned, integrity-checked `*.asterbc.json` bytecode program and minimal bundled VM runtime; the loader currently supports schema version `1`, with optional HMAC signing via `ASTER_VM_SIGNING_KEY`
- **String operations**: `+` concatenation, `len()`, `str()`, `int()` built-ins
- **Fixed-width unsigned integers**: `Nibble`/`Byte`/`Word`/`DWord`/`QWord` plus cast builtins (`nibble/byte/word/dword/qword`) and bitwise ops (`& | ^ ~ << >>`)
- **694 passing tests** covering parser, semantics, interpreter, formatter, CLI, compiler, REPL, AST printer, typed HIR, and the experimental bytecode VM backend
- beginner-friendly tutorials and runnable example programs under `tutorials/` (20 tutorials; explicitly avoiding ownership/borrow enforcement by default)
- progressively more complex multi-file example programs under `examples/programs/`
- language and toolchain docs
- Bottlecaps-compatible EBNF grammar files
- AI workflow docs and recovery docs
- **Python transpiler backend** with structural match arm conditions (list/tuple/record patterns), binding or-pattern compilation with nested-if extraction
- **Recursive build output**: `aster build` emits a runnable `__aster_build__/` dir with compiled modules under `_aster/`
- **Build output controls**: `aster build --out-dir DIR` and `--clean`
- **Lockfile support**: `aster lock` writes `aster.lock`; `aster check/build --lockfile` use a pinned module resolution config

## Lexer Features
- TokenKind enum with all language tokens (keywords, operators, literals)
- Source location tracking (line, column, offset)
- Indentation-aware tokenization (Python-like blocks)
- String literals with escape sequences
- Comment handling
- All Aster operators (:=, <-, ->, ==, !=, <=, >=, etc.)

## Parser Features
- Recursive descent parsing with Pratt expression parsing
- All declarations: functions, type aliases, imports, top-level bindings
- All statements: bindings, assign, return, if/else, while, for, break, continue
- All expressions: binary, unary, call, index, member access, literals
- Collection expressions: lists, tuples, records
- Type expressions: simple types, function types, qualified names
- Successfully parses example programs (hello.aster, sum_to.aster)

## Semantic Analysis Features
- Symbol table with hierarchical scopes
- Name resolution and duplicate detection
- Type inference for all expressions
- Type checking for operators, assignments, function calls
- Imported function signatures resolved from sibling modules
- Missing-module and cyclic-import diagnostics surfaced through semantic analysis and CLI execution
- Imports resolve only `pub` top-level declarations from sibling modules
- Manifest-configured module roots resolved from `aster.toml`
- Current-package import prefixes resolved through `package.name`
- Module resolution can search parent directories for dotted package roots
- Or-patterns for non-binding and binding alternatives (name-consistency validated)
- Trailing rest patterns for tuple and list matches
- Tuple, list, and record pattern bindings with arity/field validation
- Tuple, list, and record destructuring in local bindings
- Destructuring binding diagnostics for arity and missing fields
- `typealias` declarations registered in symbol table; `pub typealias` exported
- Qualified type names (`mod.Vec`, `alias.Vec`) resolved in type annotations via namespace import exports
- Mutability checking (immutable vs mutable variables)
- Control flow validation (if/while require Bool conditions)
- Built-in functions (print)
- Comprehensive error reporting

## Interpreter Features
- Runtime value model: Int, String, Bool, Nil, List, Tuple, Record, Function
- Borrow expressions `&x` / `&mut x` with implicit deref for borrowed bindings; `&mut` parameters can mutate caller bindings, including nested and computed postfix targets like `&mut r.inner.x`, `&mut {x: 1}.x`, and `&mut make_list()[0]`
- Environment with variable bindings and mutability tracking
- Expression evaluation: arithmetic, comparison, logical, unary operators
- Statement execution: bindings, assign, return, if/else, while, for, break, continue
- Function calls with closures and parameter passing
- Built-in functions (print with newline separation), plus string byte helpers (`ord`, `ascii_bytes`, `unicode_bytes`)
- Collection operations: list/tuple creation, indexing, record member access
- Tuple-pattern destructuring with nested bindings in match arms
- List-pattern destructuring with nested bindings in match arms
- Record-pattern destructuring with nested bindings in match arms
- Or-pattern matching for multiple alternatives in a single arm
- Trailing rest-pattern matching for tuples and lists
- Local tuple/list/record destructuring bindings, including list rest capture
- Module namespace values with named and aliased imports
- Missing-module and cyclic-import errors reported from `aster run`
- Private top-level declarations remain module-local at runtime
- Manifest-configured project roots and module search paths
- Manifest-configured current package prefix imports
- Parent-directory package-root resolution for dotted imports
- Auto-execution of main() function
- Recursive function support (factorial, fibonacci work correctly)
- Error reporting with source node context

## What does not yet exist
- compiler backend (bytecode or native)
- advanced ownership analysis (basic mutability checking only)
- advanced collections (sets, maps)
- comment-preserving formatting (needs CST/trivia-aware implementation work)
- richer pattern forms such as non-trailing rest patterns
- trait resolution and effect tracking prototypes

## Formatter Features
- All declaration types formatted (fn, bindings, typealias, use)
- All statement types formatted (bindings, assign, if/else, while, for, break, continue, return)
- All expression types formatted with correct operator precedence parenthesisation
- Type expressions (simple, generic, function types)
- 4-space indentation, blank lines between declarations
- Idempotent: `format(format(x)) == format(x)`
- `aster fmt <file>` command works end-to-end

## Current recommendation
Next steps (choose based on goals):
1. **Formatter**: comment preservation (CST/trivia-aware formatting)
2. **Ownership analysis prototype**: move semantics and lifetime tracking
3. **Compiler backend**: typed IR and bytecode or native backend exploration
- Added semantic import resolution for named imports and missing-export diagnostics
- Wired `aster run <file>` to resolve imports relative to the executed file
- Added runnable import examples and updated user-facing docs
- Added tuple-pattern parsing, formatting, semantic checks, and runtime destructuring
- Added list-pattern parsing, formatting, semantic checks, and runtime destructuring
- Added record-pattern parsing, formatting, semantic checks, and runtime destructuring
- Improved missing-module and cyclic-import diagnostics in semantic analysis and CLI execution
- Added `pub`-aware exports for imported functions and top-level bindings
- Added or-pattern parsing, formatting, semantic checks, and runtime matching
- Added trailing rest-pattern parsing, formatting, semantic checks, and runtime matching
- Added parent package-root module resolution for CLI, interpreter, and semantic analysis
- Added local tuple/list/record destructuring bindings across parser, formatter, semantics, interpreter, and transpiler
- Compiler transpiler now emits record destructuring bindings via temp extraction and field checks
- Documented ownership lowering strategy in compiler design notes
- Documented the planned backend interface layer for multi-backend support
- Added a backend adapter scaffold (`BackendAdapter`, `BackendArtifact`, registry)
- Wired default backend adapters into the CLI build path
- Documented `--vm-artifact-format` in user-facing guides
- Added basic backend registry tests
- Backend registry now validates artifact formats per adapter
- Developer guide updated for backend interface modules
- Backend interface layer marked complete (adapter interface + CLI wiring)
- Backend interface layer marked in progress in next-steps tracking
- Added optional compressed binary VM artifacts (`--vm-artifact-format binary`)
- Scoped a native backend feasibility study in compiler notes
- Proposed C as the initial native backend feasibility target
- Added a concrete C feasibility spike plan and initial IR mapping notes
- Added a C runtime stub sketch for the native backend feasibility spike
- Added an ABI sketch for the native backend feasibility spike
- Added native backend feasibility notes doc
- Added next actions checklist for native backend feasibility
- Added native backend feasibility checklist to NEXT-STEPS
- Added debug-output question to native backend open issues
- Added debug-output decision to native backend next steps
- Added a placeholder C backend adapter (returns not implemented)
- Documented `c` backend placeholder in build CLI docs
- Updated README backend list for the placeholder C backend
- Added backend registry test for None-format validation
- Backend registry reports unknown backend names with available list
- Added `aster.toml`-driven module search roots shared by runtime and semantic analysis
- Added `package.name` support for current-package import prefixes
- Full suite currently passes with 694 tests
