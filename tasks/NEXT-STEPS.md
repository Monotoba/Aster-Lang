# NEXT STEPS

Phase 3 is complete. Phase 4 (interpreter) is complete. Phase 5 (formatter) is complete.
Phase 6 (compiler) is nearly complete — one item remains.

## Phase 6 remaining

- **caching and incremental compilation** — the only open Phase 6 BACKLOG item.

Caching/incremental notes (see also `docs/toolchain/CACHING.md`):
- Pick cache directory (`.aster_cache/` in project root vs global)
- Define a cache key schema (source hash + compiler flags + toolchain version)
- Add a minimal `--cache` flag to `aster build` (off by default)
- Decide whether cache entries embed backend adapter version identifiers
- Decide whether to reuse JSON/binary VM artifacts as the cached form or add a separate internal cache format

## Phase 7 (tooling) — next major phase

- language server plan
- package manager plan
- doc generator plan
- test runner plan
- benchmark harness

## Open questions / deferred decisions

1. Decide whether nested/mixed structural or-patterns inside tuple or list elements need compiler test coverage.
2. Decide whether non-trailing or multiple rest patterns belong in the language.
3. Effect tracking design extension: currently a prototype (`effect Name`, `!name` annotations). Possible next steps: handler syntax, algebraic continuations, or async effects.
4. Native backend C spike — feasibility scoped and documented; implementation (AsterValue runtime, codegen, `cc` harness) not yet started.

## Native backend C spike (deferred, post-caching)

Next steps when ready:
- Emit one C translation unit per module (decided: single TU for spike)
- Define minimal `AsterValue` tag set (Int/Bool/Nil/String)
- Prototype a `cc` build/run harness in the C adapter
- Decide whether to emit debug-friendly C with source mapping comments
