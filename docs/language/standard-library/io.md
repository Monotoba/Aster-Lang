# `io` — File and Stream I/O

```aster
use io
use io: read_file, write_file, file_exists
```

The `io` module provides functions for reading and writing files, querying the filesystem,
and writing to stderr. All file paths are relative to the current working directory unless
an absolute path is given.

All functions raise an interpreter error on I/O failure (e.g. permission denied, file not found).

---

## Reading files

### `io.read_file(path: String) -> String`
Read an entire file as a UTF-8 string.

```aster
use io

src := io.read_file("config.txt")
print(src)
```

### `io.read_lines(path: String) -> List[String]`
Read a file and return a list of lines (newlines stripped).

```aster
lines := io.read_lines("data.csv")
print(len(lines))
```

---

## Writing files

### `io.write_file(path: String, content: String) -> Nil`
Write `content` to `path`, replacing any existing content.

```aster
io.write_file("output.txt", "hello, world\n")
```

### `io.append_file(path: String, content: String) -> Nil`
Append `content` to `path`. Creates the file if it does not exist.

```aster
io.append_file("log.txt", "line added\n")
```

### `io.write_lines(path: String, lines: List[String]) -> Nil`
Write a list of strings to `path`, joining them with newlines.
A trailing newline is always added.

```aster
io.write_lines("names.txt", ["Alice", "Bob", "Carol"])
```

---

## Filesystem queries

### `io.file_exists(path: String) -> Bool`
True if `path` exists (file or directory).

### `io.is_file(path: String) -> Bool`
True if `path` exists and is a regular file.

### `io.is_dir(path: String) -> Bool`
True if `path` exists and is a directory.

```aster
if io.is_file("config.toml"):
    cfg := io.read_file("config.toml")
```

### `io.list_dir(path: String) -> List[String]`
Return the names (not full paths) of entries in a directory, sorted alphabetically.

```aster
entries := io.list_dir(".")
print(entries)
```

### `io.walk_dir(root: String) -> List[Record]`
Recursively walk the directory tree rooted at `root`.
Returns one Record per entry (both files and directories), sorted by path.
Each Record has three fields:

| Field | Type | Description |
|-------|------|-------------|
| `path` | String | Path relative to `root`, using `/` separators |
| `name` | String | Filename component only |
| `is_dir` | Bool | True if the entry is a directory |

```aster
use io

fn main():
    entries := io.walk_dir("src")
    mut i := 0
    while i < len(entries):
        e := entries[i]
        prefix := if e.is_dir: "[dir] " else: "      "
        print(prefix + e.path)
        i <- i + 1
```

To list only files, filter by `is_dir`:

```aster
use io
use list

fn main():
    all := io.walk_dir(".")
    files := list.filter(fn(e) -> Bool: not e.is_dir, all)
    print(str(list.len(files)) + " files found")
```

---

## Filesystem mutations

### `io.delete_file(path: String) -> Nil`
Delete a file. Raises if the path does not exist or is a directory.

### `io.mkdir(path: String) -> Nil`
Create a directory (and any missing parent directories). No-ops if it already exists.

```aster
io.mkdir("build/output")
io.write_file("build/output/result.txt", data)
```

---

## Standard error

### `io.print_err(msg: String) -> Nil`
Write `msg` followed by a newline to stderr.

```aster
io.print_err("warning: config file not found, using defaults")
```
