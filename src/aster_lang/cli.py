from __future__ import annotations

import argparse
from pathlib import Path

from aster_lang.ast_printer import dump
from aster_lang.backend import BackendBuildOptions
from aster_lang.backend_adapters import get_default_backend_registry
from aster_lang.compiler import compile_source
from aster_lang.formatter import format_source
from aster_lang.hir import dump_hir
from aster_lang.interpreter import interpret_source
from aster_lang.lockfile import (
    LOCKFILE_VERSION,
    Lockfile,
    LockfileError,
    read_lockfile,
    write_lockfile,
)
from aster_lang.module_resolution import ModuleSearchConfig, discover_module_search_config
from aster_lang.parser import parse_module
from aster_lang.repl import run_repl
from aster_lang.semantic import OwnershipMode, SemanticAnalyzer
from aster_lang.vm import VMError, run_path_vm


def _parse_dep_overrides(dep_specs: list[str]) -> dict[str, Path] | None:
    dep_overrides: dict[str, Path] = {}
    for spec in dep_specs:
        if "=" not in spec:
            raise ValueError(f"Invalid --dep value '{spec}': expected NAME=PATH")
        name, _, path_str = spec.partition("=")
        dep_overrides[name.strip()] = Path(path_str.strip())
    return dep_overrides or None


