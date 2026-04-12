# 14. Operator Precedence (Practical)

Goal: avoid surprises with `and`/`or`, comparisons, and bitwise operators.

## Mental model

- Postfix: calls `f(x)`, indexing `x[i]`, member access `x.y`
- Unary: `-x`, `not x`, `~x`
- `* / %`
- `+ -`
- `<< >>`
- comparisons: `< <= > >=`
- equality: `== !=`
- bitwise: `&` then `^` then `|`
- logical: `and` then `or`

When in doubt: add parentheses. `aster fmt` will keep your intent readable.

## Examples

```aster
fn main():
    x := 1 | 2 & 3     # parsed as: 1 | (2 & 3)
    y := (1 | 2) & 3   # forced grouping
    print(x)
    print(y)
```

## Exercise

1. Predict and then run: `print(1 + 2 << 3)`.

