# User Guide

## CLI commands

```bash
aster run file.aster              # run a program (default: interpreter backend)
aster run --backend vm file.aster # run via experimental bytecode VM
aster check file.aster            # parse and semantically analyse only
aster fmt file.aster              # reformat source in canonical style
aster build file.aster            # compile to a runnable artifact
aster ast file.aster              # print the parse tree (debug)
aster hir file.aster              # print the typed HIR (debug)
aster repl                        # start the interactive REPL
aster vm file.aster               # run directly via the experimental VM
aster backends                    # list available build backends and formats
aster test [path]                 # discover and run test_*.aster files
aster bench [path]                # discover and run bench_*.aster files
aster doc [path]                  # generate Markdown docs from ## comments
aster lock                        # write aster.lock for reproducible builds
aster pkg init                    # create a new package (aster.toml)
aster pkg check                   # validate aster.toml
aster pkg build                   # build a .apkg package artifact
aster pkg list                    # list declared dependencies
aster version                     # show version string
```

### Key flags

| Command | Flag | Description |
|---------|------|-------------|
| `run` / `build` | `--backend interpreter\|vm\|python\|c` | Select backend |
| `run` / `build` | `--dep NAME=PATH` | Override or declare a dependency (repeatable) |
| `run` / `build` | `--search-root PATH` | Prepend an extra module search root (repeatable) |
| `check` / `build` | `--ownership off\|warn\|deny` | Ownership-checking mode |
| `build` | `--out-dir DIR` | Output directory (default: `./__aster_build__`) |
| `build` | `--cache` | Enable incremental build cache |
| `build` | `--vm-artifact-format json\|binary` | VM artifact encoding |
| `test` / `bench` | `--dep NAME=PATH` | Dependency override (repeatable) |
| `bench` | `--iters N` | Number of timed iterations per benchmark (default: 100) |
| `doc` | `--out-dir DIR` | Output directory for generated `.md` files |
| `lock` | `--lockfile PATH` | Lockfile output path |

---

## Learning flow

**Beginners:** use `aster repl`, `aster run`, or `aster vm` to learn the language interactively.

**Advanced:** use `aster build --backend python|vm` to produce runnable artifacts.

---

## Testing and benchmarking

### `aster test`

Discovers `test_*.aster` files under the given path (default: `tests/` subdirectory).
Runs every `fn test_*()` (no-argument) function.  Functions that return normally pass;
functions that call `assert(false)` or raise an error fail.

```aster
# tests/test_math.aster
fn test_addition():
    assert(1 + 1 == 2)

fn test_zero():
    assert(0 == 0, "zero should equal zero")
```

```bash
aster test              # search tests/ in current directory
aster test path/to/dir  # explicit search root
aster test myfile.aster # run a single file
```

### `aster bench`

Discovers `bench_*.aster` files under the given path (default: `benches/` subdirectory).
Runs every `fn bench_*()` (no-argument) function `N` times and reports mean/min/max timing.

```aster
# benches/bench_sum.aster
fn bench_sum_to_1000():
    mut total := 0
    mut i := 0
    while i < 1000:
        total <- total + i
        i <- i + 1
```

```bash
aster bench                # search benches/ in current directory
aster bench --iters 500    # run each benchmark 500 times
aster bench myfile.aster   # run a single file
```

---

## Documentation generation

`aster doc` reads `##` doc comments from `pub` declarations and emits Markdown.

```aster
## Compute the factorial of n.
pub fn factorial(n: Int) -> Int:
    ...
```

```bash
aster doc src/           # generate docs for all .aster files under src/
aster doc --out-dir docs/ src/
```

---

## Project layout

A typical project with `aster.toml`:

```
myproject/
  aster.toml
  src/
    main.aster
    helpers.aster
  tests/
    test_helpers.aster
  benches/
    bench_helpers.aster
```

`aster.toml` (minimal):

```toml
[package]
name = "myproject"
version = "0.1.0"

[modules]
search_roots = ["src"]
```
