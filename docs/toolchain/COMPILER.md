# Compiler Design Notes

## Goal

Compile Aster from source to an analyzable intermediate form and eventually to bytecode and/or native code.

## Current Backends

This repository currently includes:

- a Python transpiler (`src/aster_lang/compiler.py`)
- an experimental bytecode VM backend (`src/aster_lang/bytecode.py`, `src/aster_lang/vm.py`)

The VM backend is documented in `docs/toolchain/VM.md`.

## Recommended pipeline

1. source text
2. tokens
3. concrete syntax tree
4. abstract syntax tree
5. name resolution
6. typed high-level IR
7. lowered ownership/effect-aware IR
8. backend IR
9. bytecode or native artifact

## Why multiple IR levels

Aster has:
- expressive syntax
- structured patterns
- ownership and reference forms
- effect tracking aspirations

A staged compiler will make the language easier to validate and extend.

## Backend interface layer (multi-backend plan)

Goal: support many backends (VM, C, LLVM, Wasm, JavaScript) using a standard IR
and a stable adapter interface.

Principles:
- Define a backend-agnostic IR contract (types, control flow, ownership annotations).
- Keep backend adapters thin: translate from the standard IR into target-specific IR.
- Preserve a single semantic source of truth (no backend-specific reinterpretation).

Interface sketch:
- `BackendAdapter` consumes the standard IR module plus metadata:
  - target platform info (endianness, pointer size, calling convention)
  - artifact settings (format, compression, signing)
- `BackendAdapter` outputs an artifact bundle (bytecode/binary/library/etc.).
- Validation hooks run before and after adapter translation to catch IR drift.

This interface layer will be the anchor for future targets while keeping the
front-end stable.

## Native backend feasibility study

Goal: identify the shortest path to a native backend target and validate the
standard IR + adapter boundary.

Scope for the feasibility pass:
- Pick a first native target (LLVM IR or C) based on tooling availability.
- Identify the minimum runtime services needed (allocator, string, list/tuple/record).
- Define the calling convention for Aster functions and closures.
- Map the standard IR control-flow and ownership annotations to the target.
- Produce a small end-to-end spike: `main()` with arithmetic, calls, and a loop.

Decision criteria:
- Toolchain footprint (dependency size, platform availability).
- Debuggability and ease of inspection.
- ABI stability and FFI surface for future interop.

## Ownership lowering strategy

Goal: make ownership/borrow semantics explicit in MIR so backends can enforce or optimize
without re-deriving intent from surface syntax.

### Inputs
- Typed HIR expressions and statements.
- Ownership-aware types (`*own T`, `*shared T`, `*weak T`, `*raw T`, `&T`, `&mut T`).
- Semantic ownership/borrow diagnostics already emitted in `aster check`/`build`.

### MIR additions (planned)
- `MMove(target, value)` for move-only transfers (bindings, arguments, returns).
- `MBorrow(target, kind, temp)` where kind is `shared`/`mut`.
- `MEndBorrow(temp)` at scope exits (or structured regions).
- `MDrop(value)` for scope-end drops of owned values.

### Lowering rules (sketch)
- Bindings:
  - `let x := expr` where `expr` is `*own T` emits `MMove(x, expr)`.
  - Non-move types stay as `MLet`.
- Calls:
  - Passing a move-only value emits `MMove(temp, arg)` then uses `temp`.
  - Implicit borrow arguments (`T` passed to `&T`) emit `MBorrow` in the call site.
- Borrow expressions:
  - `&x` / `&mut x` emit `MBorrow` and produce a ref temp used by the expression.
  - Borrow lifetime is scoped to the smallest enclosing statement block.
- Returns:
  - Returning an owned value emits `MMove` into the return slot.
  - Returning references emits no move but emits borrow checks at the call boundary.

### Scope management
- Each statement block introduces a borrow region.
- On region exit, emit `MEndBorrow` for active borrows and `MDrop` for owned locals.
- This mirrors the current semantic borrow scope stack (prototype) and keeps runtime
  enforcement optional for the VM backend while enabling future native lowering.

### Notes
- The first implementation can be metadata-only (emit nodes but keep VM ignoring them).
- This keeps the VM surface stable while enabling a future pass to enforce
  drops/moves or to generate reference counting for `*shared` values.
