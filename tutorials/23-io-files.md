# Tutorial 23 — I/O, Files, and the `std` / `time` / `random` Modules

This tutorial covers file operations with `io`, program utilities with `std`,
timing with `time`, and randomness with `random`.

---

## Part 1: `io` — File and Filesystem Operations

### Reading files

```aster
use io

fn main():
    # Read an entire file as a String
    content := io.read_file("config.txt")
    print(content)

    # Read line by line
    lines := io.read_lines("config.txt")
    print(str(len(lines)) + " lines")
    print(lines[0])   # first line
```

### Writing files

```aster
use io

fn main():
    # Overwrite (or create) a file
    io.write_file("output.txt", "Hello, file!\n")

    # Append to a file
    io.append_file("output.txt", "Second line\n")

    # Write a list of lines (newline added between each)
    io.write_lines("names.txt", ["Alice", "Bob", "Carol"])
```

### Checking paths

```aster
use io

fn main():
    if io.file_exists("data.csv"):
        if io.is_file("data.csv"):
            content := io.read_file("data.csv")
            print("loaded " + str(len(content)) + " bytes")
        else:
            io.print_err("data.csv is a directory, not a file")
    else:
        io.print_err("data.csv not found")
```

### Listing and walking directories

`list_dir` returns the immediate children of a directory:

```aster
use io

fn main():
    entries := io.list_dir(".")
    mut i := 0
    while i < len(entries):
        print(entries[i])
        i <- i + 1
```

`walk_dir` recursively walks a tree, returning a list of Records with fields
`path` (relative to root), `name` (filename), and `is_dir` (Bool):

```aster
use io
use list

fn main():
    all := io.walk_dir("src")

    # Print only files
    files := list.filter(fn(e) -> Bool: not e.is_dir, all)
    mut i := 0
    while i < len(files):
        print(files[i].path)
        i <- i + 1
```

### Creating directories

```aster
use io

fn main():
    io.mkdir("build/output/reports")   # creates intermediate dirs too
    io.write_file("build/output/reports/summary.txt", "done\n")
```

### Printing to stderr

```aster
use io

fn main():
    result := process()
    if result == nil:
        io.print_err("error: process returned nil")
```

---

## Part 2: `std` — Program Utilities

### Type reflection

```aster
use std

fn describe(x):
    t := std.type_of(x)
    print("value is a " + t)

fn main():
    describe(42)       # value is a Int
    describe("hello")  # value is a String
    describe([1, 2])   # value is a List
```

### Environment variables

```aster
use std

fn main():
    # env returns the value or nil if not set
    home := std.env("HOME")
    if home == nil:
        print("HOME not set")
    else:
        print("home: " + str(home))

    # env_or provides a fallback
    port := std.env_or("PORT", "8080")
    print("serving on port " + port)
```

### Command-line arguments

```aster
use std

fn main():
    argv := std.args()
    print("program: " + argv[0])
    if len(argv) > 1:
        print("first arg: " + argv[1])
    else:
        std.panic("usage: myprogram <input-file>")
```

### Assertions and guarded panics

```aster
use std

fn divide(a: Int, b: Int) -> Int:
    std.assert(b != 0, "division by zero")
    return a / b

fn main():
    print(divide(10, 2))   # 5
    print(divide(10, 0))   # raises: assert: division by zero
```

### Exit codes

```aster
use std
use io

fn main():
    if not io.file_exists("required.txt"):
        io.print_err("error: required.txt not found")
        std.exit(1)
    # ... continue normally
```

---

## Part 3: `time` — Timestamps and Timing

### Measuring elapsed time

```aster
use time
use list

fn main():
    start := time.monotonic()

    # Some work to measure
    nums := list.range(0, 1000000)
    total := list.sum(nums)

    elapsed := time.monotonic() - start
    print("sum: " + str(total))
    print("elapsed: " + str(elapsed) + "s")
```

### Timestamps and formatting

```aster
use time

fn main():
    # Unix timestamp (Float, seconds since 1970-01-01)
    ts := time.now()
    ms := time.now_ms()     # integer milliseconds

    # Format current local time
    print(time.strftime("%Y-%m-%d"))              # e.g. 2026-04-13
    print(time.strftime("%H:%M:%S"))              # e.g. 15:04:05
    print(time.strftime("%A, %B %d %Y"))          # e.g. Monday, April 13 2026
```

### Sleeping

```aster
use time
use io

fn main():
    io.print_err("starting...")
    time.sleep(1)          # pause 1 second
    io.print_err("done")

    time.sleep(0.25)       # 250 milliseconds
```

---

## Part 4: `random` — Randomness

### Basic random numbers

```aster
use random

fn main():
    # Seed for reproducibility (omit for truly random)
    random.seed(42)

    # Float in [0.0, 1.0)
    r := random.random()
    print(r)

    # Integer in [1, 6]
    die := random.rand_int(1, 6)
    print("rolled: " + str(die))

    # Float in [0.0, 100.0)
    pct := random.rand_float(0, 100)
    print("percent: " + str(pct))
```

### Working with lists

```aster
use random
use list

fn main():
    random.seed(1)

    colors := ["red", "green", "blue", "yellow"]

    # Pick one at random
    pick := random.choice(colors)
    print("chosen: " + pick)

    # Shuffle the list (returns new list, original unchanged)
    shuffled := random.shuffle(colors)
    print(shuffled)

    # Pick 2 without replacement
    sample := random.sample(colors, 2)
    print(sample)
```

### Simulating a coin flip

```aster
use random

fn coin_flip() -> String:
    if random.rand_int(0, 1) == 0:
        return "heads"
    return "tails"

fn main():
    random.seed(99)
    mut heads := 0
    mut tails := 0
    mut i := 0
    while i < 100:
        if coin_flip() == "heads":
            heads <- heads + 1
        else:
            tails <- tails + 1
        i <- i + 1
    print("heads: " + str(heads) + "  tails: " + str(tails))
```

---

## Putting it together — a file processing script

```aster
use io
use std
use str as strl
use list
use time

fn main():
    # Require an input directory from args
    argv := std.args()
    std.assert(len(argv) >= 2, "usage: script <directory>")
    dir := argv[1]

    std.assert(io.is_dir(dir), "not a directory: " + dir)

    start := time.monotonic()
    all := io.walk_dir(dir)

    # Collect .aster files only
    aster_files := list.filter(
        fn(e) -> Bool: not e.is_dir and strl.ends_with(e.name, ".aster"),
        all
    )

    print(strl.format("found {} .aster files in {}", len(aster_files), dir))
    print(time.strftime("scanned at %Y-%m-%d %H:%M:%S"))
    print(strl.format("scan took {}s", time.monotonic() - start))
```

---

**Previous:** [Tutorial 22 — math, str, and list](22-stdlib-math-str-list.md)
