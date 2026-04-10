from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class CompilationArtifact:
    stage: str = "scaffold"

    def summary(self) -> str:
        return f"Aster compilation artifact ({self.stage})"


def compile_source(source: str) -> CompilationArtifact:
    _ = source
    return CompilationArtifact()
