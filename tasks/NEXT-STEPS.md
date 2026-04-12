# NEXT STEPS

Near-term focus:
- Keep JSON VM artifacts for now; revisit compression/binary encoding later (check back before changing formats).

Phase 3 remaining:
1. Effect tracking prototype — no infrastructure yet; needs language design decision (pure/IO/async effects? algebraic effects?).

Open questions:
2. Decide whether nested/mixed structural or-patterns inside tuple or list elements need compiler test coverage.
3. Decide whether non-trailing or multiple rest patterns belong in the language.
4. Docs cleanup: clarify that bindings are `:=`/`mut` (no `let` keyword), even though AST nodes are named `LetDecl`/`LetStmt`.
5. Backend: keep JSON VM artifacts for now; revisit compression/binary encoding later (check back with the user before changing formats).
