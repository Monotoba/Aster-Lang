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

## Data forms

### List
```aster
nums := [1, 2, 3]
```

### Record
```aster
point := {x: 10, y: 20}
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
    0: "zero"
    1: "one"
    _: "many"
```

## Ownership and references

### Shared reference
```aster
fn head(xs: &List[Int]) -> &Int:
    ...
```

### Mutable reference
```aster
fn bump(x: &mut Int):
    *x <- *x + 1
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
