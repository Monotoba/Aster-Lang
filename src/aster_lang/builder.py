"""Build orchestration for compiling Aster projects.

The transpiler emits standard Python `import` statements. To make the output
runnable, the builder recursively compiles imported `.aster` modules into a
single output directory matching their qualified import names.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from aster_lang import ast
from aster_lang.bytecode import program_to_bytes, program_to_json
from aster_lang.compiler import HIRBuildResult, Transpiler
from aster_lang.module_resolution import (
    ModuleResolutionError,
    ModuleSearchConfig,
    resolve_module_path,
)
from aster_lang.parser import parse_module
from aster_lang.vm import VMError, compile_path_to_bytecode


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


def build_project_hir(
    *,
    entry_path: Path,
    dep_overrides: dict[str, Path] | None = None,
    extra_roots: tuple[Path, ...] = (),
    resolver_config: ModuleSearchConfig | None = None,
) -> HIRBuildResult:
    """Build an entry module into HIR."""
    from aster_lang.compiler import build_hir

    return build_hir(
        entry_path=entry_path,
        dep_overrides=dep_overrides,
        extra_roots=extra_roots,
        resolver_config=resolver_config,
    )


def build_project_vm(
    *,
    entry_path: Path,
    dep_overrides: dict[str, Path] | None = None,
    extra_roots: tuple[Path, ...] = (),
    out_dir: Path | None = None,
    clean: bool = False,
    resolver_config: ModuleSearchConfig | None = None,
    artifact_format: str = "json",
) -> BuildResult:
    """Build an entry module into a runnable Python launcher around VM bytecode."""
    resolved_entry = entry_path.resolve()
    output_dir = (out_dir or resolved_entry.parent / "__aster_build__").resolve()
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = BuildResult(
        out_dir=output_dir,
        entry_py=output_dir / f"{resolved_entry.stem}.py",
        errors=[],
    )

    try:
        program = compile_path_to_bytecode(
            resolved_entry,
            dep_overrides=dep_overrides,
            extra_roots=extra_roots,
            resolver_config=resolver_config,
        )
    except VMError as exc:
        result.errors.append(str(exc))
        return result

    runtime_dst = output_dir / "aster_lang"
    runtime_dst.mkdir(parents=True, exist_ok=True)
    runtime_src = Path(__file__).resolve().parent
    for name in ("__init__.py", "bytecode.py", "vm_runtime.py"):
        source_text = (runtime_src / name).read_text(encoding="utf-8")
        (runtime_dst / name).write_text(source_text, encoding="utf-8")
    if artifact_format == "binary":
        program_path = output_dir / f"{resolved_entry.stem}.asterbc"
    else:
        program_path = output_dir / f"{resolved_entry.stem}.asterbc.json"
    signing_key = os.environ.get("ASTER_VM_SIGNING_KEY")
    key_bytes = signing_key.encode("utf-8") if signing_key else None
    if artifact_format == "binary":
        program_path.write_bytes(program_to_bytes(program, signing_key=key_bytes))
    else:
        program_path.write_text(program_to_json(program, signing_key=key_bytes), encoding="utf-8")
    result.entry_py.write_text(
        _render_vm_launcher(program_path.name, artifact_format=artifact_format),
        encoding="utf-8",
    )
    return result


def _render_vm_launcher(program_filename: str, *, artifact_format: str) -> str:
    if artifact_format == "binary":
        read_lines = [
            "from aster_lang.bytecode import program_from_bytes",
            "from aster_lang.vm_runtime import VM",
            "",
            'if __name__ == "__main__":',
            f"    program_path = Path(__file__).with_name({program_filename!r})",
            "    program_data = program_path.read_bytes()",
            '    signing_key = os.environ.get("ASTER_VM_SIGNING_KEY")',
            '    key_bytes = signing_key.encode("utf-8") if signing_key else None',
            "    program = program_from_bytes(program_data, signing_key=key_bytes)",
            "    vm = VM(program)",
            "    vm.run_entry()",
            "    if vm.output:",
            '        print("\\n".join(vm.output))',
            "",
        ]
        return "\n".join(
            [
                "# Generated by the Aster VM builder",
                "import os",
                "from pathlib import Path",
                "",
                *read_lines,
            ]
        )
    return "\n".join(
        [
            "# Generated by the Aster VM builder",
            "import json",
            "import os",
            "from pathlib import Path",
            "",
            "from aster_lang.bytecode import program_from_data",
            "from aster_lang.vm_runtime import VM",
            "",
            'if __name__ == "__main__":',
            f"    program_path = Path(__file__).with_name({program_filename!r})",
            '    program_data = json.loads(program_path.read_text(encoding="utf-8"))',
            '    signing_key = os.environ.get("ASTER_VM_SIGNING_KEY")',
            '    key_bytes = signing_key.encode("utf-8") if signing_key else None',
            "    program = program_from_data(program_data, signing_key=key_bytes)",
            "    vm = VM(program)",
            "    vm.run_entry()",
            "    if vm.output:",
            '        print("\\n".join(vm.output))',
            "",
        ]
    )


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
