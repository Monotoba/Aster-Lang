# Caching & Incremental Compilation Notes

Goal: speed up repeated builds by reusing prior compilation artifacts.

## Proposed layers

- Source hash cache: skip parse/semantic when inputs and config are identical.
- Module cache: store compiled artifacts per module and reuse when unchanged.
- Dependency graph: track transitive imports to invalidate on upstream changes.

## Inputs to hash

- Source text
- Relevant compiler flags (`--backend`, `--ownership`, `--types`, artifact format)
- Module resolver config (manifest, lockfile, search roots)

## Open questions

- Cache location: `.aster_cache/` in project root vs global cache.
- Artifact format: reuse JSON/binary VM artifacts or add a separate internal cache format.
- Cache eviction strategy and size limits.

## Next actions

- Pick cache directory and document it in user/developer docs.
- Define a cache key schema (hash inputs + toolchain version).
- Add a minimal `--cache` flag to `aster build` (off by default).
- Decide whether cache entries should embed backend adapter version identifiers.
