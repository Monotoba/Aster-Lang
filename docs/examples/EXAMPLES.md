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

## 7. Borrowed reference sketch

### Source
```aster
fn first(xs: &List[Int]) -> &Int:
    ...
```

### Description
Demonstrates the intended syntax for shared borrowed references.

## 8. Owning pointer sketch

### Source
```aster
type Node = {
    value: Int,
    next: *own Node?
}
```

### Description
Demonstrates intended ownership-aware type syntax.
