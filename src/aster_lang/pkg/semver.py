"""Semantic versioning parser and constraint evaluator for the Aster package manager.

Implements the versioning model from PACKAGE-MANAGER-DESIGN.md section 9:
  - MAJOR.MINOR.PATCH with optional pre-release and build metadata
  - Constraint syntax: exact, ^, ~, >=, <=, >, <, and comma-joined conjunctions
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import total_ordering

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

_VERSION_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)"
    r"\.(?P<minor>0|[1-9]\d*)"
    r"\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<pre>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+(?P<build>[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


class SemVerError(ValueError):
    """Raised for malformed version strings or unsatisfiable constraints."""


@total_ordering
@dataclass(frozen=True)
class Version:
    """An immutable parsed semantic version."""

    major: int
    minor: int
    patch: int
    pre: str = ""  # pre-release identifier, e.g. "alpha.1"
    build: str = ""  # build metadata (ignored for precedence)

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def parse(cls, text: str) -> Version:
        """Parse a semantic version string.  Raises SemVerError on failure."""
        m = _VERSION_RE.match(text.strip())
        if not m:
            raise SemVerError(f"Invalid version: {text!r}")
        return cls(
            major=int(m.group("major")),
            minor=int(m.group("minor")),
            patch=int(m.group("patch")),
            pre=m.group("pre") or "",
            build=m.group("build") or "",
        )

    # ------------------------------------------------------------------
    # Comparison (build metadata ignored per SemVer spec)
    # ------------------------------------------------------------------

    def _pre_key(self) -> tuple[int, list[int | str]]:
        """Return a sort key for the pre-release field.

        Stable releases (no pre) sort HIGHER than any pre-release:
            1.0.0 > 1.0.0-rc.1 > 1.0.0-alpha.1
        """
        if not self.pre:
            return (1, [])
        parts: list[int | str] = []
        for part in self.pre.split("."):
            parts.append(int(part) if part.isdigit() else part)
        return (0, parts)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return (self.major, self.minor, self.patch, self.pre) == (
            other.major,
            other.minor,
            other.patch,
            other.pre,
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        s = (self.major, self.minor, self.patch, self._pre_key())
        o = (other.major, other.minor, other.patch, other._pre_key())
        return s < o

    def __hash__(self) -> int:
        return hash((self.major, self.minor, self.patch, self.pre))

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.pre:
            base += f"-{self.pre}"
        if self.build:
            base += f"+{self.build}"
        return base

    def __repr__(self) -> str:
        return f"Version({str(self)!r})"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def is_prerelease(self) -> bool:
        return bool(self.pre)

    def bump_major(self) -> Version:
        return Version(self.major + 1, 0, 0)

    def bump_minor(self) -> Version:
        return Version(self.major, self.minor + 1, 0)

    def bump_patch(self) -> Version:
        return Version(self.major, self.minor, self.patch + 1)


# ---------------------------------------------------------------------------
# Individual constraint clause
# ---------------------------------------------------------------------------

_CLAUSE_RE = re.compile(r"^(?P<op>\^|~|>=|<=|>|<|=|)" r"\s*" r"(?P<ver>\d[\d.\w-]*)$")


class _Clause:
    """A single operator+version constraint clause."""

    __slots__ = ("op", "ver")

    def __init__(self, op: str, ver: Version) -> None:
        self.op = op
        self.ver = ver

    def matches(self, v: Version) -> bool:
        op, base = self.op, self.ver
        if op in ("=", ""):
            return v == base
        if op == ">=":
            return v >= base
        if op == ">":
            return v > base
        if op == "<=":
            return v <= base
        if op == "<":
            return v < base
        if op == "~":
            # ~MAJOR.MINOR.PATCH → >= base and < MAJOR.(MINOR+1).0
            return v >= base and v < base.bump_minor()
        if op == "^":
            # ^MAJOR.MINOR.PATCH → >= base and < (MAJOR+1).0.0
            # Special case: ^0.MINOR.PATCH → >= base and < 0.(MINOR+1).0
            if base.major > 0:
                return v >= base and v < base.bump_major()
            if base.minor > 0:
                return v >= base and v < base.bump_minor()
            # ^0.0.PATCH → exact
            return v >= base and v < base.bump_patch()
        return False  # pragma: no cover

    def __repr__(self) -> str:
        return f"{self.op}{self.ver}"


# ---------------------------------------------------------------------------
# Constraint (comma-joined conjunction of clauses)
# ---------------------------------------------------------------------------


@dataclass
class Constraint:
    """A version constraint parsed from a requirement string."""

    clauses: list[_Clause] = field(default_factory=list)
    raw: str = ""

    @classmethod
    def parse(cls, text: str) -> Constraint:
        """Parse a constraint string like '^1.2.3' or '>=1.0.0,<2.0.0'."""
        raw = text.strip()
        clauses: list[_Clause] = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            m = _CLAUSE_RE.match(part)
            if not m:
                raise SemVerError(f"Invalid constraint clause: {part!r}")
            try:
                ver = Version.parse(m.group("ver"))
            except SemVerError:
                raise SemVerError(f"Invalid version in constraint: {part!r}") from None
            clauses.append(_Clause(m.group("op"), ver))
        if not clauses:
            raise SemVerError(f"Empty constraint: {text!r}")
        return cls(clauses=clauses, raw=raw)

    def matches(self, version: Version) -> bool:
        """Return True if *version* satisfies all clauses."""
        return all(c.matches(version) for c in self.clauses)

    def __str__(self) -> str:
        return self.raw

    def __repr__(self) -> str:
        return f"Constraint({self.raw!r})"


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def parse_version(text: str) -> Version:
    """Parse and return a Version; raises SemVerError on failure."""
    return Version.parse(text)


def parse_constraint(text: str) -> Constraint:
    """Parse and return a Constraint; raises SemVerError on failure."""
    return Constraint.parse(text)


def best_match(
    versions: list[Version], constraint: Constraint, *, allow_pre: bool = False
) -> Version | None:
    """Return the highest version satisfying *constraint*, or None.

    Pre-release versions are excluded unless *allow_pre* is True or the
    constraint explicitly pins a pre-release.
    """
    has_pre_clause = any(c.ver.is_prerelease for c in constraint.clauses)
    candidates = [
        v
        for v in versions
        if constraint.matches(v) and (not v.is_prerelease or allow_pre or has_pre_clause)
    ]
    return max(candidates) if candidates else None
