# 19. Borrows in Function Signatures (Surface Only)

Goal: learn `&T` and `&mut T` as documentation and future-proofing.

## Borrow syntax

- shared: `&T`
- mutable: `&mut T`

Example:

```aster
fn head(xs: &List[Int]) -> Int:
    return xs[0]
```

Right now, borrows are:

- parsed and formatted
- accepted by the semantic analyzer (optionally warned/denied by `--ownership`)
- not enforced as a runtime rule (yet)

## Exercise

1. Run `aster check --ownership warn` on a file that uses `&mut` and observe the warnings.

