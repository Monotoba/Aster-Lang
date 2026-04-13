# path

The `path` module provides string-based path manipulation utilities.
It works entirely with `String` values and does **not** touch the filesystem.
For filesystem operations (`read_file`, `list_dir`, etc.) use the native `io` module.

Import with `use path`.

---

## Separators

| Function | Returns | Description |
|----------|---------|-------------|
| `path.sep() -> String` | `"/"` | Platform path separator (always `/`) |
| `path.ext_sep() -> String` | `"."` | Extension separator character |

---

## Joining and splitting

### `path.join(a, b) -> String`
Concatenate two path segments with exactly one `/` between them.
Trailing `/` on `a` and a leading `/` on `b` are both stripped before joining.

```aster
path.join("/a/b", "c/d")    # → "/a/b/c/d"
path.join("/a/b/", "/c/d")  # → "/a/b/c/d"
path.join("", "c/d")        # → "c/d"
```

### `path.split(path) -> List[String]`
Split a path on `/` and return its segments as a list.

```aster
path.split("/a/b/c")   # → ["", "a", "b", "c"]
```

---

## Component extraction

### `path.basename(path) -> String`
Return the final component of a path.

```aster
path.basename("/a/b/c.txt")  # → "c.txt"
path.basename("c.txt")       # → "c.txt"
```

### `path.dirname(path) -> String`
Return the directory portion of a path (everything before the last `/`).
Returns `"/"` when the last `/` is at index 0; returns `""` when there is no `/`.

```aster
path.dirname("/a/b/c.txt")  # → "/a/b"
path.dirname("/a")          # → "/"
path.dirname("a/b")         # → "a"
path.dirname("a")           # → ""
```

### `path.stem(path) -> String`
Return the filename without its extension.

```aster
path.stem("/a/b/c.txt")     # → "c"
path.stem("archive.tar.gz") # → "archive.tar"
path.stem("file")           # → "file"
```

### `path.extension(path) -> String`
Return the file extension (including the leading `.`), or `""` if none.

```aster
path.extension("/a/b/c.txt")     # → ".txt"
path.extension("archive.tar.gz") # → ".gz"
path.extension("file")           # → ""
```

### `path.with_extension(path, ext) -> String`
Replace the extension on a path.
If `ext` does not start with `.`, one is prepended automatically.

```aster
path.with_extension("/a/b/c.txt", ".md")   # → "/a/b/c.md"
path.with_extension("/a/b/c.txt", "md")    # → "/a/b/c.md"
path.with_extension("c", ".py")            # → "c.py"
```

---

## Predicates

### `path.is_absolute(path) -> Bool`
Return `true` if the path starts with `/`.

```aster
path.is_absolute("/a/b")  # → true
path.is_absolute("a/b")   # → false
```

### `path.is_relative(path) -> Bool`
Return `true` if the path does not start with `/`.

```aster
path.is_relative("a/b")   # → true
path.is_relative("/a/b")  # → false
```

### `path.has_extension(path) -> Bool`
Return `true` if the path has a non-empty file extension.

```aster
path.has_extension("file.txt")  # → true
path.has_extension("file")      # → false
```

---

## Normalisation

### `path.normalize(path) -> String`
Collapse redundant slashes and remove the trailing slash.
Returns `"."` for an empty path.

```aster
path.normalize("/a/b/")  # → "/a/b"
path.normalize("/a/b")   # → "/a/b"
path.normalize("")        # → "."
```

---

## Example

```aster
use path

fn main():
    p := "/home/user/project/main.aster"
    print(path.basename(p))                      # main.aster
    print(path.stem(p))                          # main
    print(path.extension(p))                     # .aster
    print(path.dirname(p))                       # /home/user/project
    print(path.with_extension(p, ".ast"))        # /home/user/project/main.ast
    print(path.join(path.dirname(p), "lib/utils.aster"))
    # → /home/user/project/lib/utils.aster
```