def _parse_extra_roots(root_specs: list[str]) -> tuple[Path, ...]:
    return tuple(Path(r) for r in root_specs)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aster", description="Aster language scaffold CLI")
    sub = parser.add_subparsers(dest="command", required=False)

    run_p = sub.add_parser("run", help="interpret Aster source")
    run_p.add_argument("path", type=Path)
    run_p.add_argument(
        "--backend",
        choices=["interpreter", "vm"],
        default="interpreter",
        help="execution backend (default: interpreter)",
    )
    run_p.add_argument(
        "--dep",
        action="append",
        metavar="NAME=PATH",
        default=[],
        help="override or declare a dependency path (repeatable)",
    )
    run_p.add_argument(
        "--search-root",
        action="append",
        metavar="PATH",
        default=[],
        help="prepend an extra module search root (repeatable)",
    )

    fmt_p = sub.add_parser("fmt", help="format Aster source")
    fmt_p.add_argument("path", type=Path)

    vm_p = sub.add_parser("vm", help="run Aster using the experimental bytecode VM backend")
    vm_p.add_argument("path", type=Path)
    vm_p.add_argument(
        "--dep",
        action="append",
        metavar="NAME=PATH",
        default=[],
        help="override or declare a dependency path (repeatable)",
    )
    vm_p.add_argument(
        "--search-root",
        action="append",
        metavar="PATH",
        default=[],
        help="prepend an extra module search root (repeatable)",
    )

    check_p = sub.add_parser("check", help="parse and semantically analyze Aster source")
    check_p.add_argument("path", type=Path)
    check_p.add_argument(
        "--dep",
        action="append",
        metavar="NAME=PATH",
        default=[],
        help="override or declare a dependency path (repeatable)",
    )
    check_p.add_argument(
        "--search-root",
        action="append",
        metavar="PATH",
        default=[],
        help="prepend an extra module search root (repeatable)",
    )
    check_p.add_argument(
        "--lockfile",
        type=Path,
        default=None,
        help="use an explicit lockfile for module resolution (disables --dep/--search-root)",
    )
    check_p.add_argument(
        "--ownership",
        choices=["off", "warn", "deny"],
        default="off",
        help="ownership/borrow surface diagnostics mode (default: off)",
    )
    check_p.add_argument(
        "--types",
        choices=["loose", "strict"],
        default="loose",
        help="type checking strictness (default: loose)",
    )

    build_p = sub.add_parser("build", help="compile Aster source")
    build_p.add_argument("path", type=Path)
    build_p.add_argument(
        "--backend",
        choices=["python", "vm", "c"],
        default="python",
        help="build backend (default: python; c is a placeholder)",
    )
    build_p.add_argument(
        "--vm-artifact-format",
        choices=["json", "binary"],
        default="json",
        help="VM artifact format when --backend vm (default: json)",
    )
    build_p.add_argument(
        "--dep",
        action="append",
        metavar="NAME=PATH",
        default=[],
        help="override or declare a dependency path (repeatable)",
    )
    build_p.add_argument(
        "--search-root",
        action="append",
        metavar="PATH",
        default=[],
        help="prepend an extra module search root (repeatable)",
    )
    build_p.add_argument(
        "--lockfile",
        type=Path,
        default=None,
        help="use an explicit lockfile for module resolution (disables --dep/--search-root)",
    )
    build_p.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="output directory for runnable build artifacts (default: ./__aster_build__)",
    )
    build_p.add_argument(
        "--clean",
        action="store_true",
        help="delete the output directory before building",
    )
    build_p.add_argument(
        "--ownership",
        choices=["off", "warn", "deny"],
        default="off",
        help="ownership/borrow surface diagnostics mode (default: off)",
    )
    build_p.add_argument(
        "--types",
        choices=["loose", "strict"],
        default="loose",
        help="type checking strictness (default: loose)",
    )

    ast_p = sub.add_parser("ast", help="print parse tree of Aster source")
    ast_p.add_argument("path", type=Path)

    hir_p = sub.add_parser("hir", help="print typed HIR (debug)")
    hir_p.add_argument("path", type=Path)

    lock_p = sub.add_parser("lock", help="write an aster.lock file for reproducible builds")
    lock_p.add_argument("path", type=Path)
    lock_p.add_argument(
        "--dep",
        action="append",
        metavar="NAME=PATH",
        default=[],
        help="override or declare a dependency path (repeatable)",
    )
    lock_p.add_argument(
        "--search-root",
        action="append",
        metavar="PATH",
        default=[],
        help="prepend an extra module search root (repeatable)",
    )

    sub.add_parser("backends", help="list available build backends")
    lock_p.add_argument(
        "--lockfile",
        type=Path,
        default=None,
        help="output lockfile path (default: <project-root>/aster.lock)",
    )

    sub.add_parser("repl", help="start interactive REPL")
    sub.add_parser("version", help="show version")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            dep_overrides = _parse_dep_overrides(args.dep)
        except ValueError as exc:
            print(str(exc))
            return 1
        extra_roots = _parse_extra_roots(args.search_root)

        if args.backend == "vm":
            try:
                out = run_path_vm(
                    args.path,
                    dep_overrides=dep_overrides,
                    extra_roots=extra_roots,
                )
            except VMError as exc:
                print(str(exc))
                return 1
            if out:
                print(out)
            return 0

        source = args.path.read_text(encoding="utf-8")
        result = interpret_source(
            source,
            base_dir=args.path.parent,
            dep_overrides=dep_overrides,
            extra_roots=extra_roots,
        )
        if result.error:
            print(result.error)
            return 1
        if result.output:
            print(result.output)
        return 0

    if args.command == "ast":
        try:
            source = args.path.read_text(encoding="utf-8")
            module = parse_module(source)
            print(dump(module))
        except Exception as exc:
            print(f"Parse error: {exc}")
            return 1
        return 0

    if args.command == "hir":
        try:
            source = args.path.read_text(encoding="utf-8")
            module = parse_module(source)
        except Exception as exc:
            print(f"Parse error: {exc}")
            return 1
        analyzer = SemanticAnalyzer(base_dir=args.path.parent, allow_external_imports=True)
        ok = analyzer.analyze(module)
        for warn in analyzer.warnings:
            print(warn)
        if not ok:
            for err in analyzer.errors:
                print(err)
            return 1
        print(dump_hir(module, analyzer), end="")
        return 0

    if args.command == "fmt":
        source = args.path.read_text(encoding="utf-8")
        print(format_source(source))
        return 0

    if args.command == "vm":
        try:
            dep_overrides = _parse_dep_overrides(args.dep)
        except ValueError as exc:
            print(str(exc))
            return 1
        extra_roots = _parse_extra_roots(args.search_root)
        try:
            out = run_path_vm(
                args.path,
                dep_overrides=dep_overrides,
                extra_roots=extra_roots,
            )
        except VMError as exc:
            print(str(exc))
            return 1
        if out:
            print(out)
        return 0

    if args.command == "check":
        if args.lockfile is not None and (args.dep or args.search_root):
            print("--lockfile cannot be combined with --dep/--search-root")
            return 1
        check_resolver_config: ModuleSearchConfig | None = None
        if args.lockfile is not None:
            try:
                check_resolver_config = read_lockfile(args.lockfile).to_config()
            except LockfileError as exc:
                print(str(exc))
                return 1

        try:
            check_dep_overrides = _parse_dep_overrides(args.dep)
        except ValueError as exc:
            print(str(exc))
            return 1
        check_extra_roots = _parse_extra_roots(args.search_root)

        source = args.path.read_text(encoding="utf-8")
        module = parse_module(source)
        analyzer = SemanticAnalyzer(
            base_dir=args.path.parent,
            dep_overrides=check_dep_overrides,
            extra_roots=check_extra_roots,
            resolver_config=check_resolver_config,
            allow_external_imports=True,
            strict_types=(args.types == "strict"),
            ownership_mode=OwnershipMode(args.ownership),
        )
        ok = analyzer.analyze(module)
        for warn in analyzer.warnings:
            print(warn)
        if ok:
            return 0
        for err in analyzer.errors:
            print(err)
        return 1

    if args.command == "build":
        if args.lockfile is not None and (args.dep or args.search_root):
            print("--lockfile cannot be combined with --dep/--search-root")
            return 1
        build_resolver_config: ModuleSearchConfig | None = None
        if args.lockfile is not None:
            try:
                build_resolver_config = read_lockfile(args.lockfile).to_config()
            except LockfileError as exc:
                print(str(exc))
                return 1

        try:
            build_dep_overrides = _parse_dep_overrides(args.dep)
        except ValueError as exc:
            print(str(exc))
            return 1
        build_extra_roots = _parse_extra_roots(args.search_root)

        source = args.path.read_text(encoding="utf-8")
        try:
            module = parse_module(source)
        except Exception:
            compile_artifact = compile_source(source)
            print(compile_artifact.summary())
            return 1

        analyzer = SemanticAnalyzer(
            base_dir=args.path.parent,
            dep_overrides=build_dep_overrides,
            extra_roots=build_extra_roots,
            resolver_config=build_resolver_config,
            allow_external_imports=True,
            strict_types=(args.types == "strict"),
            ownership_mode=OwnershipMode(args.ownership),
        )
        ok = analyzer.analyze(module)
        for warn in analyzer.warnings:
            print(warn)
        if not ok:
            for err in analyzer.errors:
                print(err)
            return 1

        registry = get_default_backend_registry()
        adapter = registry.get(args.backend)
        build_options = BackendBuildOptions(
            entry_path=args.path,
            entry_module=module if args.backend == "python" else None,
            dep_overrides=build_dep_overrides,
            extra_roots=build_extra_roots,
            out_dir=args.out_dir,
            clean=args.clean,
            resolver_config=build_resolver_config,
            artifact_format=args.vm_artifact_format if args.backend == "vm" else None,
        )
        try:
            registry.validate_format(adapter, build_options.artifact_format)
        except ValueError as exc:
            print(str(exc))
            return 1
        backend_artifact = adapter.build(build_options)
        if backend_artifact.errors:
            print(f"Build failed: {'; '.join(backend_artifact.errors)}")
            return 1
        print(f"Built {args.path} → {backend_artifact.entry_path}")
        return 0

    if args.command == "lock":
        try:
            dep_overrides = _parse_dep_overrides(args.dep) or {}
        except ValueError as exc:
            print(str(exc))
            return 1
        extra_roots = _parse_extra_roots(args.search_root)

        base_dir = args.path.parent
        discovered = discover_module_search_config(base_dir)
        if discovered is None:
            # No manifest: lockfile still records a synthetic config based on CLI roots.
            project_root = base_dir.resolve()
            search_roots = (project_root, *extra_roots)
            dependencies = tuple((n, p.resolve()) for n, p in dep_overrides.items())
            config = ModuleSearchConfig(
                project_root=project_root,
                package_name=None,
                search_roots=tuple(Path(p).resolve() for p in search_roots),
                dependencies=dependencies,
            )
        else:
            # Apply CLI overrides the same way resolution would.
            merged_roots = tuple(
                Path(p).resolve() for p in (*extra_roots, *discovered.search_roots)
            )
            deps = {name: path for name, path in discovered.dependencies}
            deps.update({n: p.resolve() for n, p in dep_overrides.items()})
            config = ModuleSearchConfig(
                project_root=discovered.project_root,
                package_name=discovered.package_name,
                search_roots=merged_roots,
                dependencies=tuple(deps.items()),
            )

        lockfile_path = args.lockfile or (config.project_root / "aster.lock")
        lock = Lockfile(
            version=LOCKFILE_VERSION,
            project_root=config.project_root,
            package_name=config.package_name,
            search_roots=tuple(config.search_roots),
            dependencies=tuple(config.dependencies),
        )
        write_lockfile(lockfile_path, lock)
        print(f"Wrote lockfile: {lockfile_path}")
        return 0

    if args.command == "backends":
        registry = get_default_backend_registry()
        for name in registry.names():
            adapter = registry.get(name)
            formats = ", ".join(adapter.supported_formats)
            print(f"{name}: {formats}")
        return 0

    if args.command == "repl":
        run_repl()
        return 0

    if args.command == "version":
        print("aster-lang scaffold 0.1.0")
        return 0

    parser.print_help()
    return 0
