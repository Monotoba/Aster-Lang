from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TypeAlias

import pytest

from aster_lang.cli import main

CapsysFixture: TypeAlias = pytest.CaptureFixture[str]


def test_version_command_returns_zero() -> None:
    assert main(["version"]) == 0


def test_backends_command_lists_backends(capsys: CapsysFixture) -> None:
    assert main(["backends"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert any(line.startswith("python:") for line in lines)
    assert any(line.startswith("vm:") for line in lines)
    assert any(line.startswith("c:") for line in lines)


def test_run_command_loads_sibling_module(tmp_path: Path, capsys: CapsysFixture) -> None:
    (tmp_path / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use helpers\n" "fn main():\n" "    print(helpers.answer())\n",
        encoding="utf-8",
    )

    assert main(["run", str(program)]) == 0
    assert capsys.readouterr().out.strip() == "42"


def test_run_command_supports_vm_backend(tmp_path: Path, capsys: CapsysFixture) -> None:
    (tmp_path / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use helpers\n" "fn main():\n" "    print(helpers.answer())\n",
        encoding="utf-8",
    )

    assert main(["run", str(program), "--backend", "vm"]) == 0
    assert capsys.readouterr().out.strip() == "42"


def test_run_command_reports_missing_module(tmp_path: Path, capsys: CapsysFixture) -> None:
    program = tmp_path / "main.aster"
    program.write_text(
        "use missing\n" "fn main():\n" '    print("nope")\n',
        encoding="utf-8",
    )

    assert main(["run", str(program)]) == 1
    captured = capsys.readouterr()
    assert "Module not found" in captured.out


def test_run_command_reports_cyclic_import(tmp_path: Path, capsys: CapsysFixture) -> None:
    (tmp_path / "a.aster").write_text("use b\nfn value() -> Int:\n    return 1\n", encoding="utf-8")
    (tmp_path / "b.aster").write_text("use a\nfn value() -> Int:\n    return 2\n", encoding="utf-8")
    program = tmp_path / "main.aster"
    program.write_text(
        "use a\n" "fn main():\n" "    print(a.value())\n",
        encoding="utf-8",
    )

    assert main(["run", str(program)]) == 1
    captured = capsys.readouterr()
    assert "Cyclic import detected" in captured.out


def test_run_command_resolves_parent_package_root(tmp_path: Path, capsys: CapsysFixture) -> None:
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    program = app_dir / "main.aster"
    program.write_text(
        "use lib.helpers\n" "fn main():\n" "    print(helpers.answer())\n",
        encoding="utf-8",
    )

    assert main(["run", str(program)]) == 0
    assert capsys.readouterr().out.strip() == "42"


def test_run_command_resolves_manifest_module_root(tmp_path: Path, capsys: CapsysFixture) -> None:
    (tmp_path / "aster.toml").write_text(
        "[modules]\n" 'search_roots = ["src"]\n',
        encoding="utf-8",
    )
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    program = app_dir / "main.aster"
    program.write_text(
        "use helpers\n" "fn main():\n" "    print(helpers.answer())\n",
        encoding="utf-8",
    )

    assert main(["run", str(program)]) == 0
    assert capsys.readouterr().out.strip() == "42"


def test_run_command_resolves_current_package_name_prefix(
    tmp_path: Path, capsys: CapsysFixture
) -> None:
    (tmp_path / "aster.toml").write_text(
        "[package]\n" 'name = "app"\n' "[modules]\n" 'search_roots = ["src"]\n',
        encoding="utf-8",
    )
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    program = app_dir / "main.aster"
    program.write_text(
        "use app.helpers\n" "fn main():\n" "    print(helpers.answer())\n",
        encoding="utf-8",
    )

    assert main(["run", str(program)]) == 0
    assert capsys.readouterr().out.strip() == "42"


def test_run_command_reports_invalid_manifest(tmp_path: Path, capsys: CapsysFixture) -> None:
    (tmp_path / "aster.toml").write_text(
        "[package]\n" "name = 42\n",
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use missing\n" "fn main():\n" '    print("nope")\n',
        encoding="utf-8",
    )

    assert main(["run", str(program)]) == 1
    captured = capsys.readouterr()
    assert "package.name must be a string" in captured.out


def test_run_command_resolves_declared_dependency(tmp_path: Path, capsys: CapsysFixture) -> None:
    dep_dir = tmp_path / "vendor" / "math"
    dep_dir.mkdir(parents=True)
    (dep_dir / "utils.aster").write_text(
        "pub fn double(n: Int) -> Int:\n" "    return n + n\n",
        encoding="utf-8",
    )
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'math = { path = "vendor/math" }\n',
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils\n" "fn main():\n" "    print(utils.double(21))\n",
        encoding="utf-8",
    )

    assert main(["run", str(program)]) == 0
    assert capsys.readouterr().out.strip() == "42"


def test_run_command_reports_dependency_missing_path_key(
    tmp_path: Path, capsys: CapsysFixture
) -> None:
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'bad = { version = "1.0" }\n',
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use bad.mod\n" "fn main():\n" '    print("nope")\n',
        encoding="utf-8",
    )

    assert main(["run", str(program)]) == 1
    assert "missing a 'path' key" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# --dep and --search-root CLI override flags
