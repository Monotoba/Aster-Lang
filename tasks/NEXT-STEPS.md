# NEXT STEPS

Phases 2–6 are complete. Phase 7 (tooling) is next.

## Phase 6 complete

Caching and incremental compilation is done:
- `CacheManager` in `src/aster_lang/cache.py` — key computation, put/get/invalidate/clear/stats
- Cache directory: `.aster_cache/v1/` in project root (falls back to global `~/.cache/aster-lang/`)
- Cache key: SHA256(source content) + SHA256(backend + flags + toolchain version)
- `--cache` flag on `aster build` (off by default); prints "Cached …" on hit
- Python and VM adapters wired; C adapter left for when C backend matures

## Phase 7 (tooling) — in progress

**Done:**
- `aster test` — test runner with `test_*.aster` discovery, `fn test_*()` execution, `assert()` built-in
- `aster doc` — doc generator reading `##` comments from `pub` declarations, emitting Markdown
- Error index (`docs/ERROR-INDEX.md`) — 55 error IDs with causes, examples, and fixes
- `aster bench` — benchmark harness with `bench_*.aster` discovery, `fn bench_*()` timing, `--iters N` flag, timing stats (mean/min/max per function)

**Remaining:**
- language server Phase 1 implementation (diagnostics via `pygls`) — design complete in `docs/toolchain/LANGUAGE-SERVER.md`
- package manager plan

## Phase 8 (standard library) — complete

**Done:**
- `math` — full coverage: trig (sin/cos/tan/asin/acos/atan/atan2), hyperbolic, exp/log/log2/log10, gcd/lcm, sign, clamp, is_nan/is_inf/is_finite, constants pi/e/tau/inf/nan
- `str` — full coverage: inspection (len/is_empty/is_digit/is_alpha/is_alnum/is_space), transformation (upper/lower/title/strip/reverse/repeat/replace/pad), split/join/chars, search, to_int/to_float, format
- `std` — type_of, panic, todo, input, exit, env, env_or, args, assert
- `list` — higher-order: map/filter/reduce/any/all/count/sort/sort_by; aggregate: sum/product; construction: range/repeat/append/prepend/concat; access: head/tail/last/take/drop/len; transforms: reverse/flatten/zip/enumerate/unique/contains
- `io` — read_file/write_file/append_file/read_lines/write_lines, file_exists/is_file/is_dir, delete_file/list_dir/mkdir, print_err
- `random` — random/rand_int/rand_float/choice/shuffle/sample/seed
- `time` — now/now_ms/monotonic/sleep/strftime/clock
- `linalg` — vectors and matrices (unchanged)
- All modules have semantic symbols registered for static analysis
- Documentation: `docs/language/standard-library/` (README + one page per module)
- 908 tests passing

**Remaining:**
- `Float` literals in the parser and lexer (currently only reachable via native module return values)
- Float arithmetic operators in interpreter and semantic analyzer
- Expose `Float` type in the language grammar

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
