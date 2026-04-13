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

In the build toolchain (`aster check` and `aster build`), unresolved `use` imports are treated as external Python imports (for example `use os`). Runtime interpretation (`aster run`) still requires Aster modules to exist. VM builds can select `--vm-artifact-format json|binary` to emit either JSON or compressed binary artifacts. The `c` backend is a placeholder in `aster build --backend c` until native codegen lands; it currently emits a stub `.c` file.

Use `aster backends` to list available build backends and their formats.

### Extern (FFI) declaration

Aster can call functions in shared C libraries at runtime through `extern` blocks backed by `ctypes`.

```aster
extern "libm":
    fn cos(x: Float) -> Float
    fn sin(x: Float) -> Float
    fn pow(base: Float, exp: Float) -> Float

fn main():
    print(cos(0))   # 1.0
```

Use `pub extern` to export the bound functions so other modules can import them:

```aster
# mymath.aster
pub extern "libm":
    fn sqrt(x: Float) -> Float

# main.aster
use mymath: sqrt
fn main():
    print(sqrt(4))  # 2.0
```

**Library resolution** (tried in order):
1. If the name starts with `/` or `./` it is treated as a direct file path.
2. `ctypes.util.find_library` with the stem (e.g. `"libm"` → looks for `"m"`).
3. Direct `ctypes.CDLL(name)` as a fallback.

A load failure raises a runtime error with `"FFI:"` in the message.

**Type mapping**:

| Aster  | C / ctypes     |
|--------|----------------|
| `Int`  | `c_int64`      |
| `Float`| `c_double`     |
| `String`| `c_char_p`   |
| `Bool` | `c_int`        |
| `Byte` | `c_uint8`      |
| `Word` | `c_uint16`     |
| `DWord`| `c_uint32`     |
| `QWord`| `c_uint64`     |
| absent / `Nil` | void  |

**Limitations**: Only scalar types are currently supported. Pointer and struct arguments are not yet mapped. The C transpiler backend does not yet consume `extern` declarations.

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

## Float type

`Float` represents a 64-bit IEEE 754 floating-point number. Float values are currently produced
only by native module functions (e.g. `math.sqrt`, `math.sin`). Float literals are not yet
supported in source code — use `math.pi`, `math.e`, or compute from an integer expression.

```aster
use math

fn main():
    x := math.sqrt(2)    # Float — approximately 1.4142135...
    y := math.floor(x)   # Int  — 1
    z := int(x)          # Int  — 1  (truncates toward zero)
    print(x)
    print(y)
```

`Float` participates in `str()` and `int()` conversions:

```aster
use math

fn main():
    f := math.pi
    print(str(f))    # "3.141592653589793"
    print(int(f))    # 3
```

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

## Standard library modules

Eight native modules are built in and available without any installation.
Import them with `use`:

```aster
use math
use str
use std
use list
use io
use random
use time
use linalg
```

Full documentation is in [`docs/language/standard-library/`](standard-library/README.md).

> **`String` vs `str`**: The Aster string *type* is always spelled `String` (capital S).
> `str` is the name of the string-manipulation *module* **and** a built-in
> *conversion function* (`str(x)` converts any value to a `String`). They are separate things.
> If you write `use str`, the module shadows the builtin in that scope; use
> `use str as strings` (or any alias) to keep both.

### math

Mathematical functions and constants. All functions accept `Int` or `Float` inputs.
See [`docs/language/standard-library/math.md`](standard-library/math.md) for the full reference.

**Constants**: `math.pi`, `math.e`, `math.tau`, `math.inf`, `math.nan`

**Functions (selected)**

| Function | Returns | Description |
|----------|---------|-------------|
| `math.abs(x)` | Int or Float | Absolute value |
| `math.floor(x)` | Int | Round toward −∞ |
| `math.ceil(x)` | Int | Round toward +∞ |
| `math.round(x)` | Int | Round to nearest integer |
| `math.sign(x)` | Int | `1`, `-1`, or `0` |
| `math.clamp(x, lo, hi)` | Int or Float | Clamp to `[lo, hi]` |
| `math.min(a, b)` / `math.max(a, b)` | Int or Float | Min / max of two values |
| `math.sqrt(x)` | Int or Float | Square root |
| `math.pow(base, exp)` | Int or Float | Exponentiation |
| `math.exp(x)` | Float | e^x |
| `math.log(x)` / `math.log2(x)` / `math.log10(x)` | Float | Logarithms |
| `math.sin(x)` / `math.cos(x)` / `math.tan(x)` | Float | Trig (radians) |
| `math.asin(x)` / `math.acos(x)` / `math.atan(x)` | Float | Inverse trig |
| `math.atan2(y, x)` | Float | Four-quadrant arc-tangent |
| `math.sinh(x)` / `math.cosh(x)` / `math.tanh(x)` | Float | Hyperbolic trig |
| `math.gcd(a, b)` / `math.lcm(a, b)` | Int | GCD / LCM |
| `math.is_nan(x)` / `math.is_inf(x)` / `math.is_finite(x)` | Bool | Float classification |

