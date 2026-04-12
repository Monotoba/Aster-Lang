# Aster Error Index

Every error the Aster toolchain can produce, grouped by component. Each entry
includes an ID, the message (variables shown in `<angle-brackets>`), what causes
it, an example, and how to fix it.

**Error ID prefix guide**

| Prefix | Component |
|--------|-----------|
| `PAR`  | Parser |
| `SEM`  | Semantic analyzer |
| `INT`  | Interpreter (runtime) |
| `VM`   | Bytecode VM backend |
| `MOD`  | Module resolution |
| `LCK`  | Lockfile |
| `CLI`  | Command-line interface |

---

## Parser Errors (PAR)

Parser errors occur while reading source text. They are always fatal — the file
cannot be compiled until they are fixed.

---

### PAR-001 — Expected declaration, got `<token>`

**Message:** `Expected declaration, got <TOKEN_KIND>`

**Cause:** A token appeared at module scope where only a declaration
(`fn`, `pub`, `typealias`, `use`, a binding, `trait`, `impl`, `effect`) is
valid.

**Example:**
```aster
x + 1   # expression at module level
```

**Fix:** Remove or wrap the statement. Module-level code must be inside a
function.

---

### PAR-002 — Expected `<token>`, got `<token>`

**Message:** `Expected <EXPECTED>, got <ACTUAL>`

**Cause:** A required syntactic token was missing. Common instances: missing
`:` after an `if` or `fn` header, missing `->` in a function signature, or an
unbalanced parenthesis/bracket.

**Example:**
```aster
fn add(a: Int, b: Int) Int:   # missing ->
    return a + b
```

**Fix:** Add the missing token the error message names.

---

### PAR-003 — Unexpected token in expression

**Message:** `Unexpected token in expression: <TOKEN_KIND>`

**Cause:** An expression was expected but a non-expression token was found.
Often a typo, stray keyword, or indentation problem.

**Example:**
```aster
fn main():
    x := fn   # fn is not an expression here
```

**Fix:** Check for typos or misplaced keywords in the expression.

---

### PAR-004 — Expected identifier

**Message:** `Expected identifier`

**Cause:** A name was required (e.g. after `fn`, `typealias`, `use`, or in a
`pub` declaration) but a non-identifier token appeared instead.

**Example:**
```aster
fn 42():   # 42 is not an identifier
    pass
```

**Fix:** Replace the non-identifier token with a valid name.

---

### PAR-005 — Expected pattern

**Message:** `Expected pattern, got <TOKEN_KIND>`

**Cause:** A `match` arm or destructuring binding expected a pattern but found
something that cannot start one.

**Example:**
```aster
match x:
    fn => pass   # fn is not a valid pattern
```

**Fix:** Use a valid pattern: a literal, identifier, tuple `(a, b)`, list
`[a, b]`, record `{ field }`, wildcard `_`, or or-pattern `a | b`.

---

### PAR-006 — impl blocks cannot be declared pub

**Message:** `impl blocks cannot be declared pub`

**Cause:** `pub impl` is not valid syntax. `impl` blocks are always implicitly
accessible via the type they implement.

**Example:**
```aster
pub impl MyTrait for MyType:
    fn method():
        pass
```

**Fix:** Remove the `pub` keyword before `impl`.

---

### PAR-007 — Trait methods are signatures only

**Message:** `Trait methods are signatures only (no body) in this prototype`

**Cause:** A method inside a `trait` block has a body (indented statements).
In the current prototype, trait methods are declarations only.

**Example:**
```aster
trait Greet:
    fn greet():
        print("hello")   # body not allowed
```

**Fix:** Remove the body and keep only the signature line.

---

### PAR-008 — Expected lambda parameter name

**Message:** `Expected lambda parameter name`

**Cause:** A `\` lambda expression was started but the parameter list contained
a non-identifier token.

**Fix:** Lambda parameters must be plain identifiers: `\x -> x + 1`.

---

## Semantic Errors (SEM)

Semantic errors are detected after parsing. They indicate type mismatches, scope
problems, and structural violations. The file is syntactically valid but cannot
be safely executed.

---

### SEM-001 — Undefined variable

**Message:** `Undefined variable '<name>'`

**Cause:** A name is used before it is declared, or it is out of scope.

**Example:**
```aster
fn main():
    print(x)   # x never declared
