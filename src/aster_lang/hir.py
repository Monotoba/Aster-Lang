from __future__ import annotations

from dataclasses import dataclass

from aster_lang import ast
from aster_lang.formatter import Formatter
from aster_lang.semantic import UNKNOWN_TYPE, SemanticAnalyzer, Type


@dataclass(slots=True, frozen=True)
class HExpr:
    """A typed expression node suitable for lowering to backends."""

    expr: ast.Expr
    ty: Type


@dataclass(slots=True, frozen=True)
class HStmt:
    """A statement with typed expression children."""

    stmt: ast.Stmt
    exprs: tuple[HExpr, ...]


@dataclass(slots=True, frozen=True)
class HDecl:
    """A declaration with typed expression children."""

    decl: ast.Decl
    stmts: tuple[HStmt, ...]


@dataclass(slots=True, frozen=True)
class HModule:
    """A typed module (very small initial HIR)."""

    decls: tuple[HDecl, ...]


def lower_module(module: ast.Module, analyzer: SemanticAnalyzer) -> HModule:
    """Lower an AST module into a tiny typed HIR.

    This is intentionally minimal: it reuses AST nodes but attaches the inferred
    type of each expression as computed during semantic analysis.
    """

    def ty_of(e: ast.Expr) -> Type:
        return analyzer.expr_types.get(id(e), UNKNOWN_TYPE)

    def lower_expr(e: ast.Expr) -> HExpr:
        return HExpr(expr=e, ty=ty_of(e))

    def collect_stmt_exprs(s: ast.Stmt) -> tuple[HExpr, ...]:
        if isinstance(s, ast.LetStmt):
            return (lower_expr(s.initializer),)
        if isinstance(s, ast.AssignStmt):
            return (lower_expr(s.target), lower_expr(s.value))
        if isinstance(s, ast.ReturnStmt):
            return (lower_expr(s.value),) if s.value is not None else ()
        if isinstance(s, ast.ExprStmt):
            return (lower_expr(s.expr),)
        if isinstance(s, ast.IfStmt):
            out: list[HExpr] = [lower_expr(s.condition)]
            for inner in s.then_block:
                out.extend(collect_stmt_exprs(inner))
            if s.else_block:
                for inner in s.else_block:
                    out.extend(collect_stmt_exprs(inner))
            return tuple(out)
        if isinstance(s, ast.WhileStmt):
            out = [lower_expr(s.condition)]
            for inner in s.body:
                out.extend(collect_stmt_exprs(inner))
            return tuple(out)
        if isinstance(s, ast.ForStmt):
            out = [lower_expr(s.iterable)]
            for inner in s.body:
                out.extend(collect_stmt_exprs(inner))
            return tuple(out)
        if isinstance(s, ast.MatchStmt):
            out = [lower_expr(s.subject)]
            for arm in s.arms:
                for inner in arm.body:
                    out.extend(collect_stmt_exprs(inner))
            return tuple(out)
        return ()

    decls: list[HDecl] = []
    for d in module.declarations:
        stmts: list[HStmt] = []
        if isinstance(d, ast.FunctionDecl):
            for s in d.body:
                stmts.append(HStmt(stmt=s, exprs=collect_stmt_exprs(s)))
        elif isinstance(d, ast.LetDecl):
            stmts.append(
                HStmt(
                    stmt=ast.ExprStmt(expr=d.initializer),
                    exprs=(lower_expr(d.initializer),),
                )
            )
        decls.append(HDecl(decl=d, stmts=tuple(stmts)))

    return HModule(decls=tuple(decls))


def dump_hir(module: ast.Module, analyzer: SemanticAnalyzer) -> str:
    """Debug string for the current HIR."""
    fmt = Formatter()
    hir = lower_module(module, analyzer)

    def fmt_expr(e: ast.Expr) -> str:
        return fmt._format_expr(e)  # intentionally reusing formatter logic

    def fmt_pat(p: ast.Pattern) -> str:
        return fmt._format_pattern(p)

    lines: list[str] = []
    for d in hir.decls:
        decl = d.decl
        if isinstance(decl, ast.FunctionDecl):
            params = []
            for p in decl.params:
                ann = f": {fmt._format_type(p.type_annotation)}" if p.type_annotation else ""
                params.append(f"{p.name}{ann}")
            ret = f" -> {fmt._format_type(decl.return_type)}" if decl.return_type else ""
            lines.append(f"fn {decl.name}({', '.join(params)}){ret}:")
            for s in d.stmts:
                stmt = s.stmt
                if isinstance(stmt, ast.LetStmt):
                    mut = "mut " if stmt.is_mutable else ""
                    ann = (
                        f": {fmt._format_type(stmt.type_annotation)}"
                        if stmt.type_annotation
                        else ""
                    )
                    lines.append(
                        f"  {mut}{fmt_pat(stmt.pattern)}{ann} := {fmt_expr(stmt.initializer)}"
                        f"  # {analyzer.expr_types.get(id(stmt.initializer), UNKNOWN_TYPE)}"
                    )
                elif isinstance(stmt, ast.AssignStmt):
                    lines.append(
                        f"  {fmt_expr(stmt.target)} <- {fmt_expr(stmt.value)}"
                        f"  # {analyzer.expr_types.get(id(stmt.value), UNKNOWN_TYPE)}"
                    )
                elif isinstance(stmt, ast.ReturnStmt):
                    if stmt.value is None:
                        lines.append("  return")
                    else:
                        lines.append(
                            f"  return {fmt_expr(stmt.value)}"
                            f"  # {analyzer.expr_types.get(id(stmt.value), UNKNOWN_TYPE)}"
                        )
                elif isinstance(stmt, ast.ExprStmt):
                    lines.append(
                        f"  {fmt_expr(stmt.expr)}"
                        f"  # {analyzer.expr_types.get(id(stmt.expr), UNKNOWN_TYPE)}"
                    )
                else:
                    # For now, show a basic formatted line without deep typing.
                    lines.append(f"  (# {type(stmt).__name__} #)")
            continue

        if isinstance(decl, ast.LetDecl):
            ann = f": {fmt._format_type(decl.type_annotation)}" if decl.type_annotation else ""
            lines.append(
                f"{decl.name}{ann} := {fmt_expr(decl.initializer)}"
                f"  # {analyzer.expr_types.get(id(decl.initializer), UNKNOWN_TYPE)}"
            )
            continue

        if isinstance(decl, ast.ImportDecl):
            lines.append(f"use {'.'.join(decl.module.parts)}")
            continue

        if isinstance(decl, ast.TypeAliasDecl):
            lines.append(f"typealias {decl.name} = {fmt._format_type(decl.type_expr)}")
            continue

        lines.append(f"(# {type(decl).__name__} #)")

    return "\n".join(lines) + ("\n" if lines else "")
