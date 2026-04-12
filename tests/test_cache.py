"""Tests for the caching system."""

from __future__ import annotations

from pathlib import Path

from aster_lang.cache import CacheKey, CacheManager


class TestCacheKey:
    def test_full_hash_combines_source_and_config(self) -> None:
        key = CacheKey(source_hash="abc123", config_hash="def456")
        full = key.full_hash()
        assert len(full) == 32
        assert full != "abc123"
        assert full != "def456"

    def test_same_inputs_produce_same_hash(self) -> None:
        key1 = CacheKey(source_hash="abc", config_hash="def")
        key2 = CacheKey(source_hash="abc", config_hash="def")
        assert key1.full_hash() == key2.full_hash()

    def test_different_inputs_produce_different_hash(self) -> None:
        key1 = CacheKey(source_hash="abc", config_hash="def")
        key2 = CacheKey(source_hash="xyz", config_hash="def")
        assert key1.full_hash() != key2.full_hash()


class TestCacheManager:
    def test_disabled_cache_does_not_create_dirs(self, tmp_path: Path) -> None:
        cache = CacheManager(project_root=tmp_path, enabled=False)
        assert not cache.cache_root.exists()

    def test_enabled_cache_creates_dirs(self, tmp_path: Path) -> None:
        cache = CacheManager(project_root=tmp_path, enabled=True)
        assert cache.modules_dir.exists()
        assert cache.deps_dir.exists()

    def test_compute_key_consistent(self, tmp_path: Path) -> None:
        source_file = tmp_path / "test.aster"
        source_file.write_text("fn main(): pass")
        cache = CacheManager(project_root=tmp_path, enabled=True)

        key1 = cache.compute_key(
            source_file,
            backend="python",
            ownership_mode="standard",
            types_mode="standard",
        )
        key2 = cache.compute_key(
            source_file,
            backend="python",
            ownership_mode="standard",
            types_mode="standard",
        )
        assert key1.full_hash() == key2.full_hash()

    def test_put_and_get_round_trip(self, tmp_path: Path) -> None:
        source_file = tmp_path / "test.aster"
        source_file.write_text("fn main(): pass")
        cache = CacheManager(project_root=tmp_path, enabled=True)

        key = cache.compute_key(source_file, backend="python")
        artifact = tmp_path / "artifact.py"
        artifact.write_text("# generated")

        cache.put(
            source_file,
            key,
            backend="python",
            artifact_format=None,
            ownership_mode="standard",
            types_mode="standard",
            artifact_path=artifact,
        )

        cached = cache.get(source_file, key, "python", None)
        assert cached is not None
        metadata, path = cached
        assert metadata.source_path == str(source_file)
        assert path.exists()
