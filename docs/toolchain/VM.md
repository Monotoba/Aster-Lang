# Aster Bytecode VM (Experimental)

This repository includes an **experimental bytecode backend** and a **tiny stack VM**.
It is intentionally small and incomplete: the goal is to create a stable surface to grow
compiler/backend work without changing the rest of the language implementation.

## How To Run

Run a program using the VM backend:

```bash
python -m aster_lang vm path/to/main.aster
```

Or select it through the main run command:

```bash
python -m aster_lang run path/to/main.aster --backend vm
```

The command executes `main()` and prints captured `print(...)` output to stdout.

You can also build a runnable VM artifact bundle:

```bash
python -m aster_lang build path/to/main.aster --backend vm
```

That build emits a Python launcher plus a serialized `main.asterbc.json` bytecode artifact, and
bundles a minimal local `aster_lang` runtime subset (`__init__.py`, `bytecode.py`,
`vm_runtime.py`) inside the output directory. The artifact root carries explicit `format`,
`version`, and SHA-256 integrity metadata; the loader currently accepts schema version `1` only
and reports older/newer artifacts distinctly before decode.
If `ASTER_VM_SIGNING_KEY` is set in the environment, the build embeds an HMAC-SHA256 signature
over the artifact payload and the launcher verifies it using the same key.

### Binary/compressed artifacts

Use `--vm-artifact-format binary` to emit a compressed binary artifact:

```bash
python -m aster_lang build path/to/main.aster --backend vm --vm-artifact-format binary
```

This produces `main.asterbc` instead of `main.asterbc.json`. The binary format is:
- magic header `ASTERBC` + version byte
- zlib-compressed canonical JSON payload (same schema as the JSON artifact)

Integrity/signature checks are still performed after decompression.

## Artifact Compatibility Policy

- The bytecode schema version increments on any incompatible change to the serialized layout.
- The loader accepts versions in the inclusive window
  [`BYTECODE_MIN_SUPPORTED_VERSION`, `BYTECODE_MAX_SUPPORTED_VERSION`], and reports
  too-old vs too-new artifacts distinctly before decode.
- When support for older artifacts is dropped, the minimum supported version is raised and the
  compatibility note in this doc should be updated alongside tests.
- Signatures are optional and only applied when `ASTER_VM_SIGNING_KEY` is provided; unsigned
  artifacts still use integrity hashes and version checks.

## Current Status

The VM backend is implemented in:

- `src/aster_lang/bytecode.py` (instruction set and containers)
- `src/aster_lang/vm.py` (AST-to-bytecode compiler + public entry points)
- `src/aster_lang/vm_runtime.py` (VM runtime / execution engine)

It compiles directly from AST (plus semantic analysis for early errors) into bytecode.
There is no separate IR yet; this is a stepping stone toward a real compiler pipeline.

## Supported Subset (As Of Today)

Statements:

- `fn` declarations
- local bindings: `x := expr`, `mut x := expr`, and destructuring bindings
- mutability is enforced for reassignment to identifier bindings
- assignment to identifiers: `x <- expr`
- assignment to index/member lvalues when the receiver is an identifier:
  - `xs[i] <- v` (lists and records)
  - `r.x <- v` (records)
  - nested identifier-rooted chains like `r.inner.x <- v` and `r.items[0] <- v`
- `return expr?`
- expression statements (result popped)
- `if/else`
- `while`
- `for x in iterable:` where `iterable` is a list/tuple or the result of `range(...)`
- `break` and `continue` (inside `while` and `for`)
- `match` with:
  - wildcard `_`
  - binding `x`
  - literal patterns (`0`, `"s"`, `true`, `false`, `nil`)
  - or-patterns (`1 | 2`, `[x, 0] | [0, x]`) with consistent bindings
  - tuple/list/record patterns, including trailing rest `*name` for tuple/list

Expressions:

- literals: `Int`, `String`, `Bool`, `nil`
- identifiers
- lambda expressions (closures): `x -> expr`, `(a, b: T) -> expr`, `(x) -> : ...`
- calls to identifier functions (user functions or builtins)
- unary: `-x`, `not x`
- unary: `~x` (bitwise not, Int only)
- borrow/deref: `&x`, `&mut x`, nested and computed postfix targets like `&mut r.x`, `&mut xs[i]`, `&mut r.inner.x`, `&mut {x: 1}.x`, and `*p`
- short-circuit boolean operators: `and`, `or`
- binary arithmetic/comparisons: `+ - * / %`, `== != < <= > >=`
  - `+` supports `Int+Int` and `String+String`
