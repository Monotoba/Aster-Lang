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

## Implementation

- **Cache directory**: `.aster_cache/v1/` inside the project root. Falls back to
  `~/.cache/aster-lang/v1/` when no project root is found.
- **Cache key**: `SHA256(source_content) + SHA256(backend + artifact_format + ownership +
  types + toolchain_version)`. The toolchain version is derived from a hash of
  `aster_lang/__init__.py`; a release build would use the package version string.
- **Artifact storage**: the compiled output file (`.py`, `.asterbc.json`, `.asterbc`, or `.c`) is
  copied verbatim into the cache entry directory alongside `metadata.json`.
- **Invalidation**: `get()` checks mtime, size, and full content hash before accepting a hit.
- **CLI flag**: `aster build --cache` enables caching (off by default). Reports "Cached …" on a hit.

## Open questions (deferred)

- Cache eviction strategy and size limits (manual-clear only for now).
- Backend adapter version identifier in key (toolchain version used as proxy today).
- Dependency-level invalidation for multi-module builds (entry file only today).
