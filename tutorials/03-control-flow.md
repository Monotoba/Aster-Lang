# 03. Control Flow

Goal: use `if`, `while`, and `for`.

## If / else

```aster
fn main():
    n := 7
    if n % 2 == 0:
        print("even")
    else:
        print("odd")
```

## While loops

```aster
fn main():
    mut i := 0
    while i < 5:
        print(i)
        i <- i + 1
```

## For loops

`for` iterates over a list. `range(...)` is the easiest way to get one.

```aster
fn main():
    for i in range(5):
        print(i)
```

## Exercises

1. Print the sum of `1..10` using a `while`.
2. Print the sum of `1..10` using a `for` over `range(1, 11)`.

