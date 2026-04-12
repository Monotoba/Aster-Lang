# 11. Type Aliases and Generics (Prototype)

Goal: get comfortable with `typealias` and the current generics prototype.

## Type aliases

```aster
typealias UserId = Int

fn main():
    id: UserId := 123
    print(id)
```

## Generic type aliases

```aster
typealias Box[T] = T

fn main():
    x: Box[Int] := 5
    print(x)
```

## Generic functions

```aster
fn id[T](x: T) -> T:
    return x

fn main():
    print(id(123))
    print(id("hi"))
```

## Bounds (traits)

You can write bounds like `T: Show + Hash`. Today this is mainly used for semantic prototype checks;
it does not enable runtime dispatch.

```aster
fn debug_print[T: Show](x: T):
    print(str(x))
```

## Current limitations (important)

- Generics are intentionally incomplete; they exist so you can prototype APIs without blocking on a full type system.
- There is no monomorphization story yet, and no runtime trait dispatch.

