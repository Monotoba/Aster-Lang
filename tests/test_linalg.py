"""Tests for the linalg native module (vectors and matrices)."""

from __future__ import annotations

import math

import pytest

from aster_lang.interpreter import Interpreter, InterpreterError
from aster_lang.parser import parse_module


def run(source: str) -> list[str]:
    m = parse_module(source)
    interp = Interpreter()
    interp.interpret(m)
    return interp.output


def run1(expr: str) -> str:
    """Evaluate one expression via print; return its string representation."""
    src = f"use linalg\nfn main():\n    print({expr})\n"
    return run(src)[0]


def approx(a: str, b: float, rel: float = 1e-9) -> bool:
    return math.isclose(float(a), b, rel_tol=rel)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestLinalgRegistry:
    def test_module_registered(self) -> None:
        from aster_lang.native_modules import NATIVE_MODULES

        assert "linalg" in NATIVE_MODULES

    def test_symbols_registered(self) -> None:
        from aster_lang.native_modules import NATIVE_MODULE_SYMBOLS

        syms = NATIVE_MODULE_SYMBOLS["linalg"]
        assert "vec" in syms
        assert "vdot" in syms
        assert "mmul" in syms
        assert "mdet" in syms


# ---------------------------------------------------------------------------
# Vector construction
# ---------------------------------------------------------------------------


class TestVec:
    def test_vec_2d(self) -> None:
        src = (
            "use linalg\nfn main():\n    v := linalg.vec(1, 2)\n    print(v[0])\n    print(v[1])\n"
        )
        assert run(src) == ["1", "2"]

    def test_vec_3d(self) -> None:
        src = "use linalg\nfn main():\n    v := linalg.vec(1, 2, 3)\n    print(linalg.vdim(v))\n"
        assert run(src) == ["3"]

    def test_vdim(self) -> None:
        assert run1("linalg.vdim(linalg.vec(10, 20, 30, 40))") == "4"

    def test_vec_empty_raises(self) -> None:
        src = "use linalg\nfn main():\n    v := linalg.vec()\n"
        m = parse_module(src)
        interp = Interpreter()
        with pytest.raises(InterpreterError, match="at least one"):
            interp.interpret(m)


# ---------------------------------------------------------------------------
# Vector arithmetic
# ---------------------------------------------------------------------------


class TestVectorArithmetic:
    def test_vadd(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    r := linalg.vadd(linalg.vec(1, 2), linalg.vec(3, 4))\n"
            "    print(r[0])\n    print(r[1])\n"
        )
        assert run(src) == ["4", "6"]

    def test_vsub(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    r := linalg.vsub(linalg.vec(5, 3), linalg.vec(2, 1))\n"
            "    print(r[0])\n    print(r[1])\n"
        )
        assert run(src) == ["3", "2"]

    def test_vmul_hadamard(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    r := linalg.vmul(linalg.vec(2, 3), linalg.vec(4, 5))\n"
            "    print(r[0])\n    print(r[1])\n"
        )
        assert run(src) == ["8", "15"]

    def test_vscale(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    r := linalg.vscale(linalg.vec(1, 2, 3), 2)\n"
            "    print(r[0])\n    print(r[1])\n    print(r[2])\n"
        )
        assert run(src) == ["2", "4", "6"]

    def test_vneg(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    r := linalg.vneg(linalg.vec(1, -2, 3))\n"
            "    print(r[0])\n    print(r[1])\n    print(r[2])\n"
        )
        assert run(src) == ["-1", "2", "-3"]

    def test_vadd_dim_mismatch(self) -> None:
        src = "use linalg\nfn main():\n    linalg.vadd(linalg.vec(1, 2), linalg.vec(1, 2, 3))\n"
        m = parse_module(src)
        interp = Interpreter()
        with pytest.raises(InterpreterError, match="dimension mismatch"):
            interp.interpret(m)


# ---------------------------------------------------------------------------
# Dot product and cross product
# ---------------------------------------------------------------------------