`sqrt`, `pow`, `min`, `max`, `clamp`, `abs`, and `sign` return `Int` when the result is a whole
number, `Float` otherwise. Trig, log, and exp functions always return `Float`.

```aster
use math

fn main():
    print(math.sqrt(16))       # 4
    print(math.sqrt(2))        # 1.4142135623730951
    print(math.clamp(15, 0, 10)) # 10
    print(math.sin(math.pi))   # 1.2246467991473532e-16  (≈ 0)
```

### str

String manipulation functions. All functions operate on `String` values.
Import as a namespace or with named imports:

```aster
use str                    # all functions via str.upper(s) etc.
use str as strl            # alias to avoid shadowing str() builtin
use str: upper, lower, split
```

> `use str` shadows the built-in `str()` conversion function in that scope.
> Use `use str as strl` (or any alias) to keep both available.

| Function | Returns | Description |
|----------|---------|-------------|
| `str.len(s)` | Int | Character count |
| `str.is_empty(s)` | Bool | True if zero characters |
| `str.is_digit(s)` / `str.is_alpha(s)` / `str.is_alnum(s)` / `str.is_space(s)` | Bool | Character class tests |
| `str.upper(s)` / `str.lower(s)` / `str.title(s)` | String | Case conversion |
| `str.strip(s)` / `str.lstrip(s)` / `str.rstrip(s)` | String | Whitespace trimming |
| `str.reverse(s)` | String | Reverse characters |
| `str.repeat(s, n)` | String | Repeat `n` times |
| `str.replace(s, old, new)` | String | Replace all occurrences |
| `str.pad_left(s, w, fill?)` / `str.pad_right(s, w, fill?)` | String | Width padding |
| `str.split(s, sep)` | List[String] | Split on separator |
| `str.join(sep, parts)` | String | Join list with separator |
| `str.chars(s)` | List[String] | List of characters |
| `str.starts_with(s, p)` / `str.ends_with(s, p)` / `str.contains(s, sub)` | Bool | Search |
| `str.find(s, sub)` | Int | First index of `sub`, or `-1` |
| `str.count(s, sub)` | Int | Count non-overlapping occurrences |
| `str.char_at(s, i)` | String | Character at index `i` |
| `str.slice(s, start, end)` | String | Substring `s[start:end]` |
| `str.to_int(s)` | Int | Parse as integer (raises on failure) |
| `str.to_float(s)` | Float | Parse as float (raises on failure) |
| `str.format(tmpl, args...)` | String | Replace `{}` placeholders in order |

```aster
use str as strl

fn main():
    words := strl.split("one,two,three", ",")
    print(strl.join(" / ", words))          # one / two / three
    print(strl.pad_left("42", 6, "0"))      # 000042
    print(strl.format("x={} y={}", 3, 7))  # x=3 y=7
    n := strl.to_int("99")
    print(n + 1)                            # 100
```

### std

General utilities: runtime reflection, program control, environment, and I/O.

| Function | Returns | Description |
|----------|---------|-------------|
| `std.type_of(x)` | String | Runtime type name: `"Int"`, `"Float"`, `"String"`, `"Bool"`, `"Nil"`, `"List"`, `"Tuple"`, `"Record"`, `"Function"` |
| `std.panic(msg)` | Nil | Raise a runtime error with `msg` |
| `std.assert(cond, msg?)` | Nil | Raise if `cond` is false |
| `std.todo()` | Nil | Raise "not yet implemented" |
| `std.input(prompt?)` | String | Read a line from stdin |
| `std.exit(code?)` | Nil | Terminate with exit code (default 0) |
| `std.env(key)` | String or Nil | Environment variable value, or `nil` |
| `std.env_or(key, default)` | String | Environment variable with fallback |
| `std.args()` | List[String] | Command-line arguments |

```aster
use std

fn main():
    print(std.type_of(42))       # Int
    print(std.type_of("hi"))     # String
    port := std.env_or("PORT", "8080")
    print("listening on " + port)
```

### linalg

Linear algebra: vectors and matrices. Vectors are plain `List[Float/Int]`; matrices are
`List[List[Float/Int]]` in row-major order. Import with `use linalg`.

#### Vectors