```

**Fix:** Declare the variable before using it, or check for typos.

---

### SEM-002 — Undefined function

**Message:** `Undefined function '<name>'`

**Cause:** A call to a function that has not been declared in scope and is not
a built-in.

**Example:**
```aster
fn main():
    frobnicate()   # not declared
```

**Fix:** Declare the function, import it from another module, or fix the name.

---

### SEM-003 — Function already defined

**Message:** `Function '<name>' is already defined`

**Cause:** Two top-level functions share the same name.

**Example:**
```aster
fn greet(): print("hi")
fn greet(): print("hello")   # duplicate
```

**Fix:** Rename one of the functions.

---

### SEM-004 — Variable already defined

**Message:** `Variable '<name>' is already defined`

**Cause:** A variable binding shadows another binding in the same scope.

**Example:**
```aster
fn main():
    x := 1
    x := 2   # redeclared in same scope
```

**Fix:** Use a different name, or use `<-` to mutate the existing binding
(requires `mut`).

---

### SEM-005 — Cannot assign to immutable variable

**Message:** `Cannot assign to immutable variable '<name>'`

**Cause:** An assignment (`<-`) targets a binding that was not declared `mut`.

**Example:**
```aster
fn main():
    x := 10
    x <- 20   # x is not mut
```

**Fix:** Declare the binding as `mut x := 10`.

---

### SEM-006 — Type mismatch on assignment

**Message:** `Type mismatch: cannot assign <ACTUAL> to <EXPECTED>`

**Cause:** The right-hand side of a `:=` or `<-` has a different type from the
declared or inferred type of the binding.

**Example:**
```aster
fn main():
    x: Int := "hello"   # String assigned to Int
```

**Fix:** Match the types, or remove the type annotation and let it be inferred.

---

### SEM-007 — If/While condition must be Bool

**Messages:**
- `If condition must be Bool, got <TYPE>`
- `While condition must be Bool, got <TYPE>`

**Cause:** The condition of an `if` or `while` statement evaluated to a
non-`Bool` type.

**Example:**
```aster
fn main():
    if 42:   # Int, not Bool
        print("yes")
```

**Fix:** Use a comparison expression: `if x > 0:`.

---

### SEM-008 — Arithmetic requires integer

**Message:** `Arithmetic requires an integer, got <TYPE>`

**Cause:** `+`, `-`, `*`, `/`, `%` were applied to a non-integer value (in
strict type-checking mode, or when types are known).

**Example:**
```aster
fn main():
    x: String := "a"
    y := x + 1   # String + Int
```

**Fix:** Use integers for arithmetic. For string concatenation use `+` with two
`String` values.

---

### SEM-009 — String concatenation requires String on both sides

**Messages:**
- `String + requires String, got <TYPE>` (left)
- `String + requires String, got <TYPE>` (right)

**Cause:** `+` was used with a `String` on one side and a non-`String` on the
other.

**Example:**
```aster
fn main():
    x := "hello" + 42   # Int on right
```

**Fix:** Convert the integer first: `"hello" + str(42)`.

---

### SEM-010 — Logical operator requires Bool

**Messages:**
- `Logical operator requires Bool, got <TYPE>` (left or right)

**Cause:** `and`/`or`/`not` applied to a non-`Bool` value.

**Example:**
```aster
fn main():
    x := 1 and 2   # Int, not Bool
```

**Fix:** Use a boolean expression: `x > 0 and y > 0`.

---

### SEM-011 — Function call arity mismatch

**Message:** `Function '<name>' expects <N> arguments, got <M>`

**Cause:** A function was called with the wrong number of arguments.

**Example:**
```aster
fn add(a: Int, b: Int) -> Int:
    return a + b

fn main():
    add(1)   # missing second argument
