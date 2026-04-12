# NEXT STEPS

Near-term focus:
- Continue VM parity work (mutability enforcement, destructuring bindings, remaining runtime gaps).
- Keep JSON VM artifacts for now; revisit compression/binary encoding later (check back before changing formats).

1. Decide how far the ownership/borrow checking prototype should go beyond the current non-enforcing warnings (move semantics, aliasing rules, lifetimes).
2. Decide whether trait resolution or effect tracking prototype should come next in Phase 3.
3. Decide whether nested/mixed structural or-patterns inside tuple or list elements need compiler test coverage.
4. Decide whether non-trailing or multiple rest patterns belong in the language.
5. Docs cleanup: clarify that bindings are `:=`/`mut` (no `let` keyword), even though AST nodes are named `LetDecl`/`LetStmt`.
6. Backend: expand VM coverage toward interpreter parity (mutability enforcement, destructuring bindings, more runtime parity).
7. Backend: keep JSON VM artifacts for now; revisit compression/binary encoding later (check back with the user before changing formats).
