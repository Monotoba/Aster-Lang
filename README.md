# Aster Language GPT Starter Repository

Aster is a human-first general-purpose programming language and toolchain project.
This repository is a **project bootstrap kit** for designing and implementing:

- the Aster language
- the Aster interpreter
- the Aster compiler
- the Aster formatter
- the Aster parser and grammar tools
- supporting documentation, examples, and developer workflow

This package is structured so a human developer or coding agent can unzip it, run the setup script, initialize Git, run tests, and continue development immediately.

## Included

- language and toolchain design documents
- Bottlecaps-compatible EBNF grammars
- parser / railroad diagram guidance
- scaffold Python package for the future toolchain
- tests-first workflow skeleton
- bootstrap scripts for Linux, macOS, and Windows
- AI assistant instructions for Codex, Claude Code, Gemini, Aider, and similar tools
- backlog, status, recovery, and handoff documents
- GPL-2.0 license

## Quick start

### Linux / macOS

```bash
cd aster-lang-gpt
bash ./setup-prj.sh
source .venv/bin/activate
pytest
python -m aster_lang --help
```

### Windows PowerShell

```powershell
cd aster-lang-gpt
powershell -ExecutionPolicy Bypass -File .\setup-prj.ps1
.\.venv\Scripts\Activate.ps1
pytest
python -m aster_lang --help
```

## Expected workflow

1. Run the bootstrap script.
2. Review `STATUS.md`, `BACKLOG.md`, and `RECOVERY.md`.
3. Read `AGENTS.md` and the AI-specific notes in `ai/`.
4. Review the language docs in `docs/language/`.
5. Implement changes test-first.
6. Run:
   - `pytest`
   - `ruff check .`
   - `mypy src`
7. Commit with a clear message.

## Repository map

- `src/aster_lang/` — scaffold code
- `tests/` — unit tests
- `docs/` — user and developer documentation
- `grammar/` — EBNF grammars for Bottlecaps and internal use
- `examples/` — tiny Aster examples
- `scripts/` — helper scripts
- `tasks/` — recovery-oriented task tracking
- `ai/` — AI-specific instructions and workflow notes

## Current state

This repo is intentionally a **strong scaffold**, not a completed implementation.
The goal is to provide:

- coherent language direction
- practical project structure
- test and tooling discipline
- continuity documents for long-running development

## License

GPL-2.0-only. See `LICENSE`.
