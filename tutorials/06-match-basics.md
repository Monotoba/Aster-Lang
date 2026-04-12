# 06. `match` Basics

Goal: branch on structure, not just booleans.

## Simple literal matches

```aster
fn classify(n: Int) -> String:
    match n:
        0:
            return "zero"
        1 | 2:
            return "small"
        _:
            return "other"
```

## Matching tuples, lists, and records

```aster
fn describe(v) -> String:
    match v:
        (0, y):
            return "x=0, y=" + str(y)
        [1, x]:
            return "list starts with 1, second=" + str(x)
        {kind: "point", x, y}:
            return "point(" + str(x) + "," + str(y) + ")"
        _:
            return "unknown"
```

## Exercises

1. Write a `match` that recognizes `[head, *tail]`.
2. Write a `match` that recognizes `{ok: true, value}` and `{ok: false, error}` records.

