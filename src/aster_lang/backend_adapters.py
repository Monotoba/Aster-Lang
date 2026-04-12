"""Concrete backend adapters."""

from __future__ import annotations

import shutil
from dataclasses import dataclass

from aster_lang.backend import BackendArtifact, BackendBuildOptions, BackendRegistry
from aster_lang.builder import build_project, build_project_hir, build_project_vm
from aster_lang.c_transpiler import CBuildError, CTranspiler, compile_c
from aster_lang.mir import lower_hir


@dataclass
class PythonBackendAdapter:
    name: str = "python"
    supported_formats: tuple[str, ...] = ("python",)

    def build(self, options: BackendBuildOptions) -> BackendArtifact:
        if options.entry_module is None:
            return BackendArtifact(
                entry_path=options.entry_path,
                outputs=[],
                errors=["Python backend requires a parsed entry module"],
            )

        # Check cache if enabled
        if options.cache_enabled and options.cache_manager is not None:
            key = options.cache_manager.compute_key(
                options.entry_path,
                backend=self.name,
                artifact_format=None,
                ownership_mode=options.ownership_mode,
                types_mode=options.types_mode,
                resolver_config=options.resolver_config,
            )
            cached = options.cache_manager.get(options.entry_path, key, self.name, None)
            if cached is not None:
                metadata, artifact_path = cached
                output_dir = options.out_dir or options.entry_path.parent / "__aster_build__"
                output_dir.mkdir(parents=True, exist_ok=True)
                dest_path = output_dir / f"{options.entry_path.stem}.py"
                shutil.copy2(artifact_path, dest_path)
                return BackendArtifact(
                    entry_path=dest_path,
                    outputs=[dest_path],
                    metadata={"out_dir": output_dir, "cached": True},
                    format="python",
                    errors=[],
                    cache_hit=True,
                )

        result = build_project(
            entry_path=options.entry_path,
            entry_module=options.entry_module,
            dep_overrides=options.dep_overrides,
            extra_roots=options.extra_roots,
            out_dir=options.out_dir,
            clean=options.clean,
            resolver_config=options.resolver_config,
        )
        outputs = [result.entry_py]

        # Store in cache if enabled
        if options.cache_enabled and options.cache_manager is not None:
            key = options.cache_manager.compute_key(
                options.entry_path,
                backend=self.name,
                artifact_format=None,
                ownership_mode=options.ownership_mode,
                types_mode=options.types_mode,
                resolver_config=options.resolver_config,
            )
            options.cache_manager.put(
                options.entry_path,
                key,
                self.name,
                None,
                options.ownership_mode,
                options.types_mode,
                result.entry_py,
            )

        return BackendArtifact(
            entry_path=result.entry_py,
            outputs=outputs,
            metadata={"out_dir": result.out_dir},
            format="python",
            errors=list(result.errors),
            cache_hit=False,
        )


@dataclass
class VMBackendAdapter:
    name: str = "vm"
    supported_formats: tuple[str, ...] = ("json", "binary")

    def build(self, options: BackendBuildOptions) -> BackendArtifact:
        artifact_format = options.artifact_format or "json"

        # Check cache if enabled
        if options.cache_enabled and options.cache_manager is not None:
            key = options.cache_manager.compute_key(
                options.entry_path,
                backend=self.name,
                artifact_format=artifact_format,
                ownership_mode=options.ownership_mode,
                types_mode=options.types_mode,
                resolver_config=options.resolver_config,
            )
            cached = options.cache_manager.get(options.entry_path, key, self.name, artifact_format)
            if cached is not None:
                metadata, artifact_path = cached
                output_dir = options.out_dir or options.entry_path.parent / "__aster_build__"
                output_dir.mkdir(parents=True, exist_ok=True)
                entry_py = output_dir / f"{options.entry_path.stem}.py"
                bc_dest = output_dir / artifact_path.name
                shutil.copy2(artifact_path, bc_dest)
                return BackendArtifact(
                    entry_path=entry_py,
                    outputs=[entry_py, bc_dest],
                    metadata={"out_dir": output_dir, "cached": True},
                    format=artifact_format,
                    errors=[],
                    cache_hit=True,
                )

        result = build_project_vm(
            entry_path=options.entry_path,
            dep_overrides=options.dep_overrides,
            extra_roots=options.extra_roots,
            out_dir=options.out_dir,
            clean=options.clean,
            resolver_config=options.resolver_config,
            artifact_format=artifact_format,
        )
        outputs = [result.entry_py]

        # Store in cache if enabled
        if options.cache_enabled and options.cache_manager is not None:
            key = options.cache_manager.compute_key(
                options.entry_path,
                backend=self.name,
                artifact_format=artifact_format,
                ownership_mode=options.ownership_mode,
                types_mode=options.types_mode,
                resolver_config=options.resolver_config,
            )
            bc_path = result.out_dir / f"{options.entry_path.stem}.asterbc"
            if artifact_format != "binary":
                bc_path = result.out_dir / f"{options.entry_path.stem}.asterbc.json"
            if bc_path.exists():
                options.cache_manager.put(
                    options.entry_path,
                    key,
                    self.name,
                    artifact_format,
                    options.ownership_mode,
                    options.types_mode,
                    bc_path,
                )

        return BackendArtifact(
            entry_path=result.entry_py,
            outputs=outputs,
            metadata={"out_dir": result.out_dir},
            format=artifact_format,
            errors=list(result.errors),
            cache_hit=False,
        )


@dataclass
class CBackendAdapter:
    name: str = "c"
    supported_formats: tuple[str, ...] = ("c",)

    def build(self, options: BackendBuildOptions) -> BackendArtifact:
        output_dir = options.out_dir or options.entry_path.parent / "__aster_build__"
        if options.clean and output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        hir_result = build_project_hir(
            entry_path=options.entry_path,
            dep_overrides=options.dep_overrides,
            extra_roots=options.extra_roots,
            resolver_config=options.resolver_config,
        )
        mmod = lower_hir(hir_result.module)

        c_path = output_dir / f"{options.entry_path.stem}.c"
        c_code = CTranspiler().transpile(mmod)
        c_path.write_text(c_code, encoding="utf-8")

        errors = list(hir_result.errors)

        bin_path = output_dir / options.entry_path.stem
        try:
            warnings = compile_c(c_code, bin_path)
            errors.extend(warnings)
        except CBuildError as exc:
            errors.append(str(exc))
            bin_path = c_path

        return BackendArtifact(
            entry_path=bin_path,
            outputs=[c_path, bin_path],
            format="c",
            metadata={"out_dir": output_dir},
            errors=errors,
            cache_hit=False,
        )


def get_default_backend_registry() -> BackendRegistry:
    registry = BackendRegistry()
    registry.register(PythonBackendAdapter())
    registry.register(VMBackendAdapter())
    registry.register(CBackendAdapter())
    return registry
