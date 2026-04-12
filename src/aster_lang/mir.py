"""Mid-level Intermediate Representation (MIR) for the Aster language.

The MIR sits between the HIR and the code-generation backends.  It is
produced from the HIR by two desugaring passes:

  1. **Match desugaring** — ``HMatch`` is lowered into a sequential chain
     of ``MIf`` nodes.  Each arm becomes a condition expression that tests
     whether the subject matches the pattern, followed by binding lets and
     the arm body.  No decision-tree optimisation is attempted yet.

  2. **For-loop desugaring** — ``HFor(var, iterable, body)`` is lowered
     into a ``__iter`` temporary plus a ``MWhile`` guarded by a synthetic
     ``__iter_has_next`` call, with the loop variable bound via
     ``__iter_next`` at the top of the body.

Control-flow nodes ``MIf``, ``MWhile``, ``MBreak``, and ``MContinue`` are
preserved (they map 1-to-1 to the VM / transpiler).  There is no ``MMatch``
or ``MFor``.

Ownership lowering is a separate BACKLOG item; MIR is designed so that
drop/move/borrow annotations can be added as extra ``MStmt`` variants later
without restructuring the existing nodes.

Expression nodes are reused from the HIR (``HExpr`` and all ``H*`` expression
types) — no MIR-specific expression transforms are needed yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aster_lang import ast
from aster_lang.hir import (
    HBinOp,
    HCall,
    HExpr,
    HFunction,
    HLit,
    HModule,
    HName,
    HStmt,
)
from aster_lang.semantic import UNKNOWN_TYPE, Type

# ---------------------------------------------------------------------------
# MIR statement nodes
# (Expression nodes are reused from HIR — see module docstring.)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MLet:
    """Simple let binding: name := init."""

    name: str
    is_mutable: bool
    ty: Type
    init: HExpr


@dataclass(frozen=True)
class MAssign:
    """Assignment statement: target <- value."""

    target: HExpr
    value: HExpr


@dataclass(frozen=True)
class MReturn:
    """Return statement."""

    value: HExpr | None


@dataclass(frozen=True)
class MExprStmt:
    """Expression used as a statement."""

    expr: HExpr


@dataclass(frozen=True)
class MBreak:
    """Break statement."""


@dataclass(frozen=True)
class MContinue:
    """Continue statement."""


@dataclass(frozen=True)
class MIf:
    """If / else statement."""

    condition: HExpr
    then_body: tuple[MStmt, ...]
    else_body: tuple[MStmt, ...] | None


@dataclass(frozen=True)
class MWhile:
    """While loop."""

    condition: HExpr
    body: tuple[MStmt, ...]


# MStmt forward-reference resolved after all node classes are defined.
MStmt = MLet | MAssign | MReturn | MExprStmt | MBreak | MContinue | MIf | MWhile

# ---------------------------------------------------------------------------
# MIR declaration nodes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MFunction:
    """Function definition (including lifted lambdas carried from HIR)."""

    fn_id: str
    name: str
    params: tuple[str, ...]
    param_types: tuple[Type, ...]
    return_type: Type
    free_vars: tuple[str, ...]
    body: tuple[MStmt, ...]
    is_public: bool
    effects: tuple[str, ...]


@dataclass(frozen=True)
class MLetDecl:
    """Top-level let declaration."""

    name: str
    ty: Type
    is_mutable: bool
    is_public: bool
    init: HExpr


@dataclass(frozen=True)
class MImportDecl:
    """Import declaration."""

    module: tuple[str, ...]
    imports: tuple[str, ...] | None
    alias: str | None


@dataclass(frozen=True)
class MEffectDecl:
    """Effect declaration."""

    name: str
    is_public: bool


MTopLevel = MFunction | MLetDecl | MImportDecl | MEffectDecl


@dataclass(frozen=True)
class MModule:
    """A lowered MIR module.

    ``lifted_fns`` carries the lambda functions lifted during the HIR pass;
    they are also lowered to ``MFunction`` form here.
    """

    decls: tuple[MTopLevel, ...]
    lifted_fns: dict[str, MFunction] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Lowering pass: HIR → MIR
# ---------------------------------------------------------------------------


def lower_hir(hmod: HModule) -> MModule:
    """Lower a HIR module into MIR.

    This is the main entry point.  See the module docstring for the
    transformations performed.
    """
    lowerer = _MirLowerer()
    return lowerer.lower(hmod)


class _MirLowerer:
    """Internal worker that walks HIR and produces MIR."""

    def __init__(self) -> None:
        self._tmp_counter = 0

    def _fresh_tmp(self) -> str:
        self._tmp_counter += 1
        return f"__mir_tmp{self._tmp_counter}"

    # ------------------------------------------------------------------
    # Module
    # ------------------------------------------------------------------

    def lower(self, hmod: HModule) -> MModule:
        decls: list[MTopLevel] = []
        for hdecl in hmod.decls:
            mdecl = self._lower_decl(hdecl)
            if mdecl is not None:
                decls.append(mdecl)

        lifted: dict[str, MFunction] = {}
        for fn_id, hfn in hmod.lifted_fns.items():
            lifted[fn_id] = self._lower_hfunction(hfn)

        return MModule(decls=tuple(decls), lifted_fns=lifted)

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def _lower_decl(self, hdecl: object) -> MTopLevel | None:
        from aster_lang.hir import (
            HEffectDecl,
            HFunction,
            HImportDecl,
            HLetDecl,
            HTypeAliasDecl,
        )

        if isinstance(hdecl, HFunction):
            return self._lower_hfunction(hdecl)
        if isinstance(hdecl, HLetDecl):
            return MLetDecl(
                name=hdecl.name,
                ty=hdecl.ty,
                is_mutable=hdecl.is_mutable,
                is_public=hdecl.is_public,
                init=hdecl.init,
            )
        if isinstance(hdecl, HImportDecl):
            return MImportDecl(
                module=hdecl.module,
                imports=hdecl.imports,
                alias=hdecl.alias,
            )
        if isinstance(hdecl, HEffectDecl):
            return MEffectDecl(name=hdecl.name, is_public=hdecl.is_public)
        if isinstance(hdecl, HTypeAliasDecl):
            # Type aliases have no runtime representation — drop.
            return None
        return None  # unknown node type (future-proof)

    def _lower_hfunction(self, hfn: HFunction) -> MFunction:
        body = self._lower_stmts(hfn.body)
        return MFunction(
            fn_id=hfn.fn_id,
            name=hfn.name,
            params=hfn.params,
            param_types=hfn.param_types,
            return_type=hfn.return_type,
            free_vars=hfn.free_vars,
            body=body,
            is_public=hfn.is_public,
            effects=hfn.effects,
        )

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _lower_stmts(self, stmts: tuple[HStmt, ...]) -> tuple[MStmt, ...]:
        out: list[MStmt] = []
        for s in stmts:
            out.extend(self._lower_stmt(s))
        return tuple(out)

    def _lower_stmt(self, s: HStmt) -> list[MStmt]:
        from aster_lang.hir import (
            HAssign,
            HBreak,
            HContinue,
            HExprStmt,
            HFor,
            HIf,
            HLet,
            HMatch,
            HReturn,
            HWhile,
        )

        if isinstance(s, HLet):
            return [MLet(name=s.name, is_mutable=s.is_mutable, ty=s.ty, init=s.init)]
        if isinstance(s, HAssign):
            return [MAssign(target=s.target, value=s.value)]
        if isinstance(s, HReturn):
            return [MReturn(value=s.value)]
        if isinstance(s, HExprStmt):
            return [MExprStmt(expr=s.expr)]
        if isinstance(s, HBreak):
            return [MBreak()]
        if isinstance(s, HContinue):
            return [MContinue()]
        if isinstance(s, HIf):
            return [
                MIf(
                    condition=s.condition,
                    then_body=self._lower_stmts(s.then_body),
                    else_body=self._lower_stmts(s.else_body) if s.else_body is not None else None,
                )
            ]
        if isinstance(s, HWhile):
            return [MWhile(condition=s.condition, body=self._lower_stmts(s.body))]
        if isinstance(s, HFor):
            return self._desugar_for(s)
        if isinstance(s, HMatch):
            return self._desugar_match(s)
        raise AssertionError(f"unhandled HStmt node: {type(s)}")

    # ------------------------------------------------------------------
    # For-loop desugaring
    # ------------------------------------------------------------------

    def _desugar_for(self, s: object) -> list[MStmt]:
        from aster_lang.hir import HFor

        assert isinstance(s, HFor)
        iter_tmp = self._fresh_tmp()
        # __mir_tmpN := __iter_init(iterable)
        init_call = HCall(
            func=HName(name="__iter_init", ty=UNKNOWN_TYPE),
            args=(s.iterable,),
            ty=UNKNOWN_TYPE,
        )
        iter_let = MLet(name=iter_tmp, is_mutable=True, ty=UNKNOWN_TYPE, init=init_call)

        # has_next condition
        iter_ref = HName(name=iter_tmp, ty=UNKNOWN_TYPE)
        has_next = HCall(
            func=HName(name="__iter_has_next", ty=UNKNOWN_TYPE),
            args=(iter_ref,),
            ty=UNKNOWN_TYPE,
        )

        # body: variable := __iter_next(__mir_tmpN); ...original body...
        next_call = HCall(
            func=HName(name="__iter_next", ty=UNKNOWN_TYPE),
            args=(iter_ref,),
            ty=UNKNOWN_TYPE,
        )
        var_let = MLet(name=s.variable, is_mutable=False, ty=UNKNOWN_TYPE, init=next_call)
        loop_body: list[MStmt] = [var_let, *self._lower_stmts(s.body)]

        while_stmt = MWhile(condition=has_next, body=tuple(loop_body))
        return [iter_let, while_stmt]

    # ------------------------------------------------------------------
    # Match desugaring
    # ------------------------------------------------------------------

    def _desugar_match(self, s: object) -> list[MStmt]:
        from aster_lang.hir import HMatch

        assert isinstance(s, HMatch)

        # Bind the subject to a temporary so it is evaluated only once.
        subj_tmp = self._fresh_tmp()
        subj_let = MLet(name=subj_tmp, is_mutable=False, ty=s.subject.ty, init=s.subject)
        subj_ref = HName(name=subj_tmp, ty=s.subject.ty)

        # Build arms back-to-front so we can chain them as else-branches.
        chain: tuple[MStmt, ...] | None = None
        for arm in reversed(s.arms):
            bindings, cond = self._pattern_test(arm.pattern, subj_ref)
            body_stmts = list(bindings) + list(self._lower_stmts(arm.body))
            if cond is None:
                # Unconditional arm (wildcard or bare binding) — no MIf needed.
                chain = tuple(body_stmts)
            else:
                chain = (
                    MIf(
                        condition=cond,
                        then_body=tuple(body_stmts),
                        else_body=chain,
                    ),
                )

        result: list[MStmt] = [subj_let]
        if chain:
            result.extend(chain)
        return result

    def _pattern_test(
        self, pattern: ast.Pattern, subject: HExpr
    ) -> tuple[list[MLet], HExpr | None]:
        """Return (binding_lets, condition_expr_or_None).

        ``condition_expr_or_None`` is None when the pattern always matches
        (wildcard, bare binding).  Binding lets are emitted even for the
        unconditional cases.
        """
        if isinstance(pattern, ast.WildcardPattern):
            return [], None

        if isinstance(pattern, ast.BindingPattern):
            binding = MLet(name=pattern.name, is_mutable=False, ty=subject.ty, init=subject)
            return [binding], None

        if isinstance(pattern, ast.LiteralPattern):
            lit_val = self._literal_value(pattern.literal)
            lit_expr = HLit(value=lit_val, ty=subject.ty)
            eq_expr = HBinOp(op="==", left=subject, right=lit_expr, ty=UNKNOWN_TYPE)
            return [], eq_expr

        if isinstance(pattern, ast.OrPattern):
            # Combine alternatives with logical OR.  No bindings across
            # or-alternatives (the semantic analyser enforces parity).
            conds: list[HExpr] = []
            for alt in pattern.alternatives:
                _, alt_cond = self._pattern_test(alt, subject)
                if alt_cond is None:
                    # One unconditional alternative makes the whole Or unconditional.
                    return [], None
                conds.append(alt_cond)
            if not conds:
                return [], None
            combined: HExpr = conds[0]
            for c in conds[1:]:
                combined = HBinOp(op="or", left=combined, right=c, ty=UNKNOWN_TYPE)
            return [], combined

        if isinstance(pattern, ast.TuplePattern | ast.ListPattern):
            return self._pattern_test_sequence(pattern.elements, subject)

        if isinstance(pattern, ast.RecordPattern):
            return self._pattern_test_record(pattern, subject)

        if isinstance(pattern, ast.RestPattern):
            # Rest pattern at the top level (e.g. match xs: *tail: ...)
            binding = MLet(name=pattern.name, is_mutable=False, ty=subject.ty, init=subject)
            return [binding], None

        # Unknown pattern — treat as wildcard.
        return [], None

    def _pattern_test_sequence(
        self,
        elements: list[ast.Pattern],
        subject: HExpr,
    ) -> tuple[list[MLet], HExpr | None]:
        """Desugar a tuple/list pattern into index checks + recursive tests."""
        from aster_lang.hir import HIndex

        bindings: list[MLet] = []
        cond: HExpr | None = None
        rest_seen = False

        for i, elem in enumerate(elements):
            if isinstance(elem, ast.RestPattern):
                rest_seen = True
                # Bind subject[i:] to the rest name.
                # Use the negative-sentinel convention from HIR: index -(i+1)
                # signals "slice from i" to the backend.
                slice_idx = HLit(value=-(i + 1), ty=UNKNOWN_TYPE)
                slice_expr = HIndex(obj=subject, index=slice_idx, ty=UNKNOWN_TYPE)
                tmp = self._fresh_tmp()
                bindings.append(MLet(name=tmp, is_mutable=False, ty=UNKNOWN_TYPE, init=slice_expr))
                elem_bindings, elem_cond = self._pattern_test(
                    elem, HName(name=tmp, ty=UNKNOWN_TYPE)
                )
                bindings.extend(elem_bindings)
                cond = _and_cond(cond, elem_cond)
            else:
                idx_expr = HIndex(
                    obj=subject,
                    index=HLit(value=i, ty=UNKNOWN_TYPE),
                    ty=UNKNOWN_TYPE,
                )
                tmp = self._fresh_tmp()
                bindings.append(MLet(name=tmp, is_mutable=False, ty=UNKNOWN_TYPE, init=idx_expr))
                elem_bindings, elem_cond = self._pattern_test(
                    elem, HName(name=tmp, ty=UNKNOWN_TYPE)
                )
                bindings.extend(elem_bindings)
                cond = _and_cond(cond, elem_cond)

        # Arity check: len(subject) == len(elements) when no rest pattern.
        if not rest_seen:
            n = len(elements)
            n_lit = HLit(value=n, ty=UNKNOWN_TYPE)
            len_call = HCall(
                func=HName(name="__len", ty=UNKNOWN_TYPE),
                args=(subject,),
                ty=UNKNOWN_TYPE,
            )
            arity_cond: HExpr = HBinOp(op="==", left=len_call, right=n_lit, ty=UNKNOWN_TYPE)
            cond = _and_cond(arity_cond, cond)

        return bindings, cond

    def _pattern_test_record(
        self,
        pattern: ast.RecordPattern,
        subject: HExpr,
    ) -> tuple[list[MLet], HExpr | None]:
        """Desugar a record pattern into member accesses + recursive tests."""
        from aster_lang.hir import HMember

        bindings: list[MLet] = []
        cond: HExpr | None = None

        for rf in pattern.fields:
            member_expr = HMember(obj=subject, member=rf.name, ty=UNKNOWN_TYPE)
            tmp = self._fresh_tmp()
            bindings.append(MLet(name=tmp, is_mutable=False, ty=UNKNOWN_TYPE, init=member_expr))
            field_bindings, field_cond = self._pattern_test(
                rf.pattern, HName(name=tmp, ty=UNKNOWN_TYPE)
            )
            bindings.extend(field_bindings)
            cond = _and_cond(cond, field_cond)

        return bindings, cond

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _literal_value(
        lit: ast.IntegerLiteral | ast.StringLiteral | ast.BoolLiteral | ast.NilLiteral,
    ) -> int | str | bool | None:
        if isinstance(lit, ast.IntegerLiteral):
            return lit.value
        if isinstance(lit, ast.StringLiteral):
            return lit.value
        if isinstance(lit, ast.BoolLiteral):
            return lit.value
        return None  # NilLiteral


def _and_cond(left: HExpr | None, right: HExpr | None) -> HExpr | None:
    """Combine two optional conditions with logical AND."""
    if left is None:
        return right
    if right is None:
        return left
    return HBinOp(op="and", left=left, right=right, ty=UNKNOWN_TYPE)


# ---------------------------------------------------------------------------
# Debug dump
# ---------------------------------------------------------------------------


def dump_mir(mmod: MModule) -> str:
    """Return a human-readable representation of a MIR module."""
    lines: list[str] = []

    def render_ty(ty: Type) -> str:
        return str(ty)

    def render_expr(e: HExpr) -> str:
        from aster_lang.hir import (
            HBorrow,
            HClosure,
            HIndex,
            HList,
            HMember,
            HRecord,
            HTuple,
            HUnaryOp,
        )

        if isinstance(e, HLit):
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

    def render_stmts(stmts: tuple[MStmt, ...], indent: str) -> None:
        for s in stmts:
            render_stmt(s, indent)

    def render_stmt(s: MStmt, indent: str) -> None:
        if isinstance(s, MLet):
            mut = "mut " if s.is_mutable else ""
            init_text = render_expr(s.init)
            ty_text = render_ty(s.ty)
            lines.append(f"{indent}{mut}{s.name} := {init_text}  # {ty_text}")
        elif isinstance(s, MAssign):
            lines.append(f"{indent}{render_expr(s.target)} <- {render_expr(s.value)}")
        elif isinstance(s, MReturn):
            val = render_expr(s.value) if s.value is not None else "nil"
            ty_text = render_ty(s.value.ty) if s.value is not None else "Nil"
            lines.append(f"{indent}return {val}  # {ty_text}")
        elif isinstance(s, MExprStmt):
            lines.append(f"{indent}{render_expr(s.expr)}")
        elif isinstance(s, MBreak):
            lines.append(f"{indent}break")
        elif isinstance(s, MContinue):
            lines.append(f"{indent}continue")
        elif isinstance(s, MIf):
            lines.append(f"{indent}if {render_expr(s.condition)}:")
            render_stmts(s.then_body, indent + "  ")
            if s.else_body:
                lines.append(f"{indent}else:")
                render_stmts(s.else_body, indent + "  ")
        elif isinstance(s, MWhile):
            lines.append(f"{indent}while {render_expr(s.condition)}:")
            render_stmts(s.body, indent + "  ")
        else:
            raise AssertionError(f"unhandled MStmt node: {type(s)}")

    def render_fn(fn: MFunction, prefix: str = "") -> None:
        params = ", ".join(
            f"{name}: {render_ty(ty)}" for name, ty in zip(fn.params, fn.param_types, strict=True)
        )
        ret = f" -> {render_ty(fn.return_type)}"
        efx = "".join(f" !{e}" for e in fn.effects)
        fvs = f" [free: {', '.join(fn.free_vars)}]" if fn.free_vars else ""
        lines.append(f"{prefix}fn {fn.name}({params}){ret}{efx}{fvs}:")
        render_stmts(fn.body, "  ")
        lines.append("")

    for fn_id, fn in mmod.lifted_fns.items():
        lines.append(f"# lambda fn {fn_id}")
        render_fn(fn)

    for decl in mmod.decls:
        if isinstance(decl, MFunction):
            render_fn(decl)
        elif isinstance(decl, MLetDecl):
            mut = "mut " if decl.is_mutable else ""
            lines.append(f"{mut}{decl.name} := {render_expr(decl.init)}  # {render_ty(decl.ty)}")
            lines.append("")
        elif isinstance(decl, MImportDecl):
            pass  # imports are resolved — nothing to emit
        elif isinstance(decl, MEffectDecl):
            pub = "pub " if decl.is_public else ""
            lines.append(f"{pub}effect {decl.name}")
            lines.append("")

    return "\n".join(lines)
