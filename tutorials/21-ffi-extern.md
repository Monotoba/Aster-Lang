# 21. Foreign Function Interface (FFI)

Goal: call functions from shared C libraries directly from Aster code using `extern` blocks.

## What FFI lets you do

Aster's `extern` declaration binds named C functions from any shared library on your system.
At runtime the interpreter resolves the library, configures ctypes types, and wraps the C
function so it behaves like any other Aster callable.

## Basic syntax

```aster
extern "libm":
    fn cos(x: Float) -> Float
    fn sin(x: Float) -> Float

fn main():
    print(cos(0))   # 1.0
    print(sin(0))   # 0.0
```

The string after `extern` is the library name. Aster tries:
1. Treating it as a file path if it starts with `/` or `./`
2. Asking the system to locate it (`libm` → `libm.so.6` on Linux)
3. Passing the name directly to the dynamic loader as a fallback

## Running the example

```bash
uv run aster run tutorials/programs/07-ffi-math/main.aster
```

## Types

Only scalar types cross the boundary today:

| Aster   | C              |
|---------|----------------|
| `Int`   | `int64_t`      |
| `Float` | `double`       |
| `String`| `char *`       |
| `Bool`  | `int`          |
| `Byte`  | `uint8_t`      |
| `Word`  | `uint16_t`     |
| `DWord` | `uint32_t`     |
| `QWord` | `uint64_t`     |
| (none)  | void (no return)|

Integers and floats are passed through automatically. Aster `Int` literal `0` becomes
`c_int64(0)` at the call boundary — no cast needed in your source.

## Multiple function signatures in one block

Group related functions under a single `extern` block:

```aster
extern "libm":
    fn floor(x: Float) -> Float
    fn ceil(x: Float) -> Float
    fn fabs(x: Float) -> Float

fn main():
    print(floor(2))    # 2.0
    print(ceil(2))     # 2.0
    print(fabs(-7))    # 7.0
```

## Exporting extern functions from a module

Mark the block `pub` to let other modules import the bound names:

```aster
# cmath.aster
pub extern "libm":
    fn sqrt(x: Float) -> Float
    fn pow(base: Float, exp: Float) -> Float
```

```aster
# main.aster
use cmath: sqrt, pow

fn main():
    print(sqrt(9))      # 3.0
    print(pow(2, 8))    # 256.0
```

Or import the module as a namespace:

```aster
use cmath

fn main():
    print(cmath.sqrt(16))  # 4.0
```

## Absolute paths (for local shared libraries)

```aster
extern "/usr/local/lib/libmyalgo.so":
    fn process(n: Int) -> Int

fn main():
    print(process(42))
```

## What happens when a library is not found

The error is raised at the point the `extern` declaration is executed, not at the call site:

```
FFI: cannot load library 'libnosuchlib': ...
```

The message always starts with `FFI:` so it is easy to grep for.

## Limitations (current)

- **Scalars only** — pointer and struct arguments are not yet supported.
- **No variadic C functions** — `printf` cannot be bound; use Aster's `print` instead.
- **C backend** — the C transpiler backend does not yet consume `extern` declarations.
  FFI works only in `aster run` (interpreter) today.

## Exercise

1. Bind `libm`'s `atan2` (two `Float` arguments, returns `Float`) and compute `atan2(1, 1)`.
   The result should be approximately `0.7853981633974483` (π/4).

2. Create a `cmath.aster` module that exports `sqrt`, `pow`, and `log` as `pub extern`.
   Import all three in `main.aster` and print `log(pow(2, 10))` (should be about `6.93`).