- bitwise operators (Int only): `& | ^ << >>`
- list literals `[a, b, ...]`
- tuple literals `(a, b, ...)`
- record literals `{x: 1, y: 2}`
- index: `xs[i]` for list/tuple, `r["k"]` for record (limited)
- member access: `r.x` for records

Builtins:

- `print(x)` (single argument)
- `len(x)` for `String`, list, tuple, record
- `str(x)`, `int(x)`, `abs(x)`
- `max(a, b)`, `min(a, b)` (Int only)
- `range(n)` and `range(start, stop)` (returns a list of ints)
- `ord(s)` (single-character `String`)
- `ascii_bytes(s)` (ASCII bytes as a list of `Byte`-like ints)
- `unicode_bytes(s)` (UTF-8 bytes as a list of `Byte`-like ints)
- fixed-width cast helpers (Int in, Int out): `nibble(x)`, `byte(x)`, `word(x)`, `dword(x)`, `qword(x)` (wrap by masking)

## Not Supported Yet

- assignment or borrowing for targets outside postfix lvalue chains (for example arbitrary non-lvalue expressions)
- external Python imports (VM only loads `.aster` modules)
- full runtime value model parity with the interpreter (lists/tuples/records exist, but many behaviors are still missing)
- effects/async, traits/impls, ownership enforcement

## Modules and Imports

The VM supports Aster module imports for `.aster` files using the same module-resolution
logic as the rest of the toolchain (manifest roots, dependencies, `--dep`, `--search-root`).

Supported import forms:

- `use helpers`
- `use helpers as h`
- `use helpers: answer, double`

Imported module namespaces are represented as dictionaries of exported values.
Exported functions are represented as function-id strings that the VM can call.

## Bytecode Model

The VM is a **stack machine**:

- most instructions pop operands from the stack and push results
- locals are stored in a per-frame `locals[]` array of mutable cells (so closures can capture locals)
- calls create new frames for user functions

### Key Instructions

Locals:

- `CONST k` push constant `constants[k]`
- `LOAD i` push `locals[i].value` (implicitly deref if the value is a cell reference)
- `STORE i` pop and store into `locals[i]` (writes through if the local currently holds a cell reference)
- `POP` pop and discard

Closures:

- `REF_LOCAL i` push a reference (cell) to `locals[i]`
- `REF_FREE i` push a reference (cell) to a captured free variable
- `REF_GLOBAL k` push a reference (cell) to `globals[constants[k]]`
- `LOAD_FREE i` push the value of captured free variable `i`
- `STORE_FREE i` pop and store into captured free variable `i`
- `DEREF` pop a cell reference and push its value (also used for `*(&x)`-style expressions)
- `STORE_DEREF` pop value and cell reference, then write through the cell
- `MAKE_CLOSURE (fn_k, n)` pop `n` cell refs and push a closure value
- `CALL_VALUE argc` can call either a function-id string or a closure value

Arithmetic/logic:

- `ADD SUB MUL DIV MOD`
- `BIT_AND BIT_OR BIT_XOR SHL SHR`
- `NEG NOT BIT_NOT`
- `EQ NE LT LE GT GE`

Control flow:

- `JMP target`
- `JMP_IF_FALSE target` (pops a condition)
- `RETURN` (pops return value)

Calls:

- `CALL (name_k, argc)` where `constants[name_k]` is a string function name

Collections/access:

- `BUILD_LIST n`, `BUILD_TUPLE n`, `BUILD_RECORD (field_names...)`
- `INDEX`
- `MEMBER name_k`
- `IS_LIST`, `IS_TUPLE`, `IS_RECORD`
- `LEN`
- `HAS_KEY name_k`
- `SLICE_FROM start`

## Known Differences vs Interpreter

- The VM is stricter about supported operations and will raise `VMError` for anything outside the subset.
- `match` is implemented by compiling pattern checks and binding stores; it does not share runtime code with the interpreter.
- Equality currently requires exact runtime type matches (so `1 == "1"` is `false`).
