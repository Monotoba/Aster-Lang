$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$PythonBin = if ($env:PYTHON_BIN) { $env:PYTHON_BIN } else { "python" }

Write-Host "[aster] using python: $PythonBin"
& $PythonBin -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip wheel setuptools
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"

if (-not (Test-Path .git)) {
    git init
    git branch -M main
}

try { pre-commit install } catch {}

& .\.venv\Scripts\pytest.exe
& .\.venv\Scripts\ruff.exe check .
& .\.venv\Scripts\mypy.exe src

Write-Host ""
Write-Host "[aster] setup complete"
Write-Host "[aster] activate with: .\.venv\Scripts\Activate.ps1"
