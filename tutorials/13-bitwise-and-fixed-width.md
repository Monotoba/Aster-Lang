# 13. Bitwise Operators and Fixed-Width Integers

Goal: use `& | ^ ~ << >>` and learn `Nibble`/`Byte`/`Word`/`DWord`/`QWord`.

## Bitwise operators

```aster
fn main():
    x := 10
    y := 12
    print(x & y)   # 8
    print(x | y)   # 14
    print(x ^ y)   # 6
    print(~x)      # -11 (two's complement style on unbounded Int)
    print(x << 1)  # 20
    print(y >> 2)  # 3
```

## Fixed-width unsigned integers

Types:

- `Nibble` (4-bit)
- `Byte` (8-bit)
- `Word` (16-bit)
- `DWord` (32-bit)
- `QWord` (64-bit)

### Typed bindings (fit required)

```aster
fn main():
    b: Byte := 200
    print(b)
```

If you try `b: Byte := 300`, the interpreter errors and tells you to wrap explicitly.

### Cast builtins (wrap modulo 2^N)

```aster
fn main():
    b := byte(300)  # 44
    print(b)
```

Cast functions:

- `nibble(x)`, `byte(x)`, `word(x)`, `dword(x)`, `qword(x)`

## Exercises

1. Pack two nibbles into a byte: `byte((hi << 4) | lo)`.
2. Compute XOR checksum of `range(256)`.

