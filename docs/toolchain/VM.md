# Aster Bytecode VM (Experimental)

This repository includes an **experimental bytecode backend** and a **tiny stack VM**.
It is intentionally small and incomplete: the goal is to create a stable surface to grow
compiler/backend work without changing the rest of the language implementation.

## How To Run

Run a program using the VM backend:

```bash
python -m aster_lang vm path/to/main.aster
```

The command executes `main()` and prints captured `print(...)` output to stdout.

## Current Status

The VM backend is implemented in:

- `src/aster_lang/bytecode.py` (instruction set and containers)
- `src/aster_lang/vm.py` (AST-to-bytecode compiler + VM runtime)

It compiles directly from AST (plus semantic analysis for early errors) into bytecode.
There is no separate IR yet; this is a stepping stone toward a real compiler pipeline.

## Supported Subset (As Of Today)

Statements:

- `fn` declarations
- local bindings: `x := expr` and `mut x := expr` (mutability is not enforced by the VM)
- assignment to identifiers: `x <- expr`
- assignment to index/member lvalues when the receiver is an identifier:
  - `xs[i] <- v` (lists and records)
  - `r.x <- v` (records)
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
- short-circuit boolean operators: `and`, `or`
- binary arithmetic/comparisons: `+ - * / %`, `== != < <= > >=`
  - `+` supports `Int+Int` and `String+String`
- list literals `[a, b, ...]`
- tuple literals `(a, b, ...)`
- record literals `{x: 1, y: 2}`
- index: `xs[i]` for list/tuple, `r["k"]` for record (limited)
- member access: `r.x` for records

Builtins:

- `print(...)` (variadic)
- `len(x)` for list/tuple/record
- `str(x)`, `int(x)`, `abs(x)`
- `max(...)`, `min(...)`
- `range(n)` and `range(start, stop)` (returns a list of ints)

## Not Supported Yet

- assignment to complex targets beyond identifier receivers (e.g. `(get())[0] <- v`)
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
- `LOAD i` push `locals[i]`
- `STORE i` pop and store into `locals[i]`
- `POP` pop and discard

Closures:

- `REF_LOCAL i` push a reference (cell) to `locals[i]`
- `REF_FREE i` push a reference (cell) to a captured free variable
- `LOAD_FREE i` push the value of captured free variable `i`
- `STORE_FREE i` pop and store into captured free variable `i`
- `MAKE_CLOSURE (fn_k, n)` pop `n` cell refs and push a closure value
- `CALL_VALUE argc` can call either a function-id string or a closure value

Arithmetic/logic:

- `ADD SUB MUL DIV MOD`
- `NEG NOT`
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
