# Implementation Plan: Aster C Compiler (GCC)

This plan breaks the C compiler implementation into five measurable milestones.

## Milestone 1: Runtime Foundation ✅
**Goal:** Create the minimal C runtime required for basic execution.
- [x] Implement `aster_runtime.h` with `AsterValue` and `VAL_INT`, `VAL_BOOL`, `VAL_NIL`.
- [x] Implement `aster_runtime.c` with `aster_print`, `aster_add_int`, and `aster_panic`.
- [x] Create a "Hello World" hand-written C program that uses this runtime to verify GCC linkage.

## Milestone 2: MIR Scaffolding ✅
**Goal:** Implement the MIR lowering pass in Python.
- [x] Define the MIR instruction set in `src/aster_lang/mir.py`.
- [x] Implement the `HIR -> MIR` lowering logic.
- [x] Add `aster mir <file>` CLI command to inspect the generated IR.

## Milestone 3: Basic Codegen & Build Harness ✅
**Goal:** Compile a simple "sum" function from Aster to native code.
- [x] Implement `CBackendAdapter` in `src/aster_lang/backend_adapters.py`.
- [x] Implement the C source emitter (MIR -> C text).
- [x] Wire up the GCC invocation to produce a runnable binary.
- [x] Verify with an end-to-end test: `aster build --backend c examples/sum.aster`.

## Milestone 4: Control Flow & Patterns ✅
**Goal:** Support loops, conditionals, and matching.
- [x] Implement C emission for `if`, `while`, and `return`. (Inherited from transpiler)
- [x] Lower `match` expressions in the MIR pass. (Verified working via desugaring)
- [x] Support `VAL_STRING` in the runtime and codegen. (Concatenation implemented)

## Milestone 5: Advanced Features
**Goal:** Support collections, closures, and FFI.
- [x] Implement `VAL_LIST` in the runtime with heap allocation.
- [ ] Implement `VAL_RECORD` in the runtime with heap allocation.
- [ ] Implement closure lowering (lambda lifting or environment structures).
- [ ] Implement `extern fn` linkage for FFI.
- [ ] Add optimization flags (`-O2`, `-O3`) to the build harness.