```

**Fix:** Pass the correct number of arguments.

---

### SEM-012 — Not a function

**Message:** `'<name>' is not a function`

**Cause:** A call expression targets a name that is a variable, not a function.

**Example:**
```aster
fn main():
    x := 5
    x()   # x is not callable
```

**Fix:** Call a function, not a variable.

---

### SEM-013 — Module has no public export

**Message:** `Module '<module>' has no public export '<name>'`

**Cause:** An imported module exists but does not export the requested name.
Either the name is private (missing `pub`) or misspelled.

**Example:**
```aster
use utils: secret_fn   # secret_fn is not pub in utils.aster
```

**Fix:** Add `pub` to the declaration in `utils.aster`, or import a name that
is actually exported.

---

### SEM-014 — Cyclic import

**Message:** `Cyclic import detected for module '<module>'`

**Cause:** Module A imports module B, and B (directly or transitively) imports
A.

**Fix:** Restructure modules to eliminate the cycle. Extract shared types or
utilities into a third module that neither imports the other.

---

### SEM-015 — Unknown effect

**Message:** `Unknown effect '<name>' — declare it with 'effect <name>'`

**Cause:** A function annotation references an effect that has not been
declared.

**Example:**
```aster
fn read_file() !IO -> String:   # IO not declared
    pass
```

**Fix:** Add `effect IO` at module scope, or remove the effect annotation.

---

### SEM-016 — Tuple/List/Record pattern arity or field mismatch

**Messages:**
- `Tuple pattern arity mismatch`
- `List pattern arity mismatch`
- `Record pattern field '<field>' not found`

**Cause:** A `match` pattern expects a different structure than what the value
provides.

**Example:**
```aster
match (1, 2):
    (a, b, c) => pass   # 3-tuple pattern, 2-tuple value
```

**Fix:** Match the pattern arity or field names to the actual value structure.

---

### SEM-017 — Or-pattern binding mismatch

**Message:** `Or-pattern alternatives must bind exactly the same names`

**Cause:** In an or-pattern like `Foo(x) | Bar(x)`, the two alternatives bind
different names.

**Example:**
```aster
match v:
    (a, _) | (_, b) => print(a)   # 'a' missing from second branch
```

**Fix:** Ensure every alternative in an or-pattern binds exactly the same set
of names.

---

### SEM-018 — Unknown trait

**Message:** `Unknown trait '<name>'`

**Cause:** A trait bound, `impl` declaration, or type constraint references a
trait that has not been declared.

**Fix:** Declare the trait with `trait <Name>:` or fix the spelling.

---

### SEM-019 — Missing trait implementation

**Message:** `impl is missing required method '<name>' for trait '<trait>'`

**Cause:** An `impl Trait for Type` block does not provide all methods required
by the trait.

**Fix:** Add the missing method to the `impl` block.

---

### SEM-020 — Unknown pointer kind

**Message:** `Unknown pointer kind '*<kind>'. Expected one of: own, shared, weak, raw.`

**Cause:** A pointer type expression uses an invalid ownership keyword.

**Example:**
```aster
x: *borrow T   # 'borrow' is not a valid pointer kind
```

**Fix:** Use one of `*own`, `*shared`, `*weak`, or `*raw`.

---

## Interpreter Errors (INT)

Runtime errors detected during interpretation. The program was valid at compile
time but encountered a problem while running.

---

### INT-001 — Undefined variable (runtime)

**Message:** `Undefined variable '<name>'`

**Cause:** A variable that was expected to be in scope at runtime was not found.
This can happen with module imports that failed silently at analysis, or in
closures capturing variables that no longer exist.

**Fix:** Ensure the variable is declared in the current scope.

---

### INT-002 — Cannot assign to immutable variable (runtime)

**Message:** `Cannot assign to immutable variable '<name>'`

**Cause:** An assignment was attempted on a binding that is not `mut` at
runtime. The semantic checker normally catches this, but it can slip through
in dynamic paths.

**Fix:** Declare the binding as `mut`.

---

### INT-003 — Division/modulo by zero

**Messages:**
- `Division by zero`
- `Modulo by zero`

**Cause:** The divisor or modulus evaluated to `0`.

**Example:**
```aster
fn main():
    x := 10 / 0
