"""High-level Intermediate Representation (HIR) for the Aster language.

The HIR sits between the AST (produced by the parser) and the backend
compilers (Python transpiler, bytecode VM).  It:

  1. Attaches the inferred semantic type to every expression node.
  2. Desugars destructuring let-bindings into sequences of simple
     single-name bindings backed by temporaries.
  3. Lifts lambda expressions into named ``HFunction`` definitions with an
     explicit capture list, replacing them at the use-site with
     ``HClosure`` references.

Control-flow constructs (``if``, ``while``, ``for``, ``match``) are
kept as-is — their desugaring into flat conditionals belongs in a later
MIR pass.  AST patterns inside ``HMatchArm`` are preserved as raw
``ast.Pattern`` objects for the same reason.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aster_lang import ast
from aster_lang.formatter import Formatter
from aster_lang.semantic import STRING_TYPE, UNKNOWN_TYPE, SemanticAnalyzer, Type

# ---------------------------------------------------------------------------
# HIR expression nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HLit:
    """Integer, string, bool, or nil literal."""

    value: int | str | bool | None
    ty: Type


@dataclass(frozen=True)
class HName:
    """Variable / parameter reference."""

    name: str
    ty: Type


@dataclass(frozen=True)
class HBinOp:
    """Binary operation: left op right."""

    op: str
    left: HExpr
    right: HExpr
    ty: Type


@dataclass(frozen=True)
class HUnaryOp:
    """Unary operation: op operand."""

    op: str
    operand: HExpr
    ty: Type


@dataclass(frozen=True)
class HCall:
    """Function call: func(args)."""

    func: HExpr
    args: tuple[HExpr, ...]
    ty: Type


@dataclass(frozen=True)
class HIndex:
    """Index expression: obj[index]."""

    obj: HExpr
    index: HExpr
    ty: Type


@dataclass(frozen=True)
class HMember:
    """Member access: obj.member."""

    obj: HExpr
    member: str
    ty: Type


@dataclass(frozen=True)
class HList:
    """List constructor: [e1, e2, ...]."""

    elements: tuple[HExpr, ...]
    ty: Type


@dataclass(frozen=True)
class HTuple:
    """Tuple constructor: (e1, e2, ...)."""

    elements: tuple[HExpr, ...]
    ty: Type


@dataclass(frozen=True)
class HRecord:
    """Record constructor: {field: value, ...}."""

    fields: tuple[tuple[str, HExpr], ...]
    ty: Type


@dataclass(frozen=True)
class HBorrow:
    """Borrow expression: &expr or &mut expr."""

    target: HExpr
    is_mutable: bool
    ty: Type


@dataclass(frozen=True)
class HClosure:
    """Reference to a lambda that was lifted into a named ``HFunction``.

    ``fn_id`` is the qualified function identifier used in the containing
    ``HModule.lifted_fns`` dictionary.  ``free_vars`` lists the names of
    variables captured from the enclosing lexical scope.
    """

    fn_id: str
    free_vars: tuple[str, ...]
    ty: Type


HExpr = (
    HLit
    | HName
    | HBinOp
    | HUnaryOp
    | HCall
    | HIndex
    | HMember
    | HList
    | HTuple
    | HRecord
    | HBorrow
    | HClosure
)

# ---------------------------------------------------------------------------
# HIR statement nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HLet:
    """Simple (non-destructuring) let binding: name := init."""

    name: str
    is_mutable: bool
    ty: Type
    init: HExpr


@dataclass(frozen=True)
class HAssign:
    """Assignment statement: target <- value."""

    target: HExpr
    value: HExpr


@dataclass(frozen=True)
class HReturn:
    """Return statement."""

    value: HExpr | None


@dataclass(frozen=True)
class HExprStmt:
    """Expression used as a statement."""

    expr: HExpr


@dataclass(frozen=True)
class HBreak:
    """Break statement."""


@dataclass(frozen=True)
class HContinue:
    """Continue statement."""


@dataclass(frozen=True)
class HIf:
    """If / else statement."""

    condition: HExpr
    then_body: tuple[HStmt, ...]
    else_body: tuple[HStmt, ...] | None


@dataclass(frozen=True)
class HWhile:
    """While loop."""

    condition: HExpr
    body: tuple[HStmt, ...]


@dataclass(frozen=True)
class HFor:
    """For loop (kept as-is; iterator desugaring is MIR)."""

    variable: str
    iterable: HExpr
    body: tuple[HStmt, ...]


@dataclass(frozen=True)
class HMatchArm:
    """Single arm of a match statement.

    AST patterns are preserved — pattern desugaring belongs in MIR.
    """

    pattern: ast.Pattern
    body: tuple[HStmt, ...]


@dataclass(frozen=True)
class HMatch:
    """Match statement."""

    subject: HExpr
    arms: tuple[HMatchArm, ...]


HStmt = HLet | HAssign | HReturn | HExprStmt | HBreak | HContinue | HIf | HWhile | HFor | HMatch

# ---------------------------------------------------------------------------
# HIR declaration nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HFunction:
    """Function definition (including lifted lambdas).

    ``fn_id`` is a globally unique string identifier (e.g.
    ``"__entry__::my_fn"`` or ``"__entry__::my_fn::__lambda1"``).
    For lifted lambdas ``free_vars`` is non-empty.
    """

    fn_id: str
    name: str  # user-visible name (lambda: ``__lambdaN``)
    params: tuple[str, ...]
    param_types: tuple[Type, ...]
    return_type: Type
    free_vars: tuple[str, ...]  # captured names; empty for regular functions
    body: tuple[HStmt, ...]
    is_public: bool
    effects: tuple[str, ...]


@dataclass(frozen=True)
class HLetDecl:
    """Top-level let declaration."""

    name: str
    ty: Type
    is_mutable: bool
    is_public: bool
    init: HExpr


@dataclass(frozen=True)
class HImportDecl:
    """Import declaration."""

    module: tuple[str, ...]
    imports: tuple[str, ...] | None
    alias: str | None


@dataclass(frozen=True)
class HEffectDecl:
    """Effect declaration."""

    name: str
    is_public: bool


@dataclass(frozen=True)
class HTypeAliasDecl:
    """Type alias (no runtime representation; preserved for later passes)."""

    name: str
    is_public: bool


# Top-level items that appear in HModule.decls.
HTopLevel = HFunction | HLetDecl | HImportDecl | HEffectDecl | HTypeAliasDecl


@dataclass(frozen=True)
class HModule:
    """A lowered module.

    ``decls`` contains top-level items in source order.  Lambdas lifted
    from function bodies appear in ``lifted_fns`` only — they are not
    in ``decls``.
    """

    decls: tuple[HTopLevel, ...]
    # Lambda functions lifted out of function bodies; keyed by fn_id.
    lifted_fns: dict[str, HFunction] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Lowering pass
# ---------------------------------------------------------------------------


def lower_module(module: ast.Module, analyzer: SemanticAnalyzer) -> HModule:
    """Lower an AST module into a typed HIR.

    This is the main entry point.  See module docstring for the
    transformations performed.
    """
    lowerer = _Lowerer(analyzer)
    return lowerer.lower(module)


class _Lowerer:
    """Internal worker that walks the AST and produces HIR."""

    def __init__(self, analyzer: SemanticAnalyzer) -> None:
        self._analyzer = analyzer
        self._lambda_counter = 0
        self._lifted_fns: dict[str, HFunction] = {}
        # Stack of enclosing function fn_ids (for generating lambda ids).
        self._fn_id_stack: list[str] = ["__entry__"]

    def _ty(self, expr: ast.Expr) -> Type:
        return self._analyzer.expr_types.get(id(expr), UNKNOWN_TYPE)

    # ------------------------------------------------------------------
    # Module

    def lower(self, module: ast.Module) -> HModule:
        decls: list[HTopLevel] = []
        for decl in module.declarations:
            lowered = self._lower_decl(decl)
            if lowered is not None:
                decls.append(lowered)
        return HModule(decls=tuple(decls), lifted_fns=dict(self._lifted_fns))

    # ------------------------------------------------------------------
    # Declarations

    def _lower_decl(self, decl: ast.Decl) -> HTopLevel | None:
        if isinstance(decl, ast.FunctionDecl):
            return self._lower_function_decl(decl)
        if isinstance(decl, ast.LetDecl):
            return self._lower_let_decl(decl)
        if isinstance(decl, ast.ImportDecl):
            return HImportDecl(
                module=tuple(decl.module.parts),
                imports=tuple(decl.imports) if decl.imports is not None else None,
                alias=decl.alias,
            )
        if isinstance(decl, ast.EffectDecl):
            return HEffectDecl(name=decl.name, is_public=decl.is_public)
        if isinstance(decl, ast.TypeAliasDecl):
            return HTypeAliasDecl(name=decl.name, is_public=decl.is_public)
        # TraitDecl / ImplDecl: no runtime representation yet.
        return None

    def _lower_function_decl(self, decl: ast.FunctionDecl) -> HFunction:
        from aster_lang.semantic import FunctionType

        fn_id = f"{self._fn_id_stack[0]}::{decl.name}"
        self._fn_id_stack.append(fn_id)
        try:
            body = self._lower_stmts(decl.body)
        finally:
            self._fn_id_stack.pop()

        # Resolve param/return types from the symbol.
        sym = self._analyzer.symbol_table.lookup(decl.name)
        if sym is not None and isinstance(sym.type, FunctionType):
            param_types = sym.type.param_types
            return_type = sym.type.return_type
        else:
            param_types = tuple(UNKNOWN_TYPE for _ in decl.params)
            return_type = UNKNOWN_TYPE

        return HFunction(
            fn_id=fn_id,
            name=decl.name,
            params=tuple(p.name for p in decl.params),
            param_types=param_types,
            return_type=return_type,
            free_vars=(),
            body=body,
            is_public=decl.is_public,
            effects=tuple(decl.effects),
        )

    def _lower_let_decl(self, decl: ast.LetDecl) -> HLetDecl:
        init = self._lower_expr(decl.initializer)
        sym = self._analyzer.symbol_table.lookup(decl.name)
        ty = sym.type if sym is not None else UNKNOWN_TYPE
        return HLetDecl(
            name=decl.name,
            ty=ty,
            is_mutable=decl.is_mutable,
            is_public=decl.is_public,
            init=init,
        )

    # ------------------------------------------------------------------
    # Statements

    def _lower_stmts(self, stmts: list[ast.Stmt]) -> tuple[HStmt, ...]:
        out: list[HStmt] = []
        for s in stmts:
            out.extend(self._lower_stmt(s))
        return tuple(out)

    def _lower_stmt(self, stmt: ast.Stmt) -> list[HStmt]:
        if isinstance(stmt, ast.LetStmt):
            return self._lower_let_stmt(stmt)
        if isinstance(stmt, ast.AssignStmt):
            return [
                HAssign(
                    target=self._lower_expr(stmt.target),
                    value=self._lower_expr(stmt.value),
                )
            ]
        if isinstance(stmt, ast.ReturnStmt):
            val = self._lower_expr(stmt.value) if stmt.value is not None else None
            return [HReturn(value=val)]
        if isinstance(stmt, ast.ExprStmt):
            return [HExprStmt(expr=self._lower_expr(stmt.expr))]
        if isinstance(stmt, ast.BreakStmt):
            return [HBreak()]
        if isinstance(stmt, ast.ContinueStmt):
            return [HContinue()]
        if isinstance(stmt, ast.IfStmt):
            return [
                HIf(
                    condition=self._lower_expr(stmt.condition),
                    then_body=self._lower_stmts(stmt.then_block),
                    else_body=self._lower_stmts(stmt.else_block) if stmt.else_block else None,
                )
            ]
        if isinstance(stmt, ast.WhileStmt):
            return [
                HWhile(
                    condition=self._lower_expr(stmt.condition),
                    body=self._lower_stmts(stmt.body),
                )
            ]
        if isinstance(stmt, ast.ForStmt):
            return [
                HFor(
                    variable=stmt.variable,
                    iterable=self._lower_expr(stmt.iterable),
                    body=self._lower_stmts(stmt.body),
                )
            ]
        if isinstance(stmt, ast.MatchStmt):
            arms = tuple(
                HMatchArm(
                    pattern=arm.pattern,
                    body=self._lower_stmts(arm.body),
                )
                for arm in stmt.arms
            )
            return [HMatch(subject=self._lower_expr(stmt.subject), arms=arms)]
        return []  # unknown statement type

    def _lower_let_stmt(self, stmt: ast.LetStmt) -> list[HStmt]:
        """Desugar a let statement — potentially destructuring — into HIR.

        Simple binding ``name := init`` → one ``HLet``.
        Destructuring ``(a, b) := init`` →
            ``__tmpN := init``
            ``a := __tmpN[0]``
            ``b := __tmpN[1]``
        """
        init = self._lower_expr(stmt.initializer)
        init_ty = init.ty

        if isinstance(stmt.pattern, ast.BindingPattern):
            return [
                HLet(
                    name=stmt.pattern.name,
                    is_mutable=stmt.is_mutable,
                    ty=init_ty,
                    init=init,
                )
            ]

        if isinstance(stmt.pattern, ast.WildcardPattern):
            # Evaluate init for side effects, discard.
            return [HExprStmt(expr=init)]

        # Destructuring: introduce a temporary, then emit individual bindings.
        tmp = self._fresh_tmp()
        result: list[HStmt] = [HLet(name=tmp, is_mutable=False, ty=init_ty, init=init)]
        src = HName(name=tmp, ty=init_ty)
        result.extend(self._desugar_pattern(stmt.pattern, src, is_mutable=stmt.is_mutable))
        return result

    def _desugar_pattern(
        self, pattern: ast.Pattern, src: HExpr, *, is_mutable: bool
    ) -> list[HStmt]:
        """Recursively expand a destructuring pattern into ``HLet`` statements."""
        if isinstance(pattern, ast.BindingPattern):
            return [HLet(name=pattern.name, is_mutable=is_mutable, ty=src.ty, init=src)]

        if isinstance(pattern, ast.WildcardPattern):
            return []

        if isinstance(pattern, ast.TuplePattern | ast.ListPattern):
            stmts: list[HStmt] = []
            elements = pattern.elements
            for i, elem in enumerate(elements):
                if isinstance(elem, ast.RestPattern):
                    # rest binds obj[i:]
                    slice_expr = _make_slice_from(src, i)
                    tmp = self._fresh_tmp()
                    stmts.append(HLet(name=tmp, is_mutable=False, ty=UNKNOWN_TYPE, init=slice_expr))
                    tmp_ref = HName(name=tmp, ty=UNKNOWN_TYPE)
                    stmts.extend(self._desugar_pattern(elem, tmp_ref, is_mutable=is_mutable))
                else:
                    idx_expr = _make_index(src, i)
                    tmp = self._fresh_tmp()
                    stmts.append(HLet(name=tmp, is_mutable=False, ty=UNKNOWN_TYPE, init=idx_expr))
                    tmp_ref = HName(name=tmp, ty=UNKNOWN_TYPE)
                    stmts.extend(self._desugar_pattern(elem, tmp_ref, is_mutable=is_mutable))
            return stmts

        if isinstance(pattern, ast.RecordPattern):
            stmts = []
            for rf in pattern.fields:
                member_expr = HMember(obj=src, member=rf.name, ty=UNKNOWN_TYPE)
                tmp = self._fresh_tmp()
                stmts.append(HLet(name=tmp, is_mutable=False, ty=UNKNOWN_TYPE, init=member_expr))
                tmp_ref = HName(name=tmp, ty=UNKNOWN_TYPE)
                stmts.extend(self._desugar_pattern(rf.pattern, tmp_ref, is_mutable=is_mutable))
            return stmts

        if isinstance(pattern, ast.RestPattern):
            return [HLet(name=pattern.name, is_mutable=is_mutable, ty=src.ty, init=src)]

        # Unknown pattern — no bindings.
        return []

    # ------------------------------------------------------------------
    # Expressions

    def _lower_expr(self, expr: ast.Expr) -> HExpr:
        ty = self._ty(expr)

        if isinstance(expr, ast.IntegerLiteral):
            return HLit(value=expr.value, ty=ty)
        if isinstance(expr, ast.StringLiteral):
            return HLit(value=expr.value, ty=ty)
        if isinstance(expr, ast.InterpolatedString):
            # Lower into a sequence of binary + operations.
            # f"a {b} c" -> ("a" + str(b)) + "c"
            result: HExpr | None = None
            for part in expr.parts:
                part_expr: HExpr
                if part.is_expression:
                    inner = self._lower_expr(part.value)  # type: ignore[arg-type]
                    if inner.ty == STRING_TYPE:
                        part_expr = inner
                    else:
                        # Wrap in str() call
                        part_expr = HCall(
                            func=HName(name="str", ty=UNKNOWN_TYPE),
                            args=(inner,),
                            ty=STRING_TYPE,
                        )
                else:
                    part_expr = HLit(value=str(part.value), ty=STRING_TYPE)

                if result is None:
                    result = part_expr
                else:
                    result = HBinOp(op="+", left=result, right=part_expr, ty=STRING_TYPE)
            return result or HLit(value="", ty=STRING_TYPE)
        if isinstance(expr, ast.BoolLiteral):
            return HLit(value=expr.value, ty=ty)
        if isinstance(expr, ast.NilLiteral):
            return HLit(value=None, ty=ty)
        if isinstance(expr, ast.Identifier):
            return HName(name=expr.name, ty=ty)
        if isinstance(expr, ast.QualifiedName):
            return HName(name=str(expr), ty=ty)
        if isinstance(expr, ast.ParenExpr):
            return self._lower_expr(expr.expr)
        if isinstance(expr, ast.BinaryExpr):
            return HBinOp(
                op=expr.operator,
                left=self._lower_expr(expr.left),
                right=self._lower_expr(expr.right),
                ty=ty,
            )
        if isinstance(expr, ast.UnaryExpr):
            return HUnaryOp(op=expr.operator, operand=self._lower_expr(expr.operand), ty=ty)
        if isinstance(expr, ast.BorrowExpr):
            return HBorrow(
                target=self._lower_expr(expr.target),
                is_mutable=expr.is_mutable,
                ty=ty,
            )
        if isinstance(expr, ast.CallExpr):
            return HCall(
                func=self._lower_expr(expr.func),
                args=tuple(self._lower_expr(a) for a in expr.args),
                ty=ty,
            )
        if isinstance(expr, ast.IndexExpr):
            return HIndex(
                obj=self._lower_expr(expr.obj),
                index=self._lower_expr(expr.index),
                ty=ty,
            )
        if isinstance(expr, ast.MemberExpr):
            return HMember(obj=self._lower_expr(expr.obj), member=expr.member, ty=ty)
        if isinstance(expr, ast.ListExpr):
            return HList(elements=tuple(self._lower_expr(e) for e in expr.elements), ty=ty)
        if isinstance(expr, ast.TupleExpr):
            return HTuple(elements=tuple(self._lower_expr(e) for e in expr.elements), ty=ty)
        if isinstance(expr, ast.RecordExpr):
            return HRecord(
                fields=tuple((f.name, self._lower_expr(f.value)) for f in expr.fields),
                ty=ty,
            )
        if isinstance(expr, ast.LambdaExpr):
            return self._lift_lambda(expr, ty)

        # Fallback: return a name node with best-effort label.
        return HName(name=f"<{type(expr).__name__}>", ty=ty)

    def _lift_lambda(self, expr: ast.LambdaExpr, ty: Type) -> HClosure:
        """Lift a lambda expression into a named ``HFunction``."""
        self._lambda_counter += 1
        enclosing = self._fn_id_stack[-1]
        lambda_id = f"{enclosing}::__lambda{self._lambda_counter}"

        # Compute free variables via a simple name walk.
        free_vars = sorted(_free_names_lambda(expr))

        params = tuple(p.name for p in expr.params)
        param_types = tuple(UNKNOWN_TYPE for _ in expr.params)

        # Build a synthetic body.
        body_stmts: list[ast.Stmt] = (
            expr.body if isinstance(expr.body, list) else [ast.ReturnStmt(value=expr.body)]
        )

        self._fn_id_stack.append(lambda_id)
        try:
            body = self._lower_stmts(body_stmts)
        finally:
            self._fn_id_stack.pop()

        hfn = HFunction(
            fn_id=lambda_id,
            name=f"__lambda{self._lambda_counter}",
            params=params,
            param_types=param_types,
            return_type=UNKNOWN_TYPE,
            free_vars=tuple(free_vars),
            body=body,
            is_public=False,
            effects=(),
        )
        self._lifted_fns[lambda_id] = hfn
        return HClosure(fn_id=lambda_id, free_vars=tuple(free_vars), ty=ty)

    # ------------------------------------------------------------------
    # Helpers

    _tmp_counter: int = 0

    def _fresh_tmp(self) -> str:
        _Lowerer._tmp_counter += 1
        return f"__hir_tmp{_Lowerer._tmp_counter}"


# ---------------------------------------------------------------------------
# Helpers for building HIR index/slice expressions
# ---------------------------------------------------------------------------


def _make_index(obj: HExpr, idx: int) -> HIndex:
    from aster_lang.semantic import INT_TYPE

    return HIndex(obj=obj, index=HLit(value=idx, ty=INT_TYPE), ty=UNKNOWN_TYPE)


def _make_slice_from(obj: HExpr, start: int) -> HIndex:
    """Represent obj[start:] as an HIndex with a negative-sentinel index.

    For now this uses a plain HIndex; backends that need to emit slice
    operations can inspect ``index.value < 0`` to detect rest-slice.
    We store the start as a negative literal: ``-1`` means ``[0:]``,
    ``-2`` means ``[1:]``, etc.  This is a prototype convention.
    """
    from aster_lang.semantic import INT_TYPE, ListType

    return HIndex(
        obj=obj,
        index=HLit(value=-(start + 1), ty=INT_TYPE),  # sentinel: -(start+1)
        ty=ListType(UNKNOWN_TYPE),
    )


# ---------------------------------------------------------------------------
# Free-variable analysis for lambdas
# ---------------------------------------------------------------------------


def _free_names_lambda(lam: ast.LambdaExpr) -> set[str]:
    """Collect identifiers referenced in *lam* that are not bound by it."""
    defined: set[str] = {p.name for p in lam.params}
    used: set[str] = set()
    _walk_expr_free(lam.body if isinstance(lam.body, ast.Expr) else None, used)
    if isinstance(lam.body, list):
        for s in lam.body:
            _walk_stmt_free(s, defined, used)
    elif isinstance(lam.body, ast.Expr):
        _walk_expr_free(lam.body, used)
    return used - defined


def _walk_expr_free(expr: ast.Expr | None, used: set[str]) -> None:
    if expr is None:
        return
    if isinstance(expr, ast.Identifier):
        used.add(expr.name)
    elif isinstance(expr, ast.BorrowExpr | ast.ParenExpr):
        _walk_expr_free(
            expr.target if isinstance(expr, ast.BorrowExpr) else expr.expr,
            used,
        )
    elif isinstance(expr, ast.LambdaExpr):
        # Nested lambda: only its free variables escape.
        used.update(_free_names_lambda(expr))
    elif isinstance(expr, ast.BinaryExpr):
        _walk_expr_free(expr.left, used)
        _walk_expr_free(expr.right, used)
    elif isinstance(expr, ast.UnaryExpr):
        _walk_expr_free(expr.operand, used)
    elif isinstance(expr, ast.CallExpr):
        _walk_expr_free(expr.func, used)
        for a in expr.args:
            _walk_expr_free(a, used)
    elif isinstance(expr, ast.ListExpr | ast.TupleExpr):
        for e in expr.elements:
            _walk_expr_free(e, used)
    elif isinstance(expr, ast.RecordExpr):
        for f in expr.fields:
            _walk_expr_free(f.value, used)
    elif isinstance(expr, ast.MemberExpr):
        _walk_expr_free(expr.obj, used)
    elif isinstance(expr, ast.IndexExpr):
        _walk_expr_free(expr.obj, used)
        _walk_expr_free(expr.index, used)
    # Literals, QualifiedName, etc.: no identifiers to collect.


def _walk_stmt_free(stmt: ast.Stmt, defined: set[str], used: set[str]) -> None:
    if isinstance(stmt, ast.LetStmt):
        _walk_expr_free(stmt.initializer, used)
        defined.update(_pat_names(stmt.pattern))
    elif isinstance(stmt, ast.AssignStmt):
        _walk_expr_free(stmt.target, used)
        _walk_expr_free(stmt.value, used)
    elif isinstance(stmt, ast.ReturnStmt):
        _walk_expr_free(stmt.value, used)
    elif isinstance(stmt, ast.ExprStmt):
        _walk_expr_free(stmt.expr, used)
    elif isinstance(stmt, ast.IfStmt):
        _walk_expr_free(stmt.condition, used)
        for s in stmt.then_block:
            _walk_stmt_free(s, defined, used)
        if stmt.else_block:
            for s in stmt.else_block:
                _walk_stmt_free(s, defined, used)
    elif isinstance(stmt, ast.WhileStmt):
        _walk_expr_free(stmt.condition, used)
        for s in stmt.body:
            _walk_stmt_free(s, defined, used)
    elif isinstance(stmt, ast.ForStmt):
        defined.add(stmt.variable)
        _walk_expr_free(stmt.iterable, used)
        for s in stmt.body:
            _walk_stmt_free(s, defined, used)
    elif isinstance(stmt, ast.MatchStmt):
        _walk_expr_free(stmt.subject, used)
        for arm in stmt.arms:
            defined.update(_pat_names(arm.pattern))
            for s in arm.body:
                _walk_stmt_free(s, defined, used)


def _pat_names(pattern: ast.Pattern) -> set[str]:
    if isinstance(pattern, ast.BindingPattern | ast.RestPattern):
        return {pattern.name}
    if isinstance(pattern, ast.TuplePattern | ast.ListPattern):
        out: set[str] = set()
        for e in pattern.elements:
            out |= _pat_names(e)
        return out
    if isinstance(pattern, ast.RecordPattern):
        out = set()
        for f in pattern.fields:
            out |= _pat_names(f.pattern)
        return out
    if isinstance(pattern, ast.OrPattern):
        out = set()
        for alt in pattern.alternatives:
            out |= _pat_names(alt)
        return out
    return set()


# ---------------------------------------------------------------------------
# Debug dump
# ---------------------------------------------------------------------------


def dump_hir(module: ast.Module, analyzer: SemanticAnalyzer) -> str:
    """Return a human-readable debug rendering of the HIR for *module*.

    The output format is intentionally similar to the source language but
    annotates every expression with its inferred type as ``# Type``.
    """
    hir = lower_module(module, analyzer)
    lines: list[str] = []
    fmt = Formatter()

    def render_ty(ty: Type) -> str:
        return str(ty)

    def render_expr(e: HExpr) -> str:
        if isinstance(e, HLit):
            if e.value is None:
                return "nil"
            if isinstance(e.value, bool):
                return "true" if e.value else "false"
            if isinstance(e.value, str):
                escaped = e.value.replace("\\", "\\\\").replace('"', '\\"')
                return f'"{escaped}"'
            return str(e.value)
        if isinstance(e, HName):
            return e.name
        if isinstance(e, HBinOp):
            return f"{render_expr(e.left)} {e.op} {render_expr(e.right)}"
        if isinstance(e, HUnaryOp):
            return f"{e.op}{render_expr(e.operand)}"
        if isinstance(e, HBorrow):
            mut = "mut " if e.is_mutable else ""
            return f"&{mut}{render_expr(e.target)}"
        if isinstance(e, HCall):
            args = ", ".join(render_expr(a) for a in e.args)
            return f"{render_expr(e.func)}({args})"
        if isinstance(e, HIndex):
            return f"{render_expr(e.obj)}[{render_expr(e.index)}]"
        if isinstance(e, HMember):
            return f"{render_expr(e.obj)}.{e.member}"
        if isinstance(e, HList):
            elems = ", ".join(render_expr(el) for el in e.elements)
            return f"[{elems}]"
        if isinstance(e, HTuple):
            elems = ", ".join(render_expr(el) for el in e.elements)
            return f"({elems})"
        if isinstance(e, HRecord):
            fields = ", ".join(f"{name}: {render_expr(val)}" for name, val in e.fields)
            return "{" + fields + "}"
        if isinstance(e, HClosure):
            fvs = ", ".join(e.free_vars)
            return f"<closure {e.fn_id}[{fvs}]>"
        raise AssertionError(f"unhandled HExpr node: {type(e)}")

    def render_stmts(stmts: tuple[HStmt, ...], indent: str) -> None:
        for s in stmts:
            render_stmt(s, indent)

    def render_stmt(s: HStmt, indent: str) -> None:
        if isinstance(s, HLet):
            mut = "mut " if s.is_mutable else ""
            lines.append(f"{indent}{mut}{s.name} := {render_expr(s.init)}  # {render_ty(s.ty)}")
        elif isinstance(s, HAssign):
            lines.append(
                f"{indent}{render_expr(s.target)} <- {render_expr(s.value)}"
                f"  # {render_ty(s.value.ty)}"
            )
        elif isinstance(s, HReturn):
            if s.value is None:
                lines.append(f"{indent}return")
            else:
                lines.append(f"{indent}return {render_expr(s.value)}  # {render_ty(s.value.ty)}")
        elif isinstance(s, HExprStmt):
            lines.append(f"{indent}{render_expr(s.expr)}  # {render_ty(s.expr.ty)}")
        elif isinstance(s, HBreak):
            lines.append(f"{indent}break")
        elif isinstance(s, HContinue):
            lines.append(f"{indent}continue")
        elif isinstance(s, HIf):
            lines.append(f"{indent}if {render_expr(s.condition)}:")
            render_stmts(s.then_body, indent + "  ")
            if s.else_body:
                lines.append(f"{indent}else:")
                render_stmts(s.else_body, indent + "  ")
        elif isinstance(s, HWhile):
            lines.append(f"{indent}while {render_expr(s.condition)}:")
            render_stmts(s.body, indent + "  ")
        elif isinstance(s, HFor):
            lines.append(f"{indent}for {s.variable} in {render_expr(s.iterable)}:")
            render_stmts(s.body, indent + "  ")
        elif isinstance(s, HMatch):
            lines.append(f"{indent}match {render_expr(s.subject)}:")
            for arm in s.arms:
                pat_text = fmt._format_pattern(arm.pattern)
                lines.append(f"{indent}  {pat_text}:")
                render_stmts(arm.body, indent + "    ")

    def render_fn(fn: HFunction, prefix: str = "") -> None:
        params = ", ".join(
            f"{name}: {render_ty(ty)}" for name, ty in zip(fn.params, fn.param_types, strict=True)
        )
        ret = f" -> {render_ty(fn.return_type)}"
        efx = "".join(f" !{e}" for e in fn.effects)
        fvs = f" [free: {', '.join(fn.free_vars)}]" if fn.free_vars else ""
        lines.append(f"{prefix}fn {fn.name}({params}){ret}{efx}{fvs}:")
        render_stmts(fn.body, "  ")

    # Lifted lambdas first (they may be referenced by later functions).
    for lifted in hir.lifted_fns.values():
        render_fn(lifted, prefix="# lambda ")
        lines.append("")

    # Top-level declarations.
    for decl in hir.decls:
        if isinstance(decl, HFunction):
            render_fn(decl)
            lines.append("")
        elif isinstance(decl, HLetDecl):
            lines.append(f"{decl.name} := {render_expr(decl.init)}  # {render_ty(decl.ty)}")
        elif isinstance(decl, HImportDecl):
            lines.append(f"use {'.'.join(decl.module)}")
        elif isinstance(decl, HEffectDecl):
            lines.append(f"effect {decl.name}")
        elif isinstance(decl, HTypeAliasDecl):
            lines.append(f"typealias {decl.name}")

    return "\n".join(lines) + ("\n" if lines else "")
