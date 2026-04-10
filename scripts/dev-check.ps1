$ErrorActionPreference = "Stop"
& .\.venv\Scripts\pytest.exe
& .\.venv\Scripts\ruff.exe check .
& .\.venv\Scripts\mypy.exe src
