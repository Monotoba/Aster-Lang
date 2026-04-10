# Contributing

## Ground rules

- prefer incremental changes
- keep tests green
- update docs with behavior changes
- do not rewrite broad subsystems unless explicitly approved
- use focused Git commits

## Before opening a PR or handing off work
- run `pytest`
- run `ruff check .`
- run `mypy src`
- update `STATUS.md` if repository state changed
- update `tasks/TASK-STATUS.md` and `tasks/NEXT-STEPS.md`
