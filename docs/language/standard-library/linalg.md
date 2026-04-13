# `linalg` — Vectors and Matrices

```aster
use linalg
use linalg: vec, vadd, vdot, mat, mmul
```

The `linalg` module provides 2D/3D/ND vector and matrix operations.
Vectors and matrices are represented as ordinary Aster `List` values — a vector is a
`List[Int|Float]` and a matrix is a `List[List[Int|Float]]` (row-major).

---

## Vectors

### Construction

#### `linalg.vec(x, y, ...) -> List`
Construct a vector from scalar components.

```aster
v := linalg.vec(1, 2, 3)   # → [1, 2, 3]
```

### Inspection

#### `linalg.vdim(v) -> Int`
Number of components (dimensions).

### Arithmetic

| Function | Description |
|----------|-------------|
| `linalg.vadd(a, b)` | Component-wise addition |
| `linalg.vsub(a, b)` | Component-wise subtraction |
| `linalg.vmul(a, b)` | Element-wise (Hadamard) product |
| `linalg.vscale(v, s)` | Multiply all components by scalar `s` |
| `linalg.vneg(v)` | Negate all components |

```aster
a := linalg.vec(1, 2, 3)
b := linalg.vec(4, 5, 6)
linalg.vadd(a, b)      # → [5, 7, 9]
linalg.vscale(a, 2)    # → [2, 4, 6]
```

### Geometry

#### `linalg.vdot(a, b) -> Int | Float`
Dot product of two vectors of the same dimension.

```aster
linalg.vdot(linalg.vec(1, 2), linalg.vec(3, 4))   # → 11
```

#### `linalg.vcross(a, b) -> List`
Cross product of two 3D vectors. Raises for non-3D inputs.

#### `linalg.vlen(v) -> Float`
Euclidean (L2) norm — length of the vector.

#### `linalg.vlen_sq(v) -> Int | Float`
Squared length (avoids the square root when only comparisons are needed).

#### `linalg.vnorm(v) -> List`
Unit vector in the same direction. Raises if the vector has zero length.

#### `linalg.vlerp(a, b, t) -> List`
Linear interpolation: `a + t * (b - a)`. `t = 0` returns `a`, `t = 1` returns `b`.

```aster
linalg.vlerp(linalg.vec(0, 0), linalg.vec(10, 10), 0.5)   # → [5.0, 5.0]
```

---

## Matrices

Matrices are `List[List[Int|Float]]` in row-major order.

### Construction

#### `linalg.mat(row0, row1, ...) -> List`
Construct a matrix from row vectors. All rows must have the same length.

```aster
m := linalg.mat(
    linalg.vec(1, 2),
    linalg.vec(3, 4)
)
# → [[1, 2], [3, 4]]
```

#### `linalg.identity(n: Int) -> List`
Return the n×n identity matrix.

```aster
linalg.identity(3)
# → [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
```

### Inspection

| Function | Description |
|----------|-------------|
| `linalg.mrows(m) -> Int` | Number of rows |
| `linalg.mcols(m) -> Int` | Number of columns |
| `linalg.mget(m, i, j)` | Element at row `i`, column `j` |
| `linalg.mrow(m, i) -> List` | Row `i` as a vector |
| `linalg.mcol(m, j) -> List` | Column `j` as a vector |

### Arithmetic

| Function | Description |
|----------|-------------|
| `linalg.madd(a, b)` | Element-wise addition (same shape required) |
| `linalg.msub(a, b)` | Element-wise subtraction |
| `linalg.mscale(m, s)` | Multiply every element by scalar `s` |
| `linalg.mmul(a, b)` | Matrix multiplication (`a` columns must equal `b` rows) |
| `linalg.mvmul(m, v)` | Matrix × column-vector |

```aster
a := linalg.identity(2)
b := linalg.mat(linalg.vec(2, 0), linalg.vec(0, 2))
linalg.mmul(a, b)   # → [[2, 0], [0, 2]]
```

### Transformations

#### `linalg.mtranspose(m) -> List`
Transpose: rows become columns.

#### `linalg.mdet(m) -> Int | Float`
Determinant of a square matrix.

#### `linalg.minv(m) -> List`
Inverse of a square matrix via Gaussian elimination.
Raises if the matrix is singular.

```aster
m := linalg.mat(linalg.vec(1, 2), linalg.vec(3, 4))
inv := linalg.minv(m)
# inv ≈ [[-2, 1], [1.5, -0.5]]
check := linalg.mmul(m, inv)   # ≈ identity(2)
```

---

## Full example — rotate a 2D point

```aster
use math
use linalg

fn rotate2d(point: List, angle: Float) -> List:
    c := math.cos(angle)
    s := math.sin(angle)
    rot := linalg.mat(linalg.vec(c, -s), linalg.vec(s, c))
    return linalg.mvmul(rot, point)

fn main():
    p := linalg.vec(1, 0)
    rotated := rotate2d(p, math.pi / 2)
    print(rotated)   # → [~0.0, 1.0]
```
