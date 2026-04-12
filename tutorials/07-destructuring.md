# 07. Destructuring Bindings

Goal: pull pieces out of a value when you bind it.

## Tuple destructuring

```aster
fn main():
    pair := (10, 20)
    (x, y) := pair
    print(x + y)
```

## List destructuring with a rest tail

```aster
fn main():
    [head, *tail] := [1, 2, 3, 4]
    print(head)
    print(len(tail))
```

## Record destructuring

```aster
fn main():
    p := {x: 10, y: 20}
    {x, y} := p
    print(x * y)
```

## Exercise

1. Use destructuring to swap `(a, b)` into `(b, a)` and print both.

