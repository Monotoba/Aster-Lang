# BACKLOG

## Phase 1: repository and architecture
- [x] bootstrap repository layout
- [x] create language and toolchain design docs
- [x] create grammar files
- [x] create scaffold package
- [x] create tests and CI
- [x] refine package boundaries after first parser milestone (flat structure is clean; no sub-packages needed at current scale)
- [x] docs: clarify binding syntax (`:=` / `mut`) vs. internal `Let*` AST naming (no `let` keyword)

## Phase 2: lexer and parser
- [x] implement token model
- [x] implement indentation-aware lexer
- [x] add lexer golden tests
- [x] implement parser for declarations
- [x] implement Pratt parser for expressions
- [x] implement pattern parser (for match expressions)
- [x] extend local binding syntax with tuple/list/record destructuring
- [x] add parse tree round-trip debug printer

## Phase 3: semantic model
- [x] symbol tables
- [x] module loader
- [x] type expression resolver
- [x] basic export visibility (`pub`) for imports
- [x] parent package-root lookup for imports
- [x] manifest-configured module search roots
- [x] manifest package identity for current-package imports
- [x] semantic validation for local destructuring bindings
- [x] ownership / borrow checking prototype (move semantics, borrow rules, use-after-move enforcement)
- [x] trait resolution prototype (impl validation, call-site method resolution, Self type)
- [x] effect tracking prototype

## Phase 4: interpreter
- [x] runtime value model
- [x] environments and closures
- [x] pattern matching execution
- [x] destructuring binding execution
- [x] module execution
- [x] error reporting
- [x] REPL

## Phase 5: formatter
- [x] concrete syntax tree preservation strategy
- [x] formatter style guide
- [x] stable formatting of declarations
- [x] stable formatting of expressions
- [x] stable formatting of destructuring bindings
- [x] comments preservation
- [x] idempotence tests

## Phase 6: compiler
- [x] define HIR
- [x] define MIR / typed IR
- [x] ownership lowering strategy
- [x] standard backend interface layer (shared IR + adapter boundary)
- [x] compile record destructuring bindings
- [x] experimental bytecode VM backend (subset)
- [x] expand VM backend coverage (runtime parity test gap closed; artifact compression/binary polish deferred)
- [x] VM artifact compression/binary encoding (optional binary artifacts)
- [x] native backend feasibility study (C target chosen; spike scope, ABI, and runtime stub sketched in docs/toolchain/NATIVE-BACKEND.md and COMPILER.md)
- [x] C backend: implement AsterValue runtime header (Int/Bool/Nil/String tagged union, aster_print, aster_add_int, aster_eq_int)
- [x] C backend: MIR → C codegen (functions, locals, arithmetic, if/while, calls)
- [x] C backend: cc build harness in CBackendAdapter (compile emitted .c, run main)
- [x] C backend: end-to-end spike test (integer arithmetic, if/else, while, function call)
- [x] caching and incremental compilation

## Phase 7: tooling
- [ ] language server plan
- [ ] package manager plan
- [x] doc generator (`aster doc`) — extracts `##` doc comments from pub declarations, emits Markdown
- [x] test runner (`aster test`) — discovers `test_*.aster`, runs `fn test_*()`, reports pass/fail
- [x] error index — `docs/ERROR-INDEX.md`, 55 error IDs across all pipeline components
- [ ] benchmark harness

## Phase 8: ecosystem
- [ ] stdlib design
- [ ] richer package manifest design
- [ ] dependency mapping and package resolution
- [x] versioning and compatibility policy
- [ ] unsafe / FFI policy
