# Tutorial program: FFI math

Demonstrates binding `libm` functions via `extern` and calling them from Aster.

```bash
uv run aster run tutorials/programs/07-ffi-math/main.aster
```

Expected output:
```
cos(0)  = 1.0
sin(0)  = 0.0
sqrt(9) = 3.0
floor(2) = 2.0
ceil(2)  = 2.0
```