class TestDotAndCross:
    def test_vdot_int(self) -> None:
        assert run1("linalg.vdot(linalg.vec(1, 2, 3), linalg.vec(4, 5, 6))") == "32"

    def test_vdot_zero(self) -> None:
        assert run1("linalg.vdot(linalg.vec(1, 0), linalg.vec(0, 1))") == "0"

    def test_vcross(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    r := linalg.vcross(linalg.vec(1, 0, 0), linalg.vec(0, 1, 0))\n"
            "    print(r[0])\n    print(r[1])\n    print(r[2])\n"
        )
        assert run(src) == ["0", "0", "1"]

    def test_vcross_requires_3d(self) -> None:
        src = "use linalg\nfn main():\n    linalg.vcross(linalg.vec(1, 2), linalg.vec(3, 4))\n"
        m = parse_module(src)
        interp = Interpreter()
        with pytest.raises(InterpreterError, match="3-dimensional"):
            interp.interpret(m)


# ---------------------------------------------------------------------------
# Length and normalization
# ---------------------------------------------------------------------------


class TestLengthAndNorm:
    def test_vlen_pythagorean(self) -> None:
        assert run1("linalg.vlen(linalg.vec(3, 4))") == "5"

    def test_vlen_sq(self) -> None:
        assert run1("linalg.vlen_sq(linalg.vec(3, 4))") == "25"

    def test_vnorm_unit_vector_unchanged(self) -> None:
        result = run1("linalg.vlen(linalg.vnorm(linalg.vec(3, 4)))")
        assert approx(result, 1.0)

    def test_vnorm_zero_raises(self) -> None:
        src = "use linalg\nfn main():\n    linalg.vnorm(linalg.vec(0, 0))\n"
        m = parse_module(src)
        interp = Interpreter()
        with pytest.raises(InterpreterError, match="zero-length"):
            interp.interpret(m)


# ---------------------------------------------------------------------------
# vlerp
# ---------------------------------------------------------------------------


class TestVlerp:
    def test_vlerp_midpoint(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    r := linalg.vlerp(linalg.vec(0, 0), linalg.vec(10, 20), 1)\n"
            "    print(r[0])\n    print(r[1])\n"
        )
        assert run(src) == ["10", "20"]

    def test_vlerp_start(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    r := linalg.vlerp(linalg.vec(5, 5), linalg.vec(10, 10), 0)\n"
            "    print(r[0])\n    print(r[1])\n"
        )
        assert run(src) == ["5", "5"]


# ---------------------------------------------------------------------------
# Matrix construction
# ---------------------------------------------------------------------------


class TestMatConstruction:
    def test_identity_2x2(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    m := linalg.identity(2)\n"
            "    print(linalg.mget(m, 0, 0))\n"
            "    print(linalg.mget(m, 0, 1))\n"
            "    print(linalg.mget(m, 1, 0))\n"
            "    print(linalg.mget(m, 1, 1))\n"
        )
        assert run(src) == ["1", "0", "0", "1"]

    def test_mat_from_rows(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    m := linalg.mat([1, 2], [3, 4])\n"
            "    print(linalg.mget(m, 0, 0))\n"
            "    print(linalg.mget(m, 1, 1))\n"
        )
        assert run(src) == ["1", "4"]

    def test_mrows_mcols(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    m := linalg.mat([1, 2, 3], [4, 5, 6])\n"
            "    print(linalg.mrows(m))\n"
            "    print(linalg.mcols(m))\n"
        )
        assert run(src) == ["2", "3"]

    def test_mrow(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    m := linalg.mat([10, 20], [30, 40])\n"
            "    r := linalg.mrow(m, 1)\n"
            "    print(r[0])\n    print(r[1])\n"
        )
        assert run(src) == ["30", "40"]

    def test_mcol(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    m := linalg.mat([1, 2], [3, 4])\n"
            "    c := linalg.mcol(m, 1)\n"
            "    print(c[0])\n    print(c[1])\n"
        )
        assert run(src) == ["2", "4"]


# ---------------------------------------------------------------------------
# Matrix arithmetic
# ---------------------------------------------------------------------------


