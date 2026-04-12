# 15. Higher-Order Functions and `Fn(...) -> ...` Types

Goal: pass functions around and type them when helpful.

## Function types

Use `Fn(T1, T2) -> R` in type annotations:

```aster
fn apply_twice(x: Int, f: Fn(Int) -> Int) -> Int:
    return f(f(x))

fn main():
    inc := (n: Int) -> n + 1
    print(apply_twice(10, inc))
```

## Typed closures

```aster
fn make_counter(start: Int) -> Fn() -> Int:
    mut n := start
    return () -> :
        n <- n + 1
        return n
```

## Exercises

1. Write `map_int(xs: List[Int], f: Fn(Int) -> Int) -> List[Int]` using a loop and a new list.
2. Write `filter_gt(xs: List[Int], n: Int) -> List[Int]`.

