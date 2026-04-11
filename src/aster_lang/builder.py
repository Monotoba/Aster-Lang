"""Build orchestration for compiling Aster projects to Python.

The transpiler emits standard Python `import` statements. To make the output
runnable, the builder recursively compiles imported `.aster` modules into a
single output directory matching their qualified import names.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from aster_lang import ast
from aster_lang.compiler import Transpiler
from aster_lang.module_resolution import (
    ModuleResolutionError,
    ModuleSearchConfig,
    resolve_module_path,
)
from aster_lang.parser import parse_module


@dataclass(slots=True)
class BuildResult:
    out_dir: Path
    entry_py: Path
    errors: list[str] = field(default_factory=list)


def build_project(
    *,
    entry_path: Path,
    entry_module: ast.Module,
    dep_overrides: dict[str, Path] | None = None,
    extra_roots: tuple[Path, ...] = (),
    out_dir: Path | None = None,
    clean: bool = False,
    resolver_config: ModuleSearchConfig | None = None,
) -> BuildResult:
    """Recursively build an entry module and its imports into an output directory."""
    resolved_entry = entry_path.resolve()
    output_dir = (out_dir or resolved_entry.parent / "__aster_build__").resolve()
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    module_out_root = output_dir / "_aster"
    module_out_root.mkdir(parents=True, exist_ok=True)
    (module_out_root / "__init__.py").write_text("", encoding="utf-8")

    result = BuildResult(
        out_dir=output_dir,
        entry_py=output_dir / f"{resolved_entry.stem}.py",
        errors=[],
    )

    aster_module_labels: set[str] = set()
    built: set[tuple[str, ...]] = set()
    building: set[tuple[str, ...]] = set()

    def compile_named_module(
        module_parts: tuple[str, ...],
        *,
        base_dir: Path,
    ) -> None:
        if module_parts in built:
            return
        if module_parts in building:
            result.errors.append(f"Cyclic import detected for module '{'.'.join(module_parts)}'")
            return
        building.add(module_parts)
        try:
            module_path = resolve_module_path(
                base_dir,
                list(module_parts),
                dep_overrides=dep_overrides,
                extra_roots=extra_roots,
                config=resolver_config,
            )
            aster_module_labels.add(".".join(module_parts))
            module_source = module_path.read_text(encoding="utf-8")
            module_ast = parse_module(module_source)

            # Recurse on imports using the imported module's directory as base_dir.
            for decl in module_ast.declarations:
                if isinstance(decl, ast.ImportDecl):
                    compile_named_module(tuple(decl.module.parts), base_dir=module_path.parent)

            module_py = module_out_root.joinpath(*module_parts).with_suffix(".py")
            _ensure_pkg_inits(module_out_root, module_py.parent)
            module_py.parent.mkdir(parents=True, exist_ok=True)
            module_py.write_text(
                Transpiler(
                    module_import_prefix="_aster",
                    aster_module_labels=frozenset(aster_module_labels),
                ).transpile(module_ast),
                encoding="utf-8",
            )
            built.add(module_parts)
        except ModuleResolutionError as exc:
            message = str(exc)
            # Dependency-prefixed imports should remain strict.
            if message.startswith("Dependency '") or "dependency package" in message:
                result.errors.append(message)
            else:
                # Treat unresolved imports as external Python modules.
                pass
        except Exception as exc:
            label = ".".join(module_parts)
            result.errors.append(f"Internal error building module '{label}': {exc}")
        finally:
            building.remove(module_parts)

    # Build dependency graph for the entry module based on its imports.
    entry_base_dir = resolved_entry.parent
    for decl in entry_module.declarations:
        if isinstance(decl, ast.ImportDecl):
            compile_named_module(tuple(decl.module.parts), base_dir=entry_base_dir)

    if result.errors:
        return result

    # Finally, write the entry module.
    try:
        result.entry_py.write_text(
            Transpiler(
                module_import_prefix="_aster",
                aster_module_labels=frozenset(aster_module_labels),
            ).transpile(entry_module),
            encoding="utf-8",
        )
    except Exception as exc:
        result.errors.append(f"Internal error building entry module: {exc}")
    return result


def _ensure_pkg_inits(out_dir: Path, package_dir: Path) -> None:
    """Ensure `__init__.py` exists for each package directory under out_dir."""
    out_dir = out_dir.resolve()
    current = package_dir.resolve()
    while current != out_dir and out_dir in current.parents:
        init_py = current / "__init__.py"
        if not init_py.exists():
            current.mkdir(parents=True, exist_ok=True)
            init_py.write_text("", encoding="utf-8")
        current = current.parent
