# Changelog

Notable changes to Aster are documented here.

## 0.1.3 Alpha — 2026-09-26

This alpha release presents the current interpreter and toolchain as an
experimental language implementation suitable for evaluation, learning, and
contribution. Syntax and semantics may change before 1.0.

### Highlights

- Interpreter, semantic analyzer, formatter, REPL, bytecode VM, Python
  transpiler, experimental native C backend, and language server.
- Indentation-sensitive syntax, structural pattern matching, modules,
  closures, traits, generics, and opt-in ownership diagnostics.
- Native and Aster-written standard-library modules for collections, strings,
  math, files, networking, HTTP, paths, time, randomness, and linear algebra.
- Package manifests, deterministic lockfiles, test and benchmark runners,
  documentation generation, and a VS Code extension.
- 23 tutorials, 13 progressive example programs, two EBNF grammars, and 1,097
  passing tests.

### Release maintenance

- Declared the language-server dependencies in the package's `lsp` and `dev`
  extras so clean development installations can run the complete test suite.
- Added CI, release, Python, license, and alpha-status badges.
- Improved package authorship, classifiers, project URLs, and search keywords.
- Modernized the SPDX license metadata while retaining GPL-2.0-only.
- Centralized CLI, package-manager, and language-server version reporting.
