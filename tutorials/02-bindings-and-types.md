# 02. Bindings and Types

Goal: learn how to create variables, mutate them, and use basic types.

## Bindings (no `let`)

```aster
fn main():
    x := 10
    print(x)
```

`:=` creates a new binding. Aster does not use `let`.

## Mutable bindings

To update a variable, declare it `mut` and assign with `<-`:

```aster
fn main():
    mut total := 0
    total <- total + 1
    print(total)
```

## Basic types you will use a lot

- `Int` (integers)
- `String` (double-quoted)
- `Bool` (`true` / `false`)
- `nil`

## Builtins available in the interpreter/VM

- `print(x)`
- `str(x)`
- `int(x)`
- `len(x)`
- `abs(x)`
- `max(a, b)`
- `min(a, b)`
- `range(n)` or `range(start, stop)` (produces a list of ints)
- fixed-width casts (wrap by masking): `nibble(x)`, `byte(x)`, `word(x)`, `dword(x)`, `qword(x)`

## Exercises

1. Write a program that prints `abs(-10)`.
2. Use `range(5)` and print `len(range(5))`.
