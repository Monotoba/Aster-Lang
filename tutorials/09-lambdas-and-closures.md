# 09. Lambdas and Closures

Goal: use lambdas, pass functions around, and capture variables.

## Single-expression lambdas

```aster
fn main():
    inc := x -> x + 1
    print(inc(41))
```

## Typed lambdas

```aster
fn main():
    add := (a: Int, b: Int) -> a + b
    print(add(2, 3))
```

## Block lambdas

```aster
fn main():
    twice := (x: Int) -> :
        return x + x
    print(twice(9))
```

## Capturing outer variables (closures)

Captures are by reference, so a captured `mut` binding can be updated:

```aster
fn make_counter(start: Int):
    mut n := start
    return () -> :
        n <- n + 1
        return n

fn main():
    c := make_counter(0)
    print(c())
    print(c())
```

## Exercises

1. Write `make_adder(n)` that returns a lambda `x -> x + n`.
2. Make two counters and confirm they are independent.

