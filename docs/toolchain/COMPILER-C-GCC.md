# Design: Aster to C Compiler (GCC Backend)

This document specifies the design for the primary native Aster compiler, which targets C and uses GCC for machine code generation.

## 1. Objectives
- **Performance:** Reach native execution speeds far exceeding the Python interpreter.
- **Portability:** Use standard C99/C11 to ensure Aster can run anywhere GCC is available.
- **Debuggability:** Generate human-readable C code with line mapping for easier troubleshooting.
- **Interoperability:** Provide a clear ABI for future C/FFI integration.

## 2. Compiler Pipeline
The compiler follows the standard Aster pipeline but branches at the MIR level:
1.  **Frontend:** Lexer → Parser → Semantic Analyzer → Typed HIR.
2.  **Middle-end:** HIR → MIR (Middle Intermediate Representation).
    - MIR performs ownership lowering (moves, borrows, drops).
    - MIR flattens complex expressions into a series of assignments to temporary variables.
3.  **Backend (C Codegen):** MIR → C Source Code.
    - Translates MIR instructions to C statements.
    - Maps Aster types to the `AsterValue` runtime system.
4.  **Host Compilation:** C Source → GCC → Native Executable.

## 3. Runtime System (`aster_runtime.h` / `aster_runtime.c`)

### 3.1 `AsterValue` Model
To support Aster's dynamic features and standard types, we use a tagged union for the primary value type.

```c
typedef enum {
    VAL_NIL,
    VAL_BOOL,
    VAL_INT,
    VAL_FLOAT,
    VAL_STRING,
    VAL_LIST,
    VAL_RECORD,
    VAL_FN,
    VAL_ERROR
} AsterValueKind;

typedef struct {
    AsterValueKind kind;
    union {
        bool boolean;
        int64_t integer;
        double floating;
        struct AsterString* string;
        struct AsterList* list;
        struct AsterRecord* record;
        struct AsterFunction* fn;
    } as;
} AsterValue;
```

### 3.2 Memory Management
- **Initial Phase:** Manual allocation (`malloc`/`free`) guided by MIR `MDrop` and `MMove` instructions.
- **Strings/Lists:** Heap-allocated with a simple header.
- **Future:** Reference counting or a lightweight GC for `*shared` values.

## 4. Codegen Strategy

### 4.1 Function Mapping
Aster functions are mapped to C functions with a standard signature:
```c
AsterValue aster_fn_name(AsterValue arg1, AsterValue arg2);
```

### 4.2 Control Flow
- `if/else` → `if/else` in C.
- `while` → `while` in C.
- `match` → Lowered to nested `if/else` or `switch` on the `kind` tag in C.

### 4.3 Variables and Temporaries
MIR locals are declared at the top of the C function to follow C89/C99 style and ensure clean scope management.

```c
AsterValue aster_my_function(AsterValue a) {
    AsterValue _tmp1;
    AsterValue _tmp2;
    // ... code ...
}
```

## 5. GCC Build Harness
The `CBackendAdapter` will manage the host compiler:
1.  Emit `main.c` and a `.c` file for each module.
2.  Include `aster_runtime.h`.
3.  Invoke GCC: `gcc -O2 -I./runtime main.c module1.c runtime.c -o my_program`.
4.  Handle architecture-specific flags (e.g., `-m64`).

## 6. ABI and Interop
- **Calling Convention:** Standard C calling convention.
- **FFI:** `extern fn` in Aster will map directly to C function declarations that the user must provide or link against.

## 7. Error Handling
- **Runtime Errors:** Panics (e.g., division by zero, nil dereference) will call an `aster_panic` function that prints a stack trace and exits.
- **Compile-time Errors:** Caught by the Aster frontend before codegen begins.
