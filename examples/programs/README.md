# Example Programs

These programs demonstrate Aster features in progressively more complex code.

Run any program:

```bash
uv run aster run examples/programs/<program>/main.aster
```

Type-check (semantic analysis):

```bash
uv run aster check examples/programs/<program>/main.aster
```

Ownership-surface modes (optional):

```bash
uv run aster check examples/programs/<program>/main.aster --ownership warn
uv run aster check examples/programs/<program>/main.aster --ownership deny
```

## Programs

1. `01-hello`
2. `02-sum-to`
3. `03-fizzbuzz`
4. `04-match-basics`
5. `05-destructuring`
6. `06-modules-math`
7. `07-closures`
8. `08-primes-sieve`
9. `09-bitwise-checksum`
10. `10-byte-pack`
11. `11-ownership-modes`
12. `12-raw-pointer-surface`

