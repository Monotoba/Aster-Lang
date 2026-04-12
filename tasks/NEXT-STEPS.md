# NEXT STEPS

1. Decide on a CST/trivia strategy for the comment-preserving formatter (attachment model vs. separate trivia stream).
2. Decide how far the ownership/borrow checking prototype should go beyond the current non-enforcing warnings (move semantics, aliasing rules, lifetimes).
3. Decide whether trait resolution or effect tracking prototype should come next in Phase 3.
4. Decide whether nested/mixed structural or-patterns inside tuple or list elements need compiler test coverage.
5. Decide whether non-trailing or multiple rest patterns belong in the language.
6. Start comment-preserving formatter work once the AST/CST strategy is chosen.
7. Docs cleanup: clarify that bindings are `:=`/`mut` (no `let` keyword), even though AST nodes are named `LetDecl`/`LetStmt`.
8. Backend: expand VM coverage toward interpreter parity (mutability enforcement, destructuring bindings, more runtime parity).
9. Backend: keep JSON VM artifacts for now; revisit compression/binary encoding later (check back with the user before changing formats).