| Function | Returns | Description |
|----------|---------|-------------|
| `linalg.vec(x, y, ...)` | List | Construct a vector from scalar components |
| `linalg.vdim(v)` | Int | Number of components |
| `linalg.vadd(a, b)` | List | Element-wise addition |
| `linalg.vsub(a, b)` | List | Element-wise subtraction |
| `linalg.vmul(a, b)` | List | Element-wise (Hadamard) product |
| `linalg.vscale(v, s)` | List | Multiply each component by scalar `s` |
| `linalg.vneg(v)` | List | Negate all components |
| `linalg.vdot(a, b)` | Int or Float | Dot product |
| `linalg.vcross(a, b)` | List | Cross product (3D vectors only) |
| `linalg.vlen(v)` | Float | Euclidean length (magnitude) |
| `linalg.vlen_sq(v)` | Int or Float | Squared length |
| `linalg.vnorm(v)` | List | Unit vector in same direction (raises on zero-length) |
| `linalg.vlerp(a, b, t)` | List | Linear interpolation: `a + t*(b-a)` |

#### Matrices

| Function | Returns | Description |
|----------|---------|-------------|
| `linalg.mat(row0, row1, ...)` | List[List] | Construct from row vectors (each a `List`) |
| `linalg.identity(n)` | List[List] | n×n identity matrix |
| `linalg.mrows(m)` | Int | Number of rows |
| `linalg.mcols(m)` | Int | Number of columns |
| `linalg.mget(m, i, j)` | Int or Float | Element at row `i`, column `j` |
| `linalg.mrow(m, i)` | List | Row vector `i` |
| `linalg.mcol(m, j)` | List | Column vector `j` |
| `linalg.madd(a, b)` | List[List] | Element-wise addition |
| `linalg.msub(a, b)` | List[List] | Element-wise subtraction |
| `linalg.mscale(m, s)` | List[List] | Multiply every element by scalar `s` |
| `linalg.mmul(a, b)` | List[List] | Matrix product |
| `linalg.mvmul(m, v)` | List | Matrix × column vector |
| `linalg.mtranspose(m)` | List[List] | Transpose |
| `linalg.mdet(m)` | Int or Float | Determinant (square matrices only) |
| `linalg.minv(m)` | List[List] | Inverse (raises if singular) |

```aster
use linalg

fn main():
    # Vector example
    a := linalg.vec(3, 4)
    print(linalg.vlen(a))          # 5
    b := linalg.vnorm(a)
    print(linalg.vlen(b))          # 1.0

    # Matrix example
    m := linalg.mat([2, 0], [0, 3])
    v := linalg.vec(5, 7)
    r := linalg.mvmul(m, v)
    print(r[0])                    # 10
    print(r[1])                    # 21

    print(linalg.mdet(m))          # 6
```

### list

Higher-order list utilities. See [`docs/language/standard-library/list.md`](standard-library/list.md).

Key functions: `map`, `filter`, `reduce`, `any`, `all`, `sort`, `sort_by`, `sum`, `product`,
`head`, `tail`, `last`, `take`, `drop`, `reverse`, `flatten`, `zip`, `enumerate`, `unique`,
`contains`, `append`, `prepend`, `concat`, `range`, `repeat`, `len`.

```aster
use list

fn main():
    nums := list.range(1, 6)                            # [1, 2, 3, 4, 5]
    evens := list.filter(fn(x) -> Bool: x % 2 == 0, nums)
    doubled := list.map(fn(x) -> Int: x * 2, evens)
    print(list.sum(doubled))                            # 12
    print(list.sort([3, 1, 4, 1, 5, 9]))               # [1, 1, 3, 4, 5, 9]
```

### io

File and stream I/O. See [`docs/language/standard-library/io.md`](standard-library/io.md).

Key functions: `read_file`, `write_file`, `append_file`, `read_lines`, `write_lines`,
`file_exists`, `is_file`, `is_dir`, `list_dir`, `walk_dir`, `mkdir`, `delete_file`, `print_err`.

```aster
use io

fn main():
    if io.file_exists("config.txt"):
        content := io.read_file("config.txt")
        print(content)
    else:
        io.write_file("config.txt", "# defaults\n")
```

### random

Pseudo-random number generation. See [`docs/language/standard-library/random.md`](standard-library/random.md).

Key functions: `random`, `rand_int`, `rand_float`, `choice`, `shuffle`, `sample`, `seed`.

```aster
use random

fn main():
    random.seed(42)
    print(random.rand_int(1, 6))          # simulated die roll
    suits := ["hearts", "diamonds", "clubs", "spades"]
    print(random.choice(suits))
```

### time

Timestamps and timing. See [`docs/language/standard-library/time.md`](standard-library/time.md).

Key functions: `now`, `now_ms`, `monotonic`, `sleep`, `strftime`, `clock`.

```aster
use time

fn main():
    start := time.monotonic()
    # ... work ...
    elapsed := time.monotonic() - start
    print("done in " + str(elapsed) + "s")
    print(time.strftime("%Y-%m-%d %H:%M:%S"))
```