```

**Fix:** Guard the denominator: `if b != 0: result <- a / b`.

---

### INT-004 — Index out of bounds

**Messages:**
- `List index out of bounds: <idx>`
- `Tuple index out of bounds: <idx>`

**Cause:** An integer index is negative or >= the length of the collection.

**Example:**
```aster
fn main():
    xs := [1, 2, 3]
    print(xs[10])
```

**Fix:** Check `len(xs)` before indexing, or use a `match` on the list pattern.

---

### INT-005 — Record field not found (runtime)

**Messages:**
- `Record has no field '<name>'`
- `Missing record field '<name>'`

**Cause:** A field access or index on a record used a name that does not exist
in the record value.

**Example:**
```aster
fn main():
    r := { x: 1 }
    print(r.y)   # 'y' not in r
```

**Fix:** Use a field name that exists, or extend the record literal.

---

### INT-006 — Cannot index with type

**Message:** `Cannot index <COLLECTION_TYPE> with <INDEX_TYPE>`

**Cause:** A collection was indexed with an incompatible type (e.g. a list
indexed with a string).

**Example:**
```aster
fn main():
    xs := [1, 2, 3]
    print(xs["a"])   # string index on list
```

**Fix:** Use an `Int` for list/tuple access; use a `String` for record access.

---

### INT-007 — For loop requires iterable

**Message:** `For loop requires iterable, got <TYPE>`

**Cause:** The value after `in` in a `for` loop is not a list or tuple.

**Example:**
```aster
fn main():
    for x in 42:   # Int is not iterable
        print(x)
```

**Fix:** Use a list, tuple, or `range()` expression.

---

### INT-008 — Assertion failed

**Messages:**
- `assertion failed`
- `assertion failed: <message>`

**Cause:** An `assert(condition)` or `assert(condition, message)` call
evaluated to a falsy condition at runtime.

**Example:**
```aster
fn main():
    assert(1 == 2, "math is broken")
```

**Fix:** Fix the logic so the condition holds, or only call `assert` in test
functions where failure is the expected signal.

---

### INT-009 — Type conversion failure

**Messages:**
- `Cannot convert '<value>' to Int`
- `Cannot convert <TYPE> to Int`

**Cause:** `int()` was called on a string that is not a valid integer literal,
or on a type that cannot be converted.

**Example:**
```aster
fn main():
    x := int("abc")
