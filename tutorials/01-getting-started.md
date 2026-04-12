# 01. Getting Started

Goal: run and format your first Aster program.

## Hello world

Create `hello.aster`:

```aster
fn main():
    print("hello, world")
```

Run it:

```bash
uv run aster run hello.aster
```

Type-check it (semantic analysis only):

```bash
uv run aster check hello.aster
```

Format it:

```bash
uv run aster fmt hello.aster
```

## How `main()` works

If a zero-argument function named `main` exists, `aster run` automatically calls it.

## Exercises

1. Change the string and re-run.
2. Add a second `print(...)`.

