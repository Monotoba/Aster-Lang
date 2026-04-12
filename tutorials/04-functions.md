# 04. Functions

Goal: define and call functions, including recursion.

## Defining functions

```aster
fn add(a: Int, b: Int) -> Int:
    return a + b

fn main():
    print(add(2, 3))
```

## Early returns

```aster
fn sign(n: Int) -> Int:
    if n < 0:
        return -1
    if n == 0:
        return 0
    return 1
```

## Recursion

```aster
fn fact(n: Int) -> Int:
    if n <= 1:
        return 1
    return n * fact(n - 1)

fn main():
    print(fact(5))
```

## Exercises

1. Write `fib(n: Int) -> Int` recursively.
2. Write `clamp(x: Int, lo: Int, hi: Int) -> Int` using `min`/`max`.