# ---------------------------------------------------------------------------


def test_run_dep_flag_resolves_module(tmp_path: Path, capsys: CapsysFixture) -> None:
    dep_dir = tmp_path / "external" / "math"
    dep_dir.mkdir(parents=True)
    (dep_dir / "utils.aster").write_text(
        "pub fn triple(n: Int) -> Int:\n" "    return n + n + n\n",
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils\n" "fn main():\n" "    print(utils.triple(7))\n",
        encoding="utf-8",
    )

    assert main(["run", str(program), "--dep", f"math={dep_dir}"]) == 0
    assert capsys.readouterr().out.strip() == "21"


def test_run_dep_flag_resolves_module_with_vm_backend(
    tmp_path: Path, capsys: CapsysFixture
) -> None:
    dep_dir = tmp_path / "external" / "math"
    dep_dir.mkdir(parents=True)
    (dep_dir / "utils.aster").write_text(
        "pub fn triple(n: Int) -> Int:\n" "    return n + n + n\n",
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils\n" "fn main():\n" "    print(utils.triple(7))\n",
        encoding="utf-8",
    )

    assert main(["run", str(program), "--backend", "vm", "--dep", f"math={dep_dir}"]) == 0
    assert capsys.readouterr().out.strip() == "21"


def test_run_dep_flag_overrides_manifest_entry(tmp_path: Path, capsys: CapsysFixture) -> None:
    # Manifest declares math pointing at old_math; CLI overrides it to new_math.
    old_dir = tmp_path / "old_math"
    old_dir.mkdir()
    (old_dir / "utils.aster").write_text(
        "pub fn answer() -> Int:\n    return 0\n",
        encoding="utf-8",
    )
    new_dir = tmp_path / "new_math"
    new_dir.mkdir()
    (new_dir / "utils.aster").write_text(
        "pub fn answer() -> Int:\n    return 42\n",
        encoding="utf-8",
    )
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'math = { path = "old_math" }\n',
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils\n" "fn main():\n" "    print(utils.answer())\n",
        encoding="utf-8",
    )

    assert main(["run", str(program), "--dep", f"math={new_dir}"]) == 0
    assert capsys.readouterr().out.strip() == "42"


def test_run_search_root_flag_resolves_module(tmp_path: Path, capsys: CapsysFixture) -> None:
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "helpers.aster").write_text(
        "pub fn greet() -> String:\n" '    return "hello"\n',
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use helpers\n" "fn main():\n" "    print(helpers.greet())\n",
        encoding="utf-8",
    )

    assert main(["run", str(program), "--search-root", str(lib_dir)]) == 0
    assert capsys.readouterr().out.strip() == "hello"


def test_run_invalid_dep_flag_format_returns_error(tmp_path: Path, capsys: CapsysFixture) -> None:
    program = tmp_path / "main.aster"
    program.write_text('fn main():\n    print("ok")\n', encoding="utf-8")

    assert main(["run", str(program), "--dep", "nodeppath"]) == 1
    assert "NAME=PATH" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# check command
# ---------------------------------------------------------------------------


def test_check_command_returns_zero_on_valid_program(tmp_path: Path, capsys: CapsysFixture) -> None:
    program = tmp_path / "main.aster"
    program.write_text(
        "fn main():\n" "    x := 1\n",
        encoding="utf-8",
    )
    assert main(["check", str(program)]) == 0
    assert capsys.readouterr().out.strip() == ""