class TestMatArithmetic:
    def test_madd(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    a := linalg.mat([1, 2], [3, 4])\n"
            "    b := linalg.mat([5, 6], [7, 8])\n"
            "    r := linalg.madd(a, b)\n"
            "    print(linalg.mget(r, 0, 0))\n"
            "    print(linalg.mget(r, 1, 1))\n"
        )
        assert run(src) == ["6", "12"]

    def test_msub(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    a := linalg.mat([5, 6], [7, 8])\n"
            "    b := linalg.mat([1, 2], [3, 4])\n"
            "    r := linalg.msub(a, b)\n"
            "    print(linalg.mget(r, 0, 0))\n"
            "    print(linalg.mget(r, 1, 1))\n"
        )
        assert run(src) == ["4", "4"]

    def test_mscale(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    m := linalg.mat([1, 2], [3, 4])\n"
            "    r := linalg.mscale(m, 2)\n"
            "    print(linalg.mget(r, 0, 0))\n"
            "    print(linalg.mget(r, 1, 1))\n"
        )
        assert run(src) == ["2", "8"]

    def test_mmul_identity(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    m := linalg.mat([1, 2], [3, 4])\n"
            "    i := linalg.identity(2)\n"
            "    r := linalg.mmul(m, i)\n"
            "    print(linalg.mget(r, 0, 0))\n"
            "    print(linalg.mget(r, 0, 1))\n"
            "    print(linalg.mget(r, 1, 0))\n"
            "    print(linalg.mget(r, 1, 1))\n"
        )
        assert run(src) == ["1", "2", "3", "4"]

    def test_mmul_2x2(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    a := linalg.mat([1, 2], [3, 4])\n"
            "    b := linalg.mat([5, 6], [7, 8])\n"
            "    r := linalg.mmul(a, b)\n"
            "    print(linalg.mget(r, 0, 0))\n"
            "    print(linalg.mget(r, 0, 1))\n"
            "    print(linalg.mget(r, 1, 0))\n"
            "    print(linalg.mget(r, 1, 1))\n"
        )
        assert run(src) == ["19", "22", "43", "50"]

    def test_mvmul(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    m := linalg.mat([1, 0], [0, 2])\n"
            "    v := linalg.vec(3, 4)\n"
            "    r := linalg.mvmul(m, v)\n"
            "    print(r[0])\n    print(r[1])\n"
        )
        assert run(src) == ["3", "8"]

    def test_mtranspose(self) -> None:
        src = (
            "use linalg\nfn main():\n"
            "    m := linalg.mat([1, 2, 3], [4, 5, 6])\n"
            "    t := linalg.mtranspose(m)\n"
            "    print(linalg.mrows(t))\n"
            "    print(linalg.mcols(t))\n"
            "    print(linalg.mget(t, 0, 1))\n"
        )
        assert run(src) == ["3", "2", "4"]


# ---------------------------------------------------------------------------
# Determinant and inverse
# ---------------------------------------------------------------------------


class TestDetAndInv:
    def test_det_2x2(self) -> None:
        assert run1("linalg.mdet(linalg.mat([3, 8], [4, 6]))") == "-14"

    def test_det_identity(self) -> None:
        assert run1("linalg.mdet(linalg.identity(3))") == "1"

    def test_det_3x3(self) -> None:
        # det([[6,1,1],[4,-2,5],[2,8,7]]) = -306
        src = (
            "use linalg\nfn main():\n"
            "    m := linalg.mat([6, 1, 1], [4, -2, 5], [2, 8, 7])\n"
            "    print(linalg.mdet(m))\n"
        )
        assert run(src) == ["-306"]

    def test_minv_2x2(self) -> None:
        # inverse of [[4,7],[2,6]] is [[0.6,-0.7],[-0.2,0.4]]
        src = (
            "use linalg\nfn main():\n"
            "    m := linalg.mat([4, 7], [2, 6])\n"
            "    inv := linalg.minv(m)\n"
            "    prod := linalg.mmul(m, inv)\n"
            "    print(linalg.mget(prod, 0, 0))\n"
            "    print(linalg.mget(prod, 1, 1))\n"
        )
        out = run(src)
        assert approx(out[0], 1.0)
        assert approx(out[1], 1.0)

    def test_minv_singular_raises(self) -> None:
        src = "use linalg\nfn main():\n    m := linalg.mat([1, 2], [2, 4])\n    linalg.minv(m)\n"
        m = parse_module(src)
        interp = Interpreter()
        with pytest.raises(InterpreterError, match="singular"):
            interp.interpret(m)
