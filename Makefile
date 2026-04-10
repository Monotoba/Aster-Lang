PYTHON=.venv/bin/python
PIP=.venv/bin/pip
PYTEST=.venv/bin/pytest
RUFF=.venv/bin/ruff
MYPY=.venv/bin/mypy

setup:
	bash ./setup-prj.sh

test:
	$(PYTEST)

lint:
	$(RUFF) check .

typecheck:
	$(MYPY) src

check: test lint typecheck
