# `math` — Mathematical Functions

```aster
use math
use math: sqrt, pi, sin, cos
```

---

## Constants

| Name | Value | Description |
|------|-------|-------------|
| `math.pi` | 3.14159… | Circle constant π |
| `math.e` | 2.71828… | Euler's number |
| `math.tau` | 6.28318… | τ = 2π |
| `math.inf` | ∞ | Positive infinity |
| `math.nan` | NaN | Not-a-number sentinel |

---

## Basic numeric

### `math.abs(n)`
Absolute value. Returns Int if input is Int, Float otherwise.

```aster
math.abs(-7)    # → 7
math.abs(-2.5)  # → 2.5
```

### `math.floor(n) -> Int`
Round down to the nearest integer.

### `math.ceil(n) -> Int`
Round up to the nearest integer.

### `math.round(n) -> Int`
Round to the nearest integer (ties round to even).

### `math.sign(n) -> Int`
Return `1`, `-1`, or `0` depending on the sign of `n`.

```aster
math.sign(-42)  # → -1
math.sign(0)    # → 0
math.sign(7)    # → 1
```

### `math.clamp(x, lo, hi)`
Clamp `x` to the range `[lo, hi]`.

```aster
math.clamp(15, 0, 10)   # → 10
math.clamp(-3, 0, 10)   # → 0
math.clamp(5,  0, 10)   # → 5
```

### `math.min(a, b)` / `math.max(a, b)`
Minimum or maximum of two numeric values.

---

## Power and logarithm

### `math.sqrt(n) -> Float`
Square root. Raises on negative input.

```aster
math.sqrt(16)   # → 4
math.sqrt(2)    # → 1.4142135623730951
```

### `math.pow(base, exp)`
`base` raised to the power `exp`.

```aster
math.pow(2, 10)   # → 1024
math.pow(2, 0.5)  # → 1.4142135623730951
```

### `math.exp(n) -> Float`
`e` raised to the power `n`.

```aster
math.exp(1)   # → 2.718281828459045
math.exp(0)   # → 1.0
```

### `math.log(n) -> Float`
Natural logarithm (base e). Raises on non-positive input.

### `math.log2(n) -> Float`
Base-2 logarithm. Raises on non-positive input.

### `math.log10(n) -> Float`
Base-10 logarithm. Raises on non-positive input.

---

## Trigonometry

All angles are in **radians**.

| Function | Description |
|----------|-------------|
| `math.sin(x)` | Sine |
| `math.cos(x)` | Cosine |
| `math.tan(x)` | Tangent |
| `math.asin(x)` | Arc-sine — input must be in `[-1, 1]` |
| `math.acos(x)` | Arc-cosine — input must be in `[-1, 1]` |
| `math.atan(x)` | Arc-tangent |
| `math.atan2(y, x)` | Arc-tangent of `y/x` in the correct quadrant |

```aster
use math: sin, cos, pi

x := sin(pi / 2)     # → 1.0
y := cos(0)          # → 1.0
a := atan2(1, 1)     # → 0.7853981633974483  (π/4)
```

---

## Hyperbolic functions

| Function | Description |
|----------|-------------|
| `math.sinh(x)` | Hyperbolic sine |
| `math.cosh(x)` | Hyperbolic cosine |
| `math.tanh(x)` | Hyperbolic tangent |

---

## Integer operations

### `math.gcd(a, b) -> Int`
Greatest common divisor.

```aster
math.gcd(12, 8)   # → 4
```

### `math.lcm(a, b) -> Int`
Least common multiple.

```aster
math.lcm(4, 6)    # → 12
```

---

## Classification

### `math.is_nan(n) -> Bool`
True if the value is NaN.

### `math.is_inf(n) -> Bool`
True if the value is ±∞.

### `math.is_finite(n) -> Bool`
True if the value is a finite number (not NaN or ∞).

```aster
use math: is_nan, is_inf, is_finite, nan, inf

is_nan(nan)    # → true
is_inf(inf)    # → true
is_finite(42)  # → true
```