```

**Fix:** Only call `int()` on strings that contain valid decimal integers, or
handle the error with a `match` on the string content.

---

### INT-010 — Cannot pass immutable reference as &mut

**Message:** `Cannot pass immutable reference where &mut is expected`

**Cause:** A function expecting a mutable borrow (`&mut T`) received an
immutable reference (`&T`).

**Fix:** Either pass a `&mut` reference from a `mut` binding, or change the
parameter type to `&T`.

---

### INT-011 — Module has no export (runtime)

**Messages:**
- `Module '<name>' has no public export '<name>'`
- `Module '<name>' has no export '<name>'`

**Cause:** A `use mod: name` import resolved at runtime but the requested name
was not exported.

**Fix:** Ensure the target declaration has `pub`, or import the module without
specifying names (`use mod`).

---

## VM Backend Errors (VM)

Errors from the experimental bytecode VM backend. These appear when using
`aster build --backend vm` or `aster vm`.

---

### VM-001 — Unsupported expression/statement

**Messages:**
- `Unsupported expression in VM backend: <TYPE>`
- `Unsupported statement in VM backend: <TYPE>`

**Cause:** The bytecode compiler encountered a construct it does not yet
implement. The interpreter backend supports more features than the VM at this
stage.

**Fix:** Use `aster run` (interpreter) instead, or avoid the unsupported
construct with the VM backend.

---

### VM-002 — Unsupported binary/unary operator

**Messages:**
- `Unsupported binary operator in VM backend: <op>`
- `Unsupported unary operator in VM backend: <op>`

**Cause:** An operator is not yet emitted by the bytecode compiler.

**Fix:** Use `aster run` until the operator is added to the VM backend.

---

### VM-003 — Duplicate definition

**Message:** `Duplicate definition '<name>' in VM backend`

**Cause:** Two top-level definitions share the same name in the compiled module.
The semantic analyzer should catch this first; this is a secondary guard.

**Fix:** Rename one of the declarations.

---

### VM-004 — VM backend does not support destructuring pattern

**Message:** `VM backend does not support destructuring pattern: <TYPE>`

**Cause:** A complex destructuring pattern (record, nested tuple, etc.) in a
`match` arm is not yet implemented in the VM codegen.

**Fix:** Use the interpreter backend, or restructure the match to use simpler
patterns.

---

## Module Resolution Errors (MOD)

---

### MOD-001 — Module not found

**Messages:**
- `Module not found: <module>`
- `Module not found: <module> (searched project root <path>)`
- `Module not found: <module> (searched dependency '<dep>' at <path>)`

**Cause:** A `use` declaration references a module that cannot be located under
any search root, project root, or declared dependency.

**Example:**
```aster
use utils   # utils.aster does not exist
```

**Fix:**
1. Check the module filename and spelling.
2. Ensure the file is in the project root or a configured search root.
3. Add the dependency to `aster.toml` if the module is in a separate package.

---

### MOD-002 — Cannot resolve module without base directory

**Message:** `Cannot resolve module '<module>' without a base directory`

**Cause:** Module resolution was attempted with no base directory context (rare;
usually a programmatic API usage issue).

**Fix:** Always run `aster run`/`aster check`/`aster build` with a file path;
relative imports need a base directory.

---

### MOD-003 — Dependency path not found

**Message:** `Dependency '<dep>' path not found: <path>`

**Cause:** A dependency declared in `aster.toml` or via `--dep` points to a
directory that does not exist.

**Fix:** Check the `path` value in `[dependencies]` or the `--dep` flag, and
ensure the directory exists.

---

### MOD-004 — Cannot import dependency package directly

**Message:** `Cannot import dependency package '<dep>' directly; specify a module within it`

**Cause:** `use lib` was written when `lib` is a package (directory with
multiple modules), not a single file.

**Fix:** Import a specific module: `use lib.utils` or `use lib.helpers`.

---

### MOD-005 — Invalid manifest

**Messages (various):**
- `Invalid manifest at <path>: <reason>`
- `Invalid manifest at <path>: [package] must be a table`
- `Invalid manifest at <path>: package.name must be a string`
- `Invalid manifest at <path>: modules.search_roots must be a list`
- `Invalid manifest at <path>: [dependencies] must be a table`
- `Invalid manifest at <path>: dependency '<dep>' is missing a 'path' key`

**Cause:** `aster.toml` exists but contains invalid TOML or a structural
problem.

**Fix:** Validate `aster.toml` against the expected schema:

```toml
[package]
name = "my_project"

[modules]
search_roots = ["src", "lib"]

