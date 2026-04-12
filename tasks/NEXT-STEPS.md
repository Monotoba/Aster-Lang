# NEXT STEPS

Phase 3 is complete. Phase 4 (interpreter) is complete. Phase 5 (formatter) is complete.
Phase 6 (compiler) is in progress.

Near-term focus:
- Keep JSON VM artifacts for now; revisit compression/binary encoding later (check back before changing formats).

Open questions / deferred decisions:
1. Decide whether nested/mixed structural or-patterns inside tuple or list elements need compiler test coverage.
2. Decide whether non-trailing or multiple rest patterns belong in the language.
3. Effect tracking design extension: currently a prototype (named effects declared with `effect`, propagated via `!name` annotations). Possible next steps: handler syntax, algebraic continuations, or async effects.
4. Backend: keep JSON VM artifacts for now; revisit compression/binary encoding later (check back with the user before changing formats).

Phase 6 remaining:
- define HIR
- define MIR / typed IR
- native backend feasibility study
- caching and incremental compilation

Caching/incremental notes:
- Define cache location and invalidation strategy
- Decide whether to reuse VM artifacts or introduce a dedicated cache format

Native backend feasibility (near-term checklist):
- Decide on single TU vs per-module C emission
- Define minimal `AsterValue` tag set for the spike
- Prototype a `cc` build/run harness once IR emission exists
- Decide whether to emit debug-friendly C with source mapping comments
