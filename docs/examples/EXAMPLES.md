# Aster Examples

## 1. Hello world

### Source
```aster
fn main():
    print("hello, world")
```

### Description
Prints a greeting.

### Input
None.

### Expected output
```txt
hello, world
```

## 2. Arithmetic function

### Source
```aster
fn add(a: Int, b: Int) -> Int:
    return a + b
```

### Description
Adds two integers and returns the result.

### Input
`a = 2`, `b = 3`

### Expected output
`5`

## 3. Mutable accumulation

### Source
```aster
fn sum_to(n: Int) -> Int:
    mut total := 0
    mut i := 1
    while i <= n:
        total <- total + i
        i <- i + 1
    return total
```

### Input
`n = 4`

### Expected output
`10`

## 4. Lambda

### Source
```aster
inc := x -> x + 1
```

### Description
Creates a function that increments its argument.

### Input
`x = 9`

### Expected output
`10`

## 5. Pattern match

### Source
```aster
fn classify(n: Int) -> String:
    match n:
        0: "zero"
        1: "one"
        _: "many"
```

### Input
`n = 2`

### Expected output
`many`

## 6. Record

### Source
```aster
point := {x: 4, y: 7}
```

### Description
Constructs a record value.

## 7. Module import

### Source
```aster
use helpers

fn main():
    print(helpers.double(21))
```

### Description
Loads a sibling module and calls a `pub` exported function through the module namespace.

### Expected output
`42`

## 8. Tuple pattern match

### Source
```aster
fn main():
    pair := (0, 7)
    match pair:
        (0, x):
            print(x)
        _:
            print(0)
```

### Description
Destructures a tuple in a `match` arm and binds the second element.

### Expected output
`7`

## 9. List pattern match

### Source
```aster
fn main():
    items := [0, 7]
    match items:
        [0, x]:
            print(x)
        _:
            print(0)
```

### Description
Destructures a fixed-length list in a `match` arm and binds the second element.

### Expected output
`7`

## 10. Record pattern match

### Source
```aster
fn main():
    point := {x: 0, y: 7}
    match point:
        {x: 0, y}:
            print(y)
        _:
            print(0)
```

### Description
Destructures a record in a `match` arm and binds a field using shorthand syntax.

### Expected output
`7`

## 11. Or-pattern match

### Source
```aster
fn main():
    n := 1
    match n:
        0 | 1:
            print(10)
        _:
            print(0)
```

### Description
Matches multiple literal alternatives in a single arm.

### Expected output
`10`

## 12. Rest pattern match

### Source
```aster
fn main():
    items := [1, 2, 3]
    match items:
        [head, *tail]:
            print(len(tail))
        _:
            print(0)
```

### Description
Matches a list with a head element and captures the remaining tail.

### Expected output
`2`

## 13. Parent Package Root Import

### Source
`app/main.aster`

```aster
use lib.helpers

fn main():
    print(helpers.answer())
```

`lib/helpers.aster`

```aster
pub fn answer() -> Int:
    return 42
```

### Description
Resolves a dotted module path by searching the current directory and then parent directories.

### Expected output
`42`

## 14. Manifest Module Root Import

### Source
`aster.toml`

```toml
[modules]
search_roots = ["src"]
```

`app/main.aster`

```aster
use helpers

fn main():
    print(helpers.answer())
```

`src/helpers.aster`

```aster
pub fn answer() -> Int:
    return 42
```

### Description
Resolves imports from explicit project-relative module roots declared in `aster.toml`.

### Expected output
`42`

## 15. Current Package Prefix Import

### Source
`aster.toml`

```toml
[package]
name = "app"

[modules]
search_roots = ["src"]
```

`app/main.aster`

```aster
use app.helpers

fn main():
    print(helpers.answer())
```

`src/helpers.aster`

```aster
pub fn answer() -> Int:
    return 42
```

### Description
Resolves an import through the current package name declared in `aster.toml`.

### Expected output
`42`

## 16. Local Destructuring Binding

### Source
```aster
fn main():
    [head, *tail] := [1, 2, 3]
    {x, y} := {x: head, y: len(tail)}
    print(x + y)
```

### Description
Uses list and record destructuring in local bindings outside `match`.

### Expected output
`3`

## 17. Borrowed reference sketch

### Source
```aster
fn first(xs: &List[Int]) -> &Int:
    ...
```

### Description
Demonstrates the intended syntax for shared borrowed references.

## 15. Owning pointer sketch

### Source
```aster
type Node = {
    value: Int,
    next: *own Node?
}
```

### Description
Demonstrates intended ownership-aware type syntax.
