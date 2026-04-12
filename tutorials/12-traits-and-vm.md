# 12. Traits (Prototype) and the VM Backend

Goal: learn the current trait/impl surface area and how to run programs on the experimental VM.

## Traits and impls today

Traits and `impl` blocks are parsed and formatted, and semantic analysis performs a small prototype check
for `impl Trait for Type` blocks (required method presence and basic signature shape).

There is currently:
- no dynamic dispatch
- no method-call resolution (for example `x.show()` is not a thing yet)

## Example (compile-time only)

```aster
trait Show:
    fn show(self) -> String

impl Show for Int:
    fn show(self) -> String:
        return str(self)
```

## Running on the VM

The VM backend is experimental but usable for many programs:

```bash
uv run aster vm file.aster
```

If you hit a behavior mismatch between `run` (interpreter) and `vm`, treat it as a backend bug and reduce
to a small repro.

