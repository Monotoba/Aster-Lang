# 13. FFI — calling libm from Aster

This program demonstrates Aster's Foreign Function Interface (FFI) feature.

`cmath.aster` declares a `pub extern "libm"` block that binds 15 functions from the
system math library. `main.aster` imports the module and exercises every bound function.

## Files

| File | Purpose |
|------|---------|
| `cmath.aster` | `pub extern "libm"` wrapper module — 15 bindings |
| `main.aster` | Exercises trig, roots, powers, logarithms, rounding |

## Run

```bash
uv run aster run examples/programs/13-ffi-libm/main.aster
```

## Type-check

```bash
uv run aster check examples/programs/13-ffi-libm/main.aster
```

## Expected output

```
--- Trigonometry ---
sin(0)       = 0.0
cos(0)       = 1.0
tan(0)       = 0.0
hypot(3, 4)  = 5.0

--- Roots and Powers ---
sqrt(2)      = 1.4142135623730951
cbrt(27)     = 3.0000000000000004
pow(2, 10)   = 1024.0

--- Logarithms ---
log(e)       = 1.0
log2(1024)   = 10.0
log10(1000)  = 3.0

--- Rounding ---
floor(2)     = 2.0
ceil(2)      = 2.0
fabs(-5)     = 5.0

--- atan2 ---
atan2(1, 1)  = 0.7853981633974483
```

## How it works

1. `pub extern "libm":` in `cmath.aster` tells the interpreter to load the system `libm`
   using ctypes and bind each listed function by name.
2. `use cmath` in `main.aster` loads the module; because the block is `pub`, all bound
   functions are exported.
3. At each call site, Aster coerces the arguments to the declared C types (`c_double` for
   `Float`), calls the C function, and wraps the result back into a `FloatValue`.

## Requirements

`libm` ships with every Linux and macOS system. On Windows it is part of `msvcrt`.
The ctypes loader will find it automatically via `ctypes.util.find_library("m")`.
