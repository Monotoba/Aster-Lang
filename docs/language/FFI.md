# Foreign Function Interface (FFI)

Aster's FFI lets programs call functions from shared C libraries using `extern` blocks.
At runtime the interpreter uses Python's `ctypes` module to load the library and bind
each declared function.

---

## Declaration syntax

```
extern_decl ::= "pub"? "extern" STRING_LITERAL ":" NEWLINE INDENT fn_sig+ DEDENT
fn_sig      ::= "fn" IDENTIFIER "(" param_list? ")" ("->" type_expr)?
```

Example:

```aster
extern "libm":
    fn cos(x: Float) -> Float
    fn sin(x: Float) -> Float
    fn pow(base: Float, exp: Float) -> Float
```

- The string is the **library name** (see resolution rules below).
- Each `fn` line is a signature — no body.
- Omitting `-> Type` means the function returns nothing (void / `Nil`).

---

## Library name resolution

The name is resolved in this order:

1. **Absolute / relative path** — if the string starts with `/` or `./`, it is passed
   directly to `ctypes.CDLL`.
2. **System search** — `ctypes.util.find_library(stem)` where `stem` strips a leading
   `lib` prefix (so `"libm"` searches for `"m"`, which finds `libm.so.6` on Linux).
3. **Direct fallback** — `ctypes.CDLL(name)` is attempted last, handling bare names,
   platform extensions, and full filenames.

Any `OSError` from the loader produces a runtime error whose message starts with `FFI:`.

---

## Type mapping

| Aster type | C type      | ctypes        |
|------------|-------------|---------------|
| `Int`      | `int64_t`   | `c_int64`     |
| `Float`    | `double`    | `c_double`    |
| `String`   | `char *`    | `c_char_p`    |
| `Bool`     | `int`       | `c_int`       |
| `Byte`     | `uint8_t`   | `c_uint8`     |
| `Word`     | `uint16_t`  | `c_uint16`    |
| `DWord`    | `uint32_t`  | `c_uint32`    |
| `QWord`    | `uint64_t`  | `c_uint64`    |
| (absent)   | void        | `None`        |

Arguments are coerced at each call: `IntValue` / `BitsValue` → Python `int`,
`FloatValue` → Python `float`, `StringValue` → UTF-8 `bytes`.
Return values follow the same table in reverse.

---

## Exporting extern bindings

Use `pub extern` so other modules can import the bound functions:

```aster
# cmath.aster
pub extern "libm":
    fn sqrt(x: Float) -> Float
    fn log(x: Float) -> Float
```

```aster
# main.aster
use cmath: sqrt, log

fn main():
    print(sqrt(2))   # 1.4142...
    print(log(1))    # 0.0
```

Or import the whole module as a namespace:

```aster
use cmath

fn main():
    print(cmath.sqrt(4))  # 2.0
```

---

## Execution semantics

The `extern` block is executed when the declaration is reached (module load time), not
at call time. If the library cannot be found the error surfaces immediately, before any
functions are called. Individual function wrappers are created eagerly so symbol errors
also appear at load time.

---

## Semantic analysis

Each function in an `extern` block is registered in the symbol table as a
`SymbolKind.FUNCTION` with the declared parameter and return types. The type checker
uses these entries for call-site checking. `Float` is a valid type annotation and
resolves to `FloatType`.

`pub extern` functions are included in the module's export table, so
`use module: fname` and call-site checking work just like regular `pub fn` exports.

---

## Limitations

- **Scalars only** — pointer and struct arguments are not yet supported.
- **No variadic functions** — `printf`, `scanf`, etc. cannot be bound.
- **Interpreter only** — the C transpiler backend does not yet consume `extern`
  declarations. FFI works in `aster run` and the REPL; `aster build` does not emit
  C bindings.
- **No Windows DLL name disambiguation** — the name lookup relies on
  `ctypes.util.find_library` which behaves differently on Windows. Prefer absolute
  paths when targeting Windows.

---

## Quick reference

```aster
# Single function
extern "libm":
    fn sqrt(x: Float) -> Float

# Multiple functions
extern "libm":
    fn floor(x: Float) -> Float
    fn ceil(x: Float) -> Float
    fn fabs(x: Float) -> Float

# Absolute path
extern "/usr/local/lib/libmylib.so":
    fn process(n: Int) -> Int

# Void return
extern "libfoo":
    fn init()
    fn set_verbosity(level: Int)

# Pub — export to importing modules
pub extern "libm":
    fn pow(base: Float, exp: Float) -> Float
```

---

## See also

- Tutorial `21-ffi-extern.md` — step-by-step introduction
- Example program `examples/programs/13-ffi-libm/` — multi-function libm wrapper
- `LANGUAGE-REFERENCE.md` → "Extern (FFI) declaration" for the grammar entry