def test_check_command_reports_semantic_errors(tmp_path: Path, capsys: CapsysFixture) -> None:
    program = tmp_path / "main.aster"
    program.write_text(
        "fn main():\n" "    x := y\n",
        encoding="utf-8",
    )
    assert main(["check", str(program)]) == 1
    captured = capsys.readouterr()
    assert "Undefined variable 'y'" in captured.out


def test_check_command_resolves_declared_dependency(tmp_path: Path, capsys: CapsysFixture) -> None:
    dep_dir = tmp_path / "vendor" / "math"
    dep_dir.mkdir(parents=True)
    (dep_dir / "utils.aster").write_text(
        "pub fn double(n: Int) -> Int:\n" "    return n + n\n",
        encoding="utf-8",
    )
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'math = { path = "vendor/math" }\n',
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils: double\n" "fn main():\n" "    x := double(2)\n",
        encoding="utf-8",
    )

    assert main(["check", str(program)]) == 0
    assert capsys.readouterr().out.strip() == ""


def test_check_command_resolves_dep_override(tmp_path: Path, capsys: CapsysFixture) -> None:
    old_dir = tmp_path / "old_math"
    old_dir.mkdir()
    (old_dir / "utils.aster").write_text(
        "pub fn answer() -> Int:\n    return 0\n",
        encoding="utf-8",
    )
    new_dir = tmp_path / "new_math"
    new_dir.mkdir()
    (new_dir / "utils.aster").write_text(
        "pub fn answer() -> Int:\n    return 42\n",
        encoding="utf-8",
    )
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'math = { path = "old_math" }\n',
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils\n" "fn main():\n" "    x := 1\n",
        encoding="utf-8",
    )

    assert main(["check", str(program), "--dep", f"math={new_dir}"]) == 0
    assert capsys.readouterr().out.strip() == ""


def test_check_command_prints_ownership_warnings(tmp_path: Path, capsys: CapsysFixture) -> None:
    program = tmp_path / "main.aster"
    program.write_text(
        "fn f(x: &mut Int) -> *raw Int:\n" "    return x\n",
        encoding="utf-8",
    )

    assert main(["check", str(program), "--ownership", "warn"]) == 0
    out = capsys.readouterr().out
    assert "Borrow types" in out
    assert "Raw pointers" in out


def test_hir_command_prints_typed_output(tmp_path: Path, capsys: CapsysFixture) -> None:
    program = tmp_path / "main.aster"
    program.write_text(
        "fn add(a: Int, b: Int) -> Int:\n" "    return a + b\n",
        encoding="utf-8",
    )
    assert main(["hir", str(program)]) == 0
    out = capsys.readouterr().out
    assert "fn add(a: Int, b: Int) -> Int:" in out
    assert "# Int" in out


def test_check_invalid_dep_flag_format_returns_error(tmp_path: Path, capsys: CapsysFixture) -> None:
    program = tmp_path / "main.aster"
    program.write_text('fn main():\n    print("ok")\n', encoding="utf-8")

    assert main(["check", str(program), "--dep", "nodeppath"]) == 1
    assert "NAME=PATH" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# build command
# ---------------------------------------------------------------------------


