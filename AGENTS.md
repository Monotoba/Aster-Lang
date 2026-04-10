# AGENTS.md

This repository is designed for both human developers and coding agents.

## Mandatory operating rules

1. Work test-first where practical.
2. Prefer refactoring and incremental evolution over rewrites.
3. Keep the language spec, implementation, and examples in sync.
4. Make small, reviewable commits.
5. Update `STATUS.md`, `BACKLOG.md`, and `tasks/TASK-STATUS.md` after meaningful work.
6. Never mark work complete unless:
   - tests pass
   - docs are updated
   - examples still agree with the implementation
7. Preserve human readability over cleverness.

## Development order

1. lexer
2. parser
3. AST
4. semantic model
5. interpreter
6. formatter
7. compiler / IR
8. bytecode VM or native backend
9. package manager and toolchain polish

## TDD expectations

Before implementing a new language feature:

1. add or update grammar docs
2. add parser / semantic / interpreter tests
3. implement the smallest working behavior
4. add formatting tests
5. update examples and reference docs
6. commit

## Required commands before commit

### Linux / macOS
```bash
source .venv/bin/activate
pytest
ruff check .
mypy src
```

### Windows PowerShell
```powershell
.\.venv\Scripts\Activate.ps1
pytest
ruff check .
mypy src
```

## Commit style

Use focused commits:
- `feat(parser): add tuple pattern parsing`
- `feat(types): add borrowed reference type nodes`
- `test(formatter): cover block indentation normalization`
- `docs(spec): clarify smart pointer categories`

## Continuity documents

- `STATUS.md`
- `BACKLOG.md`
- `RECOVERY.md`
- `tasks/TASK-STATUS.md`
- `tasks/NEXT-STEPS.md`

If interrupted by power loss or context loss, recover from those files first.
