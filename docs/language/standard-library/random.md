# `random` — Pseudo-Random Number Generation

```aster
use random
use random: rand_int, choice, shuffle
```

The `random` module wraps a Mersenne Twister PRNG.
Results are not cryptographically secure — do not use for security-sensitive purposes.

---

## Seeding

### `random.seed(n: Int) -> Nil`
Seed the PRNG with an integer. Seeding with the same value produces the same sequence.
Useful for reproducible tests.

```aster
random.seed(42)
```

---

## Generating numbers

### `random.random() -> Float`
Return a uniformly distributed float in the half-open interval `[0.0, 1.0)`.

```aster
x := random.random()   # e.g. 0.37444887175646646
```

### `random.rand_int(low: Int, high: Int) -> Int`
Return a random integer in `[low, high]` inclusive.

```aster
dice := random.rand_int(1, 6)
```

### `random.rand_float(low, high) -> Float`
Return a uniform float in `[low, high)`.

```aster
temp := random.rand_float(36.0, 37.5)
```

---

## Working with lists

### `random.choice(lst: List)`
Return a single randomly-chosen element from a non-empty list. Raises if the list is empty.

```aster
suits := ["hearts", "diamonds", "clubs", "spades"]
suit := random.choice(suits)
```

### `random.shuffle(lst: List) -> List`
Return a new list with the same elements in a random order. The original list is unchanged.

```aster
deck := list.range(1, 53)
shuffled := random.shuffle(deck)
```

### `random.sample(lst: List, k: Int) -> List`
Return `k` unique elements chosen at random from `lst`, without replacement.
Raises if `k` is larger than the list length.

```aster
winners := random.sample(participants, 3)
```

---

## Example — simple dice game

```aster
use random
use std

fn roll_dice(sides: Int) -> Int:
    return random.rand_int(1, sides)

fn main():
    random.seed(1)
    d6 := roll_dice(6)
    d20 := roll_dice(20)
    print("d6:  " + str(d6))
    print("d20: " + str(d20))
```
