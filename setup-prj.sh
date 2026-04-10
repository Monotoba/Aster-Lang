#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

python_bin="${PYTHON_BIN:-python3}"

echo "[aster] using python: $python_bin"
"$python_bin" -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip wheel setuptools
python -m pip install -e ".[dev]"

if command -v git >/dev/null 2>&1; then
  if [ ! -d .git ]; then
    git init
    git branch -M main || true
  fi
  git config core.autocrlf input || true
fi

if command -v pre-commit >/dev/null 2>&1; then
  pre-commit install || true
fi

pytest
ruff check .
mypy src

echo
echo "[aster] setup complete"
echo "[aster] activate with: source .venv/bin/activate"
echo "[aster] next: review STATUS.md BACKLOG.md RECOVERY.md"
