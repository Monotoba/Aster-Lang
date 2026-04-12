# 20. Unsafe Surfaces and Raw Pointers

Goal: understand why `*raw` exists and how Aster keeps “unsafe” explicit.

## Pointer syntax (surface)

- `*own T`, `*shared T`, `*weak T`, `*raw T`

The most important one for philosophy is `*raw T`:

- it is explicit
- it signals “this boundary is unsafe”
- it will be the home for FFI-like APIs

Example signature:

```aster
fn read_byte(ptr: *raw Byte) -> Byte:
    return byte(0)
```

Today there is no pointer value model at runtime. This is a design surface so we can evolve the backend
without changing user code later.

## Exercise

1. Try `aster check --ownership warn` on a file that contains `*raw` and observe the warning.
2. Switch to `--ownership deny` and confirm the syntax is still allowed, but violations (once implemented) will be treated as errors.
