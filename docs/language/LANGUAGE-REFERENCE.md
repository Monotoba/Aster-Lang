# Aster Language Reference

This document is the primary language reference for the design phase.

## Lexical model

- UTF-8 source
- indentation-sensitive blocks
- spaces only for indentation
- comments with `#`
- explicit block introducer `:`

## Declarations

### Function declaration
```aster
fn add(a: Int, b: Int) -> Int:
    return a + b
```

### Inferred binding
```aster
x := 10
```

### Mutable binding
```aster
mut total := 0
```

### Mutation
```aster
total <- total + 1
```

### Type alias
```aster
typealias UserId = Int
```

### Import
```aster
use math_utils
use math_utils as math
use math_utils: add, sub
```

Imported names come from `pub` top-level declarations. Private declarations stay available inside their defining module but are not exported.
Module resolution starts from the importing file's directory. If no manifest is present, the resolver can search parent directories for dotted module paths such as `use lib.helpers`.

If an ancestor directory contains `aster.toml`, that directory becomes the explicit project root. The resolver searches the project root plus any additional relative search roots declared under `[modules].search_roots`.

```toml
[package]
name = "app"

[modules]
search_roots = ["src", "vendor"]
```

With that manifest, `use helpers` can resolve `src/helpers.aster` and `vendor/helpers.aster` relative to the project root.
If `package.name` is set, imports may also use the current package prefix explicitly, for example `use app.helpers`.

In the build toolchain (`aster check` and `aster build`), unresolved `use` imports are treated as external Python imports (for example `use os`). Runtime interpretation (`aster run`) still requires Aster modules to exist.

### Public declaration
```aster
pub fn add(a: Int, b: Int) -> Int:
    return a + b

pub answer := 42
```

## Data forms

### List
```aster
nums := [1, 2, 3]
```

### Record
```aster
point := {x: 10, y: 20}
print(point.x)
print(point["x"])
```

### Tuple
```aster
pair := (1, "one")
```

## Functions and lambdas

### Single-expression lambda
```aster
inc := x -> x + 1
```

### Typed lambda
```aster
combine := (a: Int, b: Int) -> a + b
```

### Block lambda
```aster
inc := (x: Int) -> :
    return x + 1
```

Lambdas are closures: they can reference names from outer scopes. Captures are by reference, so updates
to a captured `mut` binding are visible when the lambda is called.

## Control flow

### If
```aster
if n > 0:
    print("positive")
else:
    print("non-positive")
```

### While
```aster
while x < 10:
    x <- x + 1
```

### For
```aster
for item in items:
    print(item)
```

## Pattern matching

```aster
match value:
    0:
        print("zero")
    1 | 2:
        print("small")
    (1, x):
        print(x)
    [2, y]:
        print(y)
    {x: 3, y}:
        print(y)
    1:
        print("one")
    _:
        print("many")
```

Or-patterns are supported, including binding or-patterns as long as all alternatives bind the same names consistently.

Trailing rest patterns are also supported for tuples and lists, for example `[head, *tail]` and `(head, *tail)`.

The same tuple, list, and record destructuring forms are also available in local bindings:

```aster
(x, y) := pair
[head, *tail] := items
{x, y} := point
```

Current limitation: destructuring binding type annotations are not supported. `mut (x, y): Pair := pair` is rejected semantically.

## Fixed-width integers and bitwise operators

Aster has `Int` plus a set of fixed-width **unsigned** integer types:

- `Nibble` (4-bit, 0..15)
- `Byte` (8-bit, 0..255)
- `Word` (16-bit, 0..65535)
- `DWord` (32-bit)
- `QWord` (64-bit)

You can get fixed-width values either by annotating a binding:

```aster
fn main():
    b: Byte := 200
    print(b)
```

If the value does not fit the range, the interpreter raises an error and suggests using an explicit cast.

Or by calling cast builtins, which **wrap** modulo `2^N`:

```aster
fn main():
    b := byte(300)  # 300 mod 256 = 44
    print(b)
```

Bitwise operators:

```aster
fn main():
    x := 10
    y := 12
    print(x & y)
    print(x | y)
    print(x ^ y)
    print(~x)
    print(x << 1)
    print(y >> 2)
```

Supported operators (on integers): `&`, `|`, `^`, `~`, `<<`, `>>`.

## String and bytes helpers

- `ord(s)` expects a single-character `String` and returns its codepoint as `Int`.
- `ascii_bytes(s)` returns a list of `Byte` values (ASCII only); non-ASCII codepoints raise an error.
- `unicode_bytes(s)` returns a list of `Byte` values (UTF-8 encoding).

## Ownership and references

### Shared reference
```aster
fn head(xs: &List[Int]) -> &Int:
    ...
```

### Mutable reference
```aster
fn bump(x: &mut Int):
    # `&mut` parameters can mutate the caller's variable.
    x <- x + 1

fn main():
    mut n := 1
    bump(n)       # implicit borrow at call sites
    bump(&mut n)  # explicit borrow is also allowed
    print(n)      # 3
```

### Owning pointer
```aster
node: *own Node
```

### Shared smart pointer
```aster
graph: *shared Graph
```

### Weak pointer
```aster
parent: *weak Node
```

### Raw pointer
```aster
buffer: *raw Byte
```

Ownership and pointer types are parsed and formatted in type annotations. Ownership/borrow checking is
**opt-in** and still experimental:

```bash
uv run aster check file.aster --ownership off   # default: no ownership diagnostics
uv run aster check file.aster --ownership warn  # warnings for ownership/borrow issues
uv run aster check file.aster --ownership deny  # errors for ownership/borrow issues
```

Expression-level borrowing and dereference are supported:
- borrow expressions: `&x`, `&mut x`, including computed postfix roots such as `&mut {x: 1}.x` and `&mut make_list()[0]`
- dereference: `*p`

Borrow targets currently support identifier, member, and index lvalues, including nested and
computed postfix roots:
`&mut r.x`, `&mut xs[0]`, `&mut r.inner.x`, `&mut {x: 1}.x`, `&mut make_list()[0]`.

Assignment targets support the same member/index surface, so expressions like `r.inner.x <- 7`
and `[1, 2][0] <- 9` are valid and operate on the selected lvalue.

Type checking strictness is also opt-in:

```bash
uv run aster check file.aster --types loose   # default: permissive typing for prototyping
uv run aster check file.aster --types strict  # reject unknown-typed arithmetic/bitwise uses
```

## Effects and async

```aster
fn read_text(path: String) -> Result[String, IoError] !io
fn fetch(url: String) -> Response !io async
```

## Traits and impls

```aster
trait Show:
    fn show(self) -> String

impl Int:
    fn show(self) -> String:
        return "Int(...)"
```

Current status: traits and impl blocks are parsed and formatted. Semantic analysis performs a small
prototype check for `impl Trait for Type` blocks (required method presence and basic signature shape),
but there is no dynamic dispatch or full trait resolution yet.
