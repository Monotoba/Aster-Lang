# Tutorial 22 — Standard Library: math, str, and list

This tutorial introduces the three most commonly used standard library modules.
No setup beyond a working Aster install is required — all three are native modules.

---

## Part 1: `math`

The `math` module provides numeric functions and constants.

```aster
use math

fn main():
    print(math.pi)              # 3.141592653589793
    print(math.sqrt(144))       # 12
    print(math.pow(2, 10))      # 1024
    print(math.log2(1024))      # 10.0
    print(math.clamp(150, 0, 100))  # 100
```

### Trigonometry (radians)

All trig functions take angles in **radians**. Convert from degrees with `angle * math.pi / 180`.

```aster
use math

fn deg_to_rad(deg: Float) -> Float:
    return deg * math.pi / 180

fn main():
    print(math.sin(math.pi / 2))   # 1.0
    print(math.cos(0))             # 1.0

    # Inverse trig: get angle from ratio
    angle := math.atan2(1, 1)      # π/4 ≈ 0.7854
    print(angle)
```

### GCD and integer ops

```aster
use math

fn main():
    print(math.gcd(48, 18))    # 6
    print(math.lcm(4, 6))      # 12
    print(math.sign(-42))      # -1
    print(math.sign(0))        # 0
```

### Checking special float values

```aster
use math

fn main():
    x := math.sqrt(-1)   # domain error — but we can guard:
    y := math.inf
    print(math.is_inf(y))       # true
    print(math.is_finite(y))    # false
    print(math.is_nan(math.nan))  # true
```

---

## Part 2: `str`

The `str` module contains string manipulation functions.

> **Name note:** `str` is both a module and a built-in conversion function.
> Use an alias when you need both: `use str as strl`.

```aster
use str as strl

fn main():
    s := "  Hello, World!  "
    print(strl.strip(s))          # "Hello, World!"
    print(strl.upper(s))          # "  HELLO, WORLD!  "
    print(strl.lower(s))          # "  hello, world!  "
    print(strl.reverse("abcde"))  # "edcba"
    print(strl.title("the quick brown fox"))  # "The Quick Brown Fox"
```

### Splitting and joining

```aster
use str as strl

fn main():
    csv := "alice,bob,carol,dave"
    names := strl.split(csv, ",")
    print(names[0])              # alice
    print(len(names))            # 4

    rejoined := strl.join(" | ", names)
    print(rejoined)              # alice | bob | carol | dave
```

### Searching

```aster
use str as strl

fn main():
    s := "the quick brown fox"
    print(strl.contains(s, "quick"))     # true
    print(strl.starts_with(s, "the"))    # true
    print(strl.find(s, "brown"))         # 10
    print(strl.count("banana", "an"))    # 2
```

### Parsing and formatting

```aster
use str as strl

fn main():
    n := strl.to_int("42")          # parse String → Int
    f := strl.to_float("3.14")      # parse String → Float
    print(n + 1)                    # 43

    msg := strl.format("name={} age={}", "Alice", 30)
    print(msg)                      # name=Alice age=30

    # Padding for aligned output
    print(strl.pad_left("7", 4, "0"))    # 0007
    print(strl.pad_right("ok", 6, "."))  # ok....
```

### Character inspection

```aster
use str as strl

fn main():
    print(strl.is_digit("123"))   # true
    print(strl.is_alpha("abc"))   # true
    print(strl.is_alnum("a1b2"))  # true
    print(strl.is_space("   "))   # true
    print(strl.is_empty(""))      # true

    chars := strl.chars("hello")  # ["h", "e", "l", "l", "o"]
    print(len(chars))              # 5
```

---

## Part 3: `list`

The `list` module provides higher-order list operations — functions that take other
functions as arguments.

> Lambda syntax recap: `fn(x) -> ReturnType: body_expression`

### map, filter, reduce

```aster
use list

fn main():
    nums := [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    # Double every element
    doubled := list.map(fn(x) -> Int: x * 2, nums)
    print(doubled)           # [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]

    # Keep only even numbers
    evens := list.filter(fn(x) -> Bool: x % 2 == 0, nums)
    print(evens)             # [2, 4, 6, 8, 10]

    # Sum all elements
    total := list.reduce(fn(acc, x) -> Int: acc + x, nums, 0)
    print(total)             # 55
```

### Sorting

```aster
use list

fn main():
    words := ["banana", "apple", "fig", "cherry"]
    print(list.sort(words))   # ["apple", "banana", "cherry", "fig"]

    # Sort by string length
    by_len := list.sort_by(fn(w) -> Int: len(w), words)
    print(by_len)             # ["fig", "apple", "banana", "cherry"]

    nums := [3, 1, 4, 1, 5, 9, 2, 6]
    print(list.sort(nums))    # [1, 1, 2, 3, 4, 5, 6, 9]
```

### any and all

```aster
use list

fn main():
    nums := [2, 4, 6, 7, 8]
    print(list.any(fn(x) -> Bool: x % 2 != 0, nums))  # true (7 is odd)
    print(list.all(fn(x) -> Bool: x > 0, nums))        # true (all positive)
    print(list.count(fn(x) -> Bool: x > 4, nums))      # 3 (6, 7, 8)
```

### Building and slicing

```aster
use list

fn main():
    # range: [start, end)
    print(list.range(5))          # [0, 1, 2, 3, 4]
    print(list.range(2, 7))       # [2, 3, 4, 5, 6]

    # take and drop
    print(list.take(3, [10, 20, 30, 40, 50]))   # [10, 20, 30]
    print(list.drop(2, [10, 20, 30, 40, 50]))   # [30, 40, 50]

    # flatten nested lists
    nested := [[1, 2], [3, 4], [5]]
    print(list.flatten(nested))    # [1, 2, 3, 4, 5]

    # zip pairs two lists
    zipped := list.zip([1, 2, 3], ["a", "b", "c"])
    # → [(1, "a"), (2, "b"), (3, "c")]
    print(zipped[0])

    # enumerate adds indices
    indexed := list.enumerate(["x", "y", "z"])
    # → [(0, "x"), (1, "y"), (2, "z")]
    e0 := indexed[0]
    print(e0)
```

### Aggregation

```aster
use list

fn main():
    print(list.sum([1, 2, 3, 4, 5]))        # 15
    print(list.product([1, 2, 3, 4, 5]))    # 120
    print(list.unique([1, 2, 1, 3, 2, 4]))  # [1, 2, 3, 4]

    words := ["apple", "banana", "kiwi"]
    print(list.head(words))                 # apple
    print(list.last(words))                 # kiwi
    tail := list.tail(words)               # ["banana", "kiwi"]
    print(len(tail))                        # 2
```

---

## Putting it together

A complete example combining all three modules:

```aster
use math
use str as strl
use list

fn word_stats(text: String):
    words := strl.split(text, " ")
    lengths := list.map(fn(w) -> Int: len(w), words)
    total := list.sum(lengths)
    n := len(words)
    avg := total / n
    longest := list.last(list.sort_by(fn(w) -> Int: len(w), words))

    print(strl.format("words:   {}", n))
    print(strl.format("avg len: {}", avg))
    print(strl.format("longest: {}", longest))

fn main():
    word_stats("the quick brown fox jumps over the lazy dog")
```

Expected output:
```
words:   9
avg len: 3
longest: jumps
```

---

**Next:** [Tutorial 23 — I/O and File Operations](23-io-files.md)
