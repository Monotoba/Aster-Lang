# BACKLOG

## Phase 1: repository and architecture
- [x] bootstrap repository layout
- [x] create language and toolchain design docs
- [x] create grammar files
- [x] create scaffold package
- [x] create tests and CI
- [ ] refine package boundaries after first parser milestone

## Phase 2: lexer and parser
- [x] implement token model
- [x] implement indentation-aware lexer
- [x] add lexer golden tests
- [x] implement parser for declarations
- [x] implement Pratt parser for expressions
- [ ] implement pattern parser (for match expressions)
- [ ] add parse tree round-trip debug printer

## Phase 3: semantic model
- [x] symbol tables
- [ ] module loader
- [x] type expression resolver
- [ ] ownership / borrow checking prototype (basic mutability checking done)
- [ ] trait resolution prototype
- [ ] effect tracking prototype

## Phase 4: interpreter
- [x] runtime value model
- [x] environments and closures
- [ ] pattern matching execution
- [ ] module execution
- [x] error reporting
- [ ] REPL

## Phase 5: formatter
- [x] concrete syntax tree preservation strategy
- [x] formatter style guide
- [x] stable formatting of declarations
- [x] stable formatting of expressions
- [ ] comments preservation
- [x] idempotence tests

## Phase 6: compiler
- [ ] define HIR
- [ ] define MIR / typed IR
- [ ] ownership lowering strategy
- [ ] bytecode backend
- [ ] native backend feasibility study
- [ ] caching and incremental compilation

## Phase 7: tooling
- [ ] language server plan
- [ ] package manager plan
- [ ] doc generator plan
- [ ] test runner plan
- [ ] benchmark harness

## Phase 8: ecosystem
- [ ] stdlib design
- [ ] package manifest design
- [ ] versioning and compatibility policy
- [ ] unsafe / FFI policy
