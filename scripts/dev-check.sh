#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
pytest
ruff check .
mypy src