[dependencies]
math = { path = "vendor/math" }
```

---

## Lockfile Errors (LCK)

---

### LCK-001 — Cannot read lockfile

**Message:** `Cannot read lockfile: <path>`

**Cause:** The lockfile path was provided but the file could not be opened
(permissions, missing file when `--lockfile` was specified explicitly).

**Fix:** Check the path passed to `--lockfile`, or regenerate with `aster lock`.

---

### LCK-002 — Invalid lockfile JSON

**Message:** `Invalid lockfile JSON: <path>`

**Cause:** The lockfile exists but is not valid JSON.

**Fix:** Delete the lockfile and regenerate with `aster lock`.

---

### LCK-003 — Unsupported lockfile version

**Message:** `Unsupported lockfile version: <version>`

**Cause:** The lockfile was written by a newer version of the toolchain.

**Fix:** Update the Aster toolchain, or regenerate the lockfile with `aster lock`.

---

### LCK-004 — Invalid lockfile structure

**Messages:**
- `Invalid lockfile: project_root must be a string`
- `Invalid lockfile: search_roots must be a list of strings`
- `Invalid lockfile: dependencies must be an object of string paths`

**Cause:** The lockfile JSON has the wrong structure — a field is the wrong
type.

**Fix:** Regenerate the lockfile with `aster lock`.

---

## CLI Errors (CLI)

---

### CLI-001 — Invalid --dep flag format

**Message:** `Invalid --dep value '<spec>': expected NAME=PATH`

**Cause:** A `--dep` argument was not in `NAME=PATH` format.

**Example:**
```
aster run --dep utils  # missing =PATH
```

**Fix:** Use `--dep utils=/path/to/utils`.

---

### CLI-002 — --lockfile cannot be combined with --dep or --search-root

**Message:** `--lockfile cannot be combined with --dep or --search-root`

**Cause:** Both a pinned lockfile and override flags were specified. The lockfile
pins all resolution; overrides are ignored when it is active.

**Fix:** Use either `--lockfile` (pinned, reproducible) or `--dep`/`--search-root`
(flexible), not both.

---

### CLI-003 — Build failed

**Message:** `Build failed: <errors>`

**Cause:** The backend compiler (Python transpiler, VM, or C) reported errors
during code generation.

**Fix:** Address the errors listed. Backend errors typically mean the source
is valid Aster but uses a construct not yet supported by the chosen backend.
Try `aster run` (interpreter) if the backend rejects the program.

---

## Quick Reference

| ID | Short description |
|----|-------------------|
| PAR-001 | Expression at module level |
| PAR-002 | Missing required token |
| PAR-003 | Unexpected token in expression |
| PAR-004 | Expected identifier |
| PAR-005 | Expected pattern |
| PAR-006 | `pub impl` is not valid |
| PAR-007 | Trait method has a body |
| PAR-008 | Bad lambda parameter |
| SEM-001 | Undefined variable |
| SEM-002 | Undefined function |
| SEM-003 | Duplicate function name |
| SEM-004 | Duplicate variable name |
| SEM-005 | Assign to immutable binding |
| SEM-006 | Type mismatch on assignment |
| SEM-007 | Non-Bool condition |
| SEM-008 | Arithmetic on non-integer |
| SEM-009 | String concat type mismatch |
| SEM-010 | Logical op on non-Bool |
| SEM-011 | Wrong argument count |
| SEM-012 | Not a function |
| SEM-013 | Module export not found |
| SEM-014 | Cyclic import |
| SEM-015 | Unknown effect |
| SEM-016 | Pattern arity/field mismatch |
| SEM-017 | Or-pattern binding mismatch |
| SEM-018 | Unknown trait |
| SEM-019 | Missing trait implementation |
| SEM-020 | Unknown pointer kind |
| INT-001 | Undefined variable (runtime) |
| INT-002 | Assign to immutable (runtime) |
| INT-003 | Division/modulo by zero |
| INT-004 | Index out of bounds |
| INT-005 | Record field not found |
| INT-006 | Wrong index type |
| INT-007 | For loop non-iterable |
| INT-008 | Assertion failed |
| INT-009 | Type conversion failure |
| INT-010 | Immutable ref passed as &mut |
| INT-011 | Module export missing (runtime) |
| VM-001 | Unsupported expression/statement |
| VM-002 | Unsupported operator |
| VM-003 | Duplicate VM definition |
| VM-004 | Unsupported destructuring in VM |
| MOD-001 | Module not found |
| MOD-002 | No base directory for resolution |
| MOD-003 | Dependency path not found |
| MOD-004 | Cannot import package directly |
| MOD-005 | Invalid aster.toml |
| LCK-001 | Cannot read lockfile |
| LCK-002 | Invalid lockfile JSON |
| LCK-003 | Unsupported lockfile version |
| LCK-004 | Invalid lockfile structure |
| CLI-001 | Invalid --dep format |
| CLI-002 | --lockfile conflicts with --dep |
| CLI-003 | Build failed |
