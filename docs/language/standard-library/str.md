# `str` — String Manipulation

```aster
use str
use str as strl   # alias avoids shadowing the str() builtin
use str: split, join, upper
```

> **Name clash note:** `str` is both a built-in function (`str(value)`) and a module name.
> When you write `use str`, the module shadows the builtin within that scope.
> Use `use str as strl` (or any alias) to keep both available.

---

## Inspection

### `str.len(s) -> Int`
Character count (Unicode code points, not bytes).

```aster
str.len("hello")   # → 5
```

### `str.is_empty(s) -> Bool`
True if the string has zero characters.

### `str.is_digit(s) -> Bool`
True if every character is a decimal digit.

```aster
str.is_digit("123")   # → true
str.is_digit("12a")   # → false
```

### `str.is_alpha(s) -> Bool`
True if every character is an alphabetic letter.

### `str.is_alnum(s) -> Bool`
True if every character is alphanumeric.

### `str.is_space(s) -> Bool`
True if every character is whitespace.

---

## Transformation

### `str.upper(s) -> String`
Convert to uppercase.

### `str.lower(s) -> String`
Convert to lowercase.

### `str.title(s) -> String`
Capitalise the first letter of each word.

```aster
str.title("hello world")   # → "Hello World"
```

### `str.strip(s) -> String`
Remove leading and trailing whitespace.

### `str.lstrip(s, chars?) -> String`
Remove leading whitespace (no second argument) or remove any characters in `chars` from the left.

```aster
str.lstrip("  hello")        # → "hello"
str.lstrip("/a/b/", "/")     # → "a/b/"
```

### `str.rstrip(s, chars?) -> String`
Remove trailing whitespace (no second argument) or remove any characters in `chars` from the right.

```aster
str.rstrip("hello  ")        # → "hello"
str.rstrip("/a/b/", "/")     # → "/a/b"
```

### `str.reverse(s) -> String`
Reverse the characters of a string.

```aster
str.reverse("abcd")   # → "dcba"
```

### `str.repeat(s, n) -> String`
Repeat `s` exactly `n` times.

```aster
str.repeat("ab", 3)   # → "ababab"
```

### `str.replace(s, old, new) -> String`
Replace all occurrences of `old` with `new`.

### `str.pad_left(s, width, fill?) -> String`
Right-justify `s` in a field of `width` characters, padding on the left with `fill` (default `" "`).

```aster
str.pad_left("42", 5, "0")   # → "00042"
```

### `str.pad_right(s, width, fill?) -> String`
Left-justify `s`, padding on the right.

```aster
str.pad_right("hi", 5, ".")   # → "hi..."
```

---

## Splitting and joining

### `str.split(s, sep) -> List[String]`
Split `s` on the separator string.

```aster
str.split("a,b,c", ",")   # → ["a", "b", "c"]
```

### `str.join(sep, parts) -> String`
Join a list of strings with `sep` between each.

```aster
str.join("-", ["x", "y", "z"])   # → "x-y-z"
```

### `str.chars(s) -> List[String]`
Return a list of single-character strings.

```aster
str.chars("abc")   # → ["a", "b", "c"]
```

---

## Search

### `str.starts_with(s, prefix) -> Bool`
True if `s` begins with `prefix`.

### `str.ends_with(s, suffix) -> Bool`
True if `s` ends with `suffix`.

### `str.contains(s, sub) -> Bool`
True if `sub` appears anywhere in `s`.

### `str.find(s, sub) -> Int`
Index of the first occurrence of `sub`, or `-1` if not found.

### `str.count(s, sub) -> Int`
Count non-overlapping occurrences of `sub` in `s`.

```aster
str.count("banana", "an")   # → 2
```

---

## Indexing

### `str.char_at(s, i) -> String`
Return the single character at index `i` (zero-based). Raises on out-of-bounds.

### `str.slice(s, start, end) -> String`
Return the substring `s[start:end]` (end is exclusive).

```aster
str.slice("hello", 1, 4)   # → "ell"
```

---

## Parsing

### `str.to_int(s) -> Int`
Parse `s` as a decimal integer. Raises if the string is not a valid integer.

```aster
str.to_int("42")    # → 42
str.to_int("-7")    # → -7
```

### `str.to_float(s) -> Float`
Parse `s` as a floating-point number. Raises if the string is not valid.

```aster
str.to_float("3.14")   # → 3.14
```

---

## Formatting

### `str.format(template, arg...) -> String`
Replace each `{}` placeholder in `template` with the corresponding argument (converted via `str()`).
The number of `{}` tokens must exactly match the number of arguments.

```aster
str.format("hello {}", "world")           # → "hello world"
str.format("{} + {} = {}", 1, 2, 3)       # → "1 + 2 = 3"
str.format("score: {}", 99)               # → "score: 99"
```
