# 05. Collections and Records

Goal: use lists, tuples, and records; index and update them.

## Lists

```aster
fn main():
    nums := [10, 20, 30]
    print(nums[0])
    print(len(nums))
```

### Mutating a list element

Index assignment works when the base is an identifier:

```aster
fn main():
    mut nums := [10, 20, 30]
    nums[1] <- 999
    print(nums)
```

## Tuples

```aster
fn main():
    pair := (1, "one")
    print(pair[0])
    print(pair[1])
```

## Records

```aster
fn main():
    p := {x: 10, y: 20}
    print(p.x)
    print(p["y"])
```

### Mutating a record field

```aster
fn main():
    mut p := {x: 10, y: 20}
    p.x <- 99
    p["y"] <- 100
    print(p)
```

## Exercises

1. Create a record `{name: "Ada", age: 37}` and print both fields.
2. Create a list of 5 numbers using `range(5)` and overwrite index `2`.