def test_build_command_resolves_declared_dependency(tmp_path: Path, capsys: CapsysFixture) -> None:
    dep_dir = tmp_path / "vendor" / "math"
    dep_dir.mkdir(parents=True)
    (dep_dir / "utils.aster").write_text(
        "pub fn double(n: Int) -> Int:\n" "    return n + n\n",
        encoding="utf-8",
    )
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'math = { path = "vendor/math" }\n',
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils\n" "fn main():\n" "    print(utils.double(21))\n",
        encoding="utf-8",
    )

    assert main(["build", str(program)]) == 0
    _ = capsys.readouterr()
    out_dir = program.parent / "__aster_build__"
    entry_py = out_dir / "main.py"
    assert entry_py.exists()

    result = subprocess.run(
        [sys.executable, str(entry_py)],
        cwd=out_dir,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "42"


def test_build_command_supports_vm_backend(tmp_path: Path, capsys: CapsysFixture) -> None:
    dep_dir = tmp_path / "vendor" / "math"
    dep_dir.mkdir(parents=True)
    (dep_dir / "utils.aster").write_text(
        "pub fn double(n: Int) -> Int:\n" "    return n + n\n",
        encoding="utf-8",
    )
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'math = { path = "vendor/math" }\n',
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils\n" "fn main():\n" "    print(utils.double(21))\n",
        encoding="utf-8",
    )

    assert main(["build", str(program), "--backend", "vm"]) == 0
    _ = capsys.readouterr()
    out_dir = program.parent / "__aster_build__"
    entry_py = out_dir / "main.py"
    assert entry_py.exists()
    program_json = out_dir / "main.asterbc.json"
    assert program_json.exists()
    artifact_data = json.loads(program_json.read_text(encoding="utf-8"))
    assert artifact_data["kind"] == "program"
    assert artifact_data["format"] == "asterbc"
    assert artifact_data["version"] == 1
    assert artifact_data["integrity"]["algorithm"] == "sha256"
    assert (out_dir / "aster_lang" / "vm_runtime.py").exists()
    assert not (out_dir / "aster_lang" / "parser.py").exists()
    launcher = entry_py.read_text(encoding="utf-8")
    assert "json.loads" in launcher
    assert "PROGRAM = BCProgram(" not in launcher

    result = subprocess.run(
        [sys.executable, str(entry_py)],
        cwd=out_dir,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "42"


def test_build_command_supports_vm_signing_key(
    tmp_path: Path, capsys: CapsysFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    dep_dir = tmp_path / "vendor" / "math"
    dep_dir.mkdir(parents=True)
    (dep_dir / "utils.aster").write_text(
        "pub fn double(n: Int) -> Int:\n" "    return n + n\n",
        encoding="utf-8",
    )
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'math = { path = "vendor/math" }\n',
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils\n" "fn main():\n" "    print(utils.double(21))\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("ASTER_VM_SIGNING_KEY", "test-key")
    assert main(["build", str(program), "--backend", "vm"]) == 0
    _ = capsys.readouterr()
    out_dir = program.parent / "__aster_build__"
    entry_py = out_dir / "main.py"
    assert entry_py.exists()
    program_json = out_dir / "main.asterbc.json"
    assert program_json.exists()
    artifact_data = json.loads(program_json.read_text(encoding="utf-8"))
    assert artifact_data["signature"]["algorithm"] == "hmac-sha256"

    env = dict(os.environ)
    env["ASTER_VM_SIGNING_KEY"] = "test-key"
    result = subprocess.run(
        [sys.executable, str(entry_py)],
        cwd=out_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "42"


def test_build_preserves_python_imports(tmp_path: Path, capsys: CapsysFixture) -> None:
    # Build should not rewrite true Python imports like `os`.
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use os\n" "use helpers\n" "fn main():\n" "    print(helpers.answer())\n",
        encoding="utf-8",
    )

    assert main(["build", str(program), "--search-root", str(lib_dir)]) == 0
    _ = capsys.readouterr()

    out_dir = program.parent / "__aster_build__"
    entry_py = out_dir / "main.py"
    assert entry_py.exists()
    code = entry_py.read_text(encoding="utf-8")
    assert "import os" in code

    result = subprocess.run(
        [sys.executable, str(entry_py)],
        cwd=out_dir,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "42"


def test_build_command_out_dir(tmp_path: Path, capsys: CapsysFixture) -> None:
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "helpers.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use helpers\n" "fn main():\n" "    print(helpers.answer())\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "dist"
    assert (
        main(
            [
                "build",
                str(program),
                "--search-root",
                str(lib_dir),
                "--out-dir",
                str(out_dir),
            ]
        )
        == 0
    )
    _ = capsys.readouterr()

    entry_py = out_dir / "main.py"
    assert entry_py.exists()
    result = subprocess.run(
        [sys.executable, str(entry_py)],
        cwd=out_dir,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "42"


def test_build_command_resolves_dep_override(tmp_path: Path, capsys: CapsysFixture) -> None:
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'math = { path = "old_math" }\n',
        encoding="utf-8",
    )
    dep_dir = tmp_path / "new_math"
    dep_dir.mkdir()
    (dep_dir / "utils.aster").write_text(
        "pub fn answer() -> Int:\n" "    return 42\n",
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils\n" "fn main():\n" "    print(utils.answer())\n",
        encoding="utf-8",
    )

    assert main(["build", str(program), "--dep", f"math={dep_dir}"]) == 0
    _ = capsys.readouterr()
    out_dir = program.parent / "__aster_build__"
    entry_py = out_dir / "main.py"
    assert entry_py.exists()


def test_build_command_reports_missing_dependency(tmp_path: Path, capsys: CapsysFixture) -> None:
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'math = { path = "does_not_exist" }\n',
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils\n" "fn main():\n" '    print("ok")\n',
        encoding="utf-8",
    )

    assert main(["build", str(program)]) == 1
    captured = capsys.readouterr()
    assert "Dependency 'math' path not found" in captured.out


def test_build_invalid_dep_flag_format_returns_error(tmp_path: Path, capsys: CapsysFixture) -> None:
    program = tmp_path / "main.aster"
    program.write_text('fn main():\n    print("ok")\n', encoding="utf-8")

    assert main(["build", str(program), "--dep", "nodeppath"]) == 1
    assert "NAME=PATH" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# lockfile
# ---------------------------------------------------------------------------


def test_lock_command_writes_lockfile(tmp_path: Path, capsys: CapsysFixture) -> None:
    dep_dir = tmp_path / "vendor" / "math"
    dep_dir.mkdir(parents=True)
    (dep_dir / "utils.aster").write_text(
        "pub fn double(n: Int) -> Int:\n" "    return n + n\n",
        encoding="utf-8",
    )
    (tmp_path / "aster.toml").write_text(
        "[dependencies]\n" 'math = { path = "vendor/math" }\n',
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils\n" "fn main():\n" "    print(utils.double(21))\n",
        encoding="utf-8",
    )

    assert main(["lock", str(program)]) == 0
    _ = capsys.readouterr()
    lock_path = tmp_path / "aster.lock"
    assert lock_path.exists()
    contents = lock_path.read_text(encoding="utf-8")
    assert '"dependencies"' in contents
    assert '"math"' in contents


def test_build_uses_lockfile_even_if_manifest_changes(
    tmp_path: Path, capsys: CapsysFixture
) -> None:
    dep_dir = tmp_path / "vendor" / "math"
    dep_dir.mkdir(parents=True)
    (dep_dir / "utils.aster").write_text(
        "pub fn double(n: Int) -> Int:\n" "    return n + n\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "aster.toml"
    manifest.write_text(
        "[dependencies]\n" 'math = { path = "vendor/math" }\n',
        encoding="utf-8",
    )
    program = tmp_path / "main.aster"
    program.write_text(
        "use math.utils\n" "fn main():\n" "    print(utils.double(21))\n",
        encoding="utf-8",
    )

    lock_path = tmp_path / "aster.lock"
    assert main(["lock", str(program), "--lockfile", str(lock_path)]) == 0
    _ = capsys.readouterr()

    # Break the manifest; build should still work with the lockfile.
    manifest.write_text(
        "[dependencies]\n" 'math = { path = "does_not_exist" }\n',
        encoding="utf-8",
    )

    assert main(["build", str(program), "--lockfile", str(lock_path), "--clean"]) == 0
    _ = capsys.readouterr()
    out_dir = tmp_path / "__aster_build__"
    entry_py = out_dir / "main.py"
    assert entry_py.exists()
    result = subprocess.run(
        [sys.executable, str(entry_py)],
        cwd=out_dir,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "42"


def test_check_lockfile_cannot_combine_with_dep_overrides(
    tmp_path: Path, capsys: CapsysFixture
) -> None:
    program = tmp_path / "main.aster"
    program.write_text('fn main():\n    print("ok")\n', encoding="utf-8")
    lock_path = tmp_path / "aster.lock"
    lock_path.write_text(
        '{"version": 1, "project_root": ".", "package_name": null, '
        '"search_roots": ["."], "dependencies": {}}\n',
        encoding="utf-8",
    )

    assert (
        main(
            [
                "check",
                str(program),
                "--lockfile",
                str(lock_path),
                "--dep",
                "x=.",
            ]
        )
        == 1
    )
    assert "--lockfile cannot be combined" in capsys.readouterr().out
