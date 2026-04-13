# Aster Standard Library

The Aster standard library is a set of built-in modules available without any external dependencies.
Import any module with `use`:

```aster
use math
use list
use io
```

Use named imports to bring specific symbols into scope:

```aster
use math: sqrt, pi
use list: map, filter
```

Use an alias to avoid name clashes:

```aster
use str as strl   # avoids shadowing the str() builtin
```

---

## Built-in functions

These functions are available globally — no `use` statement required.

| Name | Signature | Description |
|------|-----------|-------------|
| `print` | `(value) -> Nil` | Print a value to stdout |
| `str` | `(value) -> String` | Convert any value to its string representation |
| `int` | `(value) -> Int` | Convert a value to Int (truncates floats) |
| `len` | `(value) -> Int` | Length of a String, List, Tuple, or Record |
| `abs` | `(n) -> Int\|Float` | Absolute value |
| `min` | `(a, b) -> Int\|Float` | Minimum of two values |
| `max` | `(a, b) -> Int\|Float` | Maximum of two values |
| `range` | `(end)` or `(start, end) -> List[Int]` | Integer range as a List |
| `ord` | `(ch: String) -> Int` | Unicode code point of a single character |
| `ascii_bytes` | `(s: String) -> List[Int]` | ASCII bytes of a string |
| `unicode_bytes` | `(s: String) -> List[Int]` | UTF-8 bytes of a string |
| `assert` | `(cond: Bool, msg?: String) -> Nil` | Raise if condition is false |
| `Nibble` | `(n: Int) -> Bits` | Cast to 4-bit unsigned integer |
| `Byte` | `(n: Int) -> Bits` | Cast to 8-bit unsigned integer |
| `Word` | `(n: Int) -> Bits` | Cast to 16-bit unsigned integer |
| `DWord` | `(n: Int) -> Bits` | Cast to 32-bit unsigned integer |
| `QWord` | `(n: Int) -> Bits` | Cast to 64-bit unsigned integer |

---

## Modules

| Module | Description |
|--------|-------------|
| [math](math.md) | Mathematical functions and constants |
| [str](str.md) | String inspection and manipulation |
| [std](std.md) | Program control, environment access, and utilities |
| [list](list.md) | Higher-order list operations |
| [io](io.md) | File and stream I/O |
| [random](random.md) | Pseudo-random number generation |
| [time](time.md) | Timestamps and timing |
| [linalg](linalg.md) | Vectors and matrices |
| [socket](socket.md) | Network sockets |
