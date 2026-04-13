# `std` — Standard Utilities

```aster
use std
use std: panic, type_of, env
```

The `std` module provides program-control functions, environment access, and runtime reflection.

---

## Runtime reflection

### `std.type_of(value) -> String`
Return the runtime type name of a value as a string.

| Value type | Returns |
|------------|---------|
| `Int` | `"Int"` |
| `Float` | `"Float"` |
| `String` | `"String"` |
| `Bool` | `"Bool"` |
| `Nil` | `"Nil"` |
| `List` | `"List"` |
| `Tuple` | `"Tuple"` |
| `Record` | `"Record"` |
| `Function` | `"Function"` |
| `Module` | `"Module"` |
| `Bits` | `"Bits"` |

```aster
use std

std.type_of(42)       # → "Int"
std.type_of("hi")     # → "String"
std.type_of([1, 2])   # → "List"
```

---

## Assertions and errors

### `std.assert(cond: Bool, msg?: String) -> Nil`
Raise an interpreter error if `cond` is `false`. An optional message is included in the error.

```aster
std.assert(x > 0, "x must be positive")
```

### `std.panic(msg: String) -> Nil`
Unconditionally abort with the given message. Useful for unreachable code paths.

```aster
std.panic("this branch should never be reached")
```

### `std.todo() -> Nil`
Mark a code path as not yet implemented. Raises immediately when reached.

```aster
fn my_fn():
    std.todo()
```

---

## Program control

### `std.exit(code?: Int) -> Nil`
Terminate the program with the given exit code (default `0`).

```aster
std.exit(1)   # exit with failure code
```

---

## Environment

### `std.env(key: String) -> String | Nil`
Return the value of the environment variable `key`, or `nil` if it is not set.

```aster
home := std.env("HOME")   # → "/home/user" or nil
```

### `std.env_or(key: String, default: String) -> String`
Return the environment variable `key`, falling back to `default` if it is not set.

```aster
port := std.env_or("PORT", "8080")
```

### `std.args() -> List[String]`
Return the command-line arguments (including the program name as `args()[0]`).

```aster
argv := std.args()
print(argv[0])   # program name
```

---

## I/O (basic)

### `std.input(prompt?: String) -> String`
Read a line from stdin. If `prompt` is provided it is printed before waiting.
Returns an empty string at EOF.

```aster
name := std.input("Enter your name: ")
print("Hello, " + name)
```
