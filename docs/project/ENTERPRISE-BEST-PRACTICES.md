# Enterprise Best Practices

## Repository discipline
- use Git from day one
- commit frequently with focused messages
- require green tests before merge
- keep docs in the same PR as behavior changes

## Quality gates
- pytest
- ruff
- mypy
- CI on every push and PR

## Architecture discipline
- stable package boundaries
- explicit interfaces between lexer, parser, semantics, and runtime
- avoid hidden global state
- design for incremental parsing and future language server support

## Documentation discipline
- examples must be executable or near-executable
- docs must specify implemented vs planned behavior
- grammar changes must update railroad-diagram source

## Recovery discipline
- maintain `STATUS.md`, `BACKLOG.md`, and `tasks/`
- keep unfinished work and risks visible
