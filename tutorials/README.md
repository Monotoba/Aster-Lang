# Aster Tutorials

This folder contains 20 tutorials that teach Aster from “Python-feeling basics” through more advanced
features. Ownership/borrowing is introduced as an **opt-in** diagnostic surface (`--ownership off|warn|deny`)
so you can learn it gradually.

## Lessons

1. [01-getting-started.md](01-getting-started.md)
2. [02-bindings-and-types.md](02-bindings-and-types.md)
3. [03-control-flow.md](03-control-flow.md)
4. [04-functions.md](04-functions.md)
5. [05-collections-and-records.md](05-collections-and-records.md)
6. [06-match-basics.md](06-match-basics.md)
7. [07-destructuring.md](07-destructuring.md)
8. [08-modules-and-imports.md](08-modules-and-imports.md)
9. [09-lambdas-and-closures.md](09-lambdas-and-closures.md)
10. [10-tooling-and-debugging.md](10-tooling-and-debugging.md)
11. [11-typealiases-and-generics.md](11-typealiases-and-generics.md)
12. [12-traits-and-vm.md](12-traits-and-vm.md)
13. [13-bitwise-and-fixed-width.md](13-bitwise-and-fixed-width.md)
14. [14-operator-precedence.md](14-operator-precedence.md)
15. [15-higher-order-and-fn-types.md](15-higher-order-and-fn-types.md)
16. [16-project-layout-and-aster-toml.md](16-project-layout-and-aster-toml.md)
17. [17-debugging-type-errors.md](17-debugging-type-errors.md)
18. [18-ownership-philosophy.md](18-ownership-philosophy.md)
19. [19-borrows-and-signatures.md](19-borrows-and-signatures.md)
20. [20-unsafe-and-raw-pointers.md](20-unsafe-and-raw-pointers.md)

## Tutorial Programs

Runnable programs live under [programs](programs).

Example:

```bash
uv run aster run tutorials/programs/01-fizzbuzz/main.aster
```

