# `list` — Higher-Order List Operations

```aster
use list
use list: map, filter, reduce, sort
```

The `list` module provides functional-style utilities for working with lists.
All functions return new lists — the originals are never modified.

---

## Higher-order functions

### `list.map(fn, lst) -> List`
Apply `fn` to every element; return a new list of results.

```aster
use list

doubles := list.map(fn(x) -> Int: x * 2, [1, 2, 3, 4])
# → [2, 4, 6, 8]
```

### `list.filter(pred, lst) -> List`
Keep only elements for which `pred` returns `true`.

```aster
evens := list.filter(fn(x) -> Bool: x % 2 == 0, [1, 2, 3, 4, 5])
# → [2, 4]
```

### `list.reduce(fn, lst, init)`
Left-fold `lst` using `fn(accumulator, element)`, starting from `init`.

```aster
total := list.reduce(fn(acc, x): acc + x, [1, 2, 3, 4], 0)
# → 10
```

### `list.any(pred, lst) -> Bool`
Return `true` if `pred` is true for at least one element.

```aster
list.any(fn(x) -> Bool: x > 3, [1, 2, 5])   # → true
```

### `list.all(pred, lst) -> Bool`
Return `true` if `pred` is true for every element.

```aster
list.all(fn(x) -> Bool: x > 0, [1, 2, 3])   # → true
```

### `list.count(pred, lst) -> Int`
Count elements for which `pred` returns `true`.

```aster
list.count(fn(x) -> Bool: x % 2 == 0, [1, 2, 3, 4])   # → 2
```

---

## Sorting

### `list.sort(lst) -> List`
Sort a list of comparable values (Int, Float, or String) in ascending order.

```aster
list.sort([3, 1, 4, 1, 5, 9])   # → [1, 1, 3, 4, 5, 9]
list.sort(["banana", "apple"])   # → ["apple", "banana"]
```

### `list.sort_by(key_fn, lst) -> List`
Sort by applying `key_fn` to each element and comparing the results.

```aster
# Sort strings by length
list.sort_by(fn(s) -> Int: len(s), ["banana", "kiwi", "fig"])
# → ["fig", "kiwi", "banana"]
```

---

## Aggregation

### `list.sum(lst) -> Int | Float`
Sum all numeric elements.

```aster
list.sum([1, 2, 3, 4])     # → 10
list.sum([1.5, 2.5])       # → 4.0
```

### `list.product(lst) -> Int | Float`
Multiply all numeric elements together.

```aster
list.product([1, 2, 3, 4])   # → 24
```

---

## Construction

### `list.range(end) -> List[Int]`
### `list.range(start, end) -> List[Int]`
Produce a list of integers from `start` (inclusive) to `end` (exclusive).

```aster
list.range(5)       # → [0, 1, 2, 3, 4]
list.range(2, 6)    # → [2, 3, 4, 5]
```

### `list.repeat(value, n) -> List`
Produce a list of `n` copies of `value`.

```aster
list.repeat(0, 4)   # → [0, 0, 0, 0]
```

### `list.append(lst, elem) -> List`
Return a new list with `elem` added at the end.

```aster
list.append([1, 2], 3)   # → [1, 2, 3]
```

### `list.prepend(elem, lst) -> List`
Return a new list with `elem` at the front.

```aster
list.prepend(0, [1, 2])   # → [0, 1, 2]
```

### `list.concat(a, b) -> List`
Concatenate two lists.

```aster
list.concat([1, 2], [3, 4])   # → [1, 2, 3, 4]
```

---

## Access

### `list.head(lst)`
Return the first element. Raises if the list is empty.

### `list.tail(lst) -> List`
Return all elements except the first. Raises if the list is empty.

### `list.last(lst)`
Return the last element. Raises if the list is empty.

### `list.len(lst) -> Int`
Number of elements. (The global `len()` builtin also accepts lists.)

### `list.take(n, lst) -> List`
Return the first `n` elements.

```aster
list.take(3, [10, 20, 30, 40, 50])   # → [10, 20, 30]
```

### `list.drop(n, lst) -> List`
Skip the first `n` elements and return the rest.

```aster
list.drop(2, [10, 20, 30, 40])   # → [30, 40]
```

---

## Transformation

### `list.reverse(lst) -> List`
Return the list in reversed order.

```aster
list.reverse([1, 2, 3])   # → [3, 2, 1]
```

### `list.flatten(lst) -> List`
Flatten one level of nesting — a list of lists becomes a list.

```aster
list.flatten([[1, 2], [3, 4], [5]])   # → [1, 2, 3, 4, 5]
```

### `list.zip(a, b) -> List[Tuple]`
Pair elements from two lists. Stops at the shorter list.

```aster
list.zip([1, 2, 3], ["a", "b", "c"])
# → [(1, "a"), (2, "b"), (3, "c")]
```

### `list.enumerate(lst) -> List[Tuple]`
Pair each element with its zero-based index.

```aster
list.enumerate(["x", "y", "z"])
# → [(0, "x"), (1, "y"), (2, "z")]
```

### `list.unique(lst) -> List`
Remove duplicate values, preserving order of first occurrence.

```aster
list.unique([1, 2, 1, 3, 2])   # → [1, 2, 3]
```

### `list.contains(lst, value) -> Bool`
True if `value` is present in `lst`.

```aster
list.contains([1, 2, 3], 2)   # → true
```
