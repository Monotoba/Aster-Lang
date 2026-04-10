# RECOVERY

Use this file after a power outage, machine restart, or agent context loss.

## Immediate recovery procedure

1. Open `STATUS.md`
2. Open `BACKLOG.md`
3. Open `tasks/TASK-STATUS.md`
4. Open `tasks/NEXT-STEPS.md`
5. Run the environment setup if needed
6. Run tests
7. Resume the highest-priority incomplete task

## Environment recovery

### Linux / macOS
```bash
bash ./setup-prj.sh
source .venv/bin/activate
pytest
```

### Windows
```powershell
powershell -ExecutionPolicy Bypass -File .\setup-prj.ps1
.\.venv\Scripts\Activate.ps1
pytest
```

## Priority order after interruption
1. restore green tests
2. inspect last touched files
3. inspect pending diffs
4. continue smallest open task
5. update `tasks/TASK-STATUS.md`

## If Git exists
```bash
git status
git log --oneline --decorate -n 15
```

## Always update before ending a work session
- task status
- next steps
- known risks
