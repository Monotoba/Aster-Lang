"""Tests for the Aster package manager semver module."""

from __future__ import annotations

import pytest

from aster_lang.pkg.semver import (
    Constraint,
    SemVerError,
    Version,
    best_match,
    parse_constraint,
    parse_version,
)

# ---------------------------------------------------------------------------
# Version parsing
# ---------------------------------------------------------------------------


class TestVersionParsing:
    def test_basic(self) -> None:
        v = Version.parse("1.2.3")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.pre == ""
        assert v.build == ""

    def test_prerelease(self) -> None:
        v = Version.parse("1.2.3-alpha.1")
        assert v.pre == "alpha.1"

    def test_build_metadata(self) -> None:
        v = Version.parse("1.2.3+build.5")
        assert v.build == "build.5"

    def test_pre_and_build(self) -> None:
        v = Version.parse("1.0.0-rc.2+build.5")
        assert v.pre == "rc.2"
        assert v.build == "build.5"

    def test_zero_version(self) -> None:
        v = Version.parse("0.0.0")
        assert v.major == 0

    def test_invalid_missing_patch(self) -> None:
        with pytest.raises(SemVerError):
            Version.parse("1.2")

    def test_invalid_text(self) -> None:
        with pytest.raises(SemVerError):
            Version.parse("not-a-version")

    def test_invalid_leading_zeros(self) -> None:
        with pytest.raises(SemVerError):
            Version.parse("01.2.3")

    def test_str_roundtrip(self) -> None:
        assert str(Version.parse("1.2.3-alpha.1+build")) == "1.2.3-alpha.1+build"

    def test_parse_version_helper(self) -> None:
        assert parse_version("2.0.0") == Version(2, 0, 0)


# ---------------------------------------------------------------------------
# Version ordering
# ---------------------------------------------------------------------------


class TestVersionOrdering:
    def test_major(self) -> None:
        assert Version.parse("2.0.0") > Version.parse("1.9.9")

    def test_minor(self) -> None:
        assert Version.parse("1.2.0") > Version.parse("1.1.9")

    def test_patch(self) -> None:
        assert Version.parse("1.0.1") > Version.parse("1.0.0")

    def test_pre_sorts_lower(self) -> None:
        assert Version.parse("1.0.0-alpha") < Version.parse("1.0.0")

    def test_pre_alpha_lt_beta(self) -> None:
        assert Version.parse("1.0.0-alpha") < Version.parse("1.0.0-beta")

    def test_pre_numeric(self) -> None:
        assert Version.parse("1.0.0-rc.1") < Version.parse("1.0.0-rc.2")

    def test_build_ignored_for_ordering(self) -> None:
        assert Version.parse("1.0.0+a") == Version.parse("1.0.0+b")

    def test_equality(self) -> None:
        assert Version.parse("1.2.3") == Version.parse("1.2.3")

    def test_sorted(self) -> None:
        versions = [Version.parse(v) for v in ["1.0.0", "2.0.0", "1.0.0-alpha", "1.0.1"]]
        assert sorted(versions) == [
            Version.parse("1.0.0-alpha"),
            Version.parse("1.0.0"),
            Version.parse("1.0.1"),
            Version.parse("2.0.0"),
        ]


# ---------------------------------------------------------------------------
# Constraint parsing
# ---------------------------------------------------------------------------


class TestConstraintParsing:
    def test_exact(self) -> None:
        c = Constraint.parse("1.2.3")
        assert c.matches(Version.parse("1.2.3"))
        assert not c.matches(Version.parse("1.2.4"))

    def test_exact_with_eq(self) -> None:
        c = Constraint.parse("=1.2.3")
        assert c.matches(Version.parse("1.2.3"))

    def test_caret_stable(self) -> None:
        c = Constraint.parse("^1.2.3")
        assert c.matches(Version.parse("1.2.3"))
        assert c.matches(Version.parse("1.9.9"))
        assert not c.matches(Version.parse("2.0.0"))
        assert not c.matches(Version.parse("1.2.2"))

    def test_caret_zero_minor(self) -> None:
        c = Constraint.parse("^0.2.3")
        assert c.matches(Version.parse("0.2.3"))
        assert c.matches(Version.parse("0.2.9"))
        assert not c.matches(Version.parse("0.3.0"))

    def test_caret_zero_patch(self) -> None:
        c = Constraint.parse("^0.0.3")
        assert c.matches(Version.parse("0.0.3"))
        assert not c.matches(Version.parse("0.0.4"))

    def test_tilde(self) -> None:
        c = Constraint.parse("~1.2.3")
        assert c.matches(Version.parse("1.2.3"))
        assert c.matches(Version.parse("1.2.9"))
        assert not c.matches(Version.parse("1.3.0"))

    def test_gte(self) -> None:
        c = Constraint.parse(">=1.2.0")
        assert c.matches(Version.parse("1.2.0"))
        assert c.matches(Version.parse("9.9.9"))
        assert not c.matches(Version.parse("1.1.9"))

    def test_lt(self) -> None:
        c = Constraint.parse("<2.0.0")
        assert c.matches(Version.parse("1.9.9"))
        assert not c.matches(Version.parse("2.0.0"))

    def test_range(self) -> None:
        c = Constraint.parse(">=1.0.0,<2.0.0")
        assert c.matches(Version.parse("1.0.0"))
        assert c.matches(Version.parse("1.9.9"))
        assert not c.matches(Version.parse("2.0.0"))
        assert not c.matches(Version.parse("0.9.9"))

    def test_invalid_clause(self) -> None:
        with pytest.raises(SemVerError):
            Constraint.parse(">>1.0.0")

    def test_parse_constraint_helper(self) -> None:
        c = parse_constraint("^2.0.0")
        assert c.matches(Version.parse("2.1.0"))

    def test_str(self) -> None:
        assert str(Constraint.parse("^1.2.3")) == "^1.2.3"


# ---------------------------------------------------------------------------
# best_match
# ---------------------------------------------------------------------------


class TestBestMatch:
    def _vs(self, *texts: str) -> list[Version]:
        return [Version.parse(t) for t in texts]

    def test_picks_highest(self) -> None:
        vs = self._vs("1.0.0", "1.2.0", "1.1.0")
        c = parse_constraint("^1.0.0")
        assert best_match(vs, c) == Version.parse("1.2.0")

    def test_excludes_prerelease_by_default(self) -> None:
        vs = self._vs("1.0.0", "1.1.0-alpha")
        c = parse_constraint("^1.0.0")
        assert best_match(vs, c) == Version.parse("1.0.0")

    def test_allows_prerelease_when_flagged(self) -> None:
        vs = self._vs("1.0.0", "1.1.0-alpha")
        c = parse_constraint("^1.0.0")
        assert best_match(vs, c, allow_pre=True) == Version.parse("1.1.0-alpha")

    def test_returns_none_when_no_match(self) -> None:
        vs = self._vs("1.0.0", "1.1.0")
        c = parse_constraint("^2.0.0")
        assert best_match(vs, c) is None

    def test_empty_list(self) -> None:
        assert best_match([], parse_constraint("^1.0.0")) is None
