# NEXT STEPS

Phases 2–6 are complete. Phase 7 (tooling) is next.

## Phase 6 complete

Caching and incremental compilation is done:
- `CacheManager` in `src/aster_lang/cache.py` — key computation, put/get/invalidate/clear/stats
- Cache directory: `.aster_cache/v1/` in project root (falls back to global `~/.cache/aster-lang/`)
- Cache key: SHA256(source content) + SHA256(backend + flags + toolchain version)
- `--cache` flag on `aster build` (off by default); prints "Cached …" on hit
- Python and VM adapters wired; C adapter left for when C backend matures

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
