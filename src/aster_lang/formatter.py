"""Formatter for the Aster language.

Produces canonical, idempotent Aster source from an AST.
Formatting rules:
  - 4-space indentation
  - Single blank line between top-level declarations
  - Spaces around binary operators
  - No trailing whitespace
  - Trailing newline
"""

from __future__ import annotations

from aster_lang import ast
from aster_lang.parser import parse_module

INDENT = "    "


class Formatter:
    """Walk the AST and emit canonical Aster source."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._indent_level: int = 0

    # ------------------------------------------------------------------
    # Internal helpers

    def _emit(self, text: str) -> None:
        prefix = INDENT * self._indent_level
        self._lines.append(prefix + text)

    def _blank(self) -> None:
        self._lines.append("")

    def _indent(self) -> None:
        self._indent_level += 1

    def _dedent(self) -> None:
        self._indent_level -= 1

    # ------------------------------------------------------------------
    # Public entry point

    def format_module(self, module: ast.Module) -> str:
        for i, decl in enumerate(module.declarations):
            if i > 0:
                self._blank()
            self._format_decl(decl)
        result = "\n".join(self._lines)
        return result.rstrip() + "\n"

    # ------------------------------------------------------------------
    # Declarations

    def _emit_leading_comments(self, node: ast.Node) -> None:
        """Emit any leading comments attached to *node*."""
        for comment in node.leading_comments:
            self._emit(comment)

    def _apply_trailing_comment(self, node: ast.Node) -> None:
        """Append a trailing comment to the last emitted line, if any."""
        if node.trailing_comment and self._lines:
            self._lines[-1] = self._lines[-1] + "  " + node.trailing_comment

    def _format_decl(self, decl: ast.Decl) -> None:
        self._emit_leading_comments(decl)
        if isinstance(decl, ast.FunctionDecl):
            self._format_function_decl(decl)
        elif isinstance(decl, ast.LetDecl):
            self._format_let_decl(decl)
        elif isinstance(decl, ast.ImportDecl):
            self._format_import_decl(decl)
        elif isinstance(decl, ast.TypeAliasDecl):
            self._format_type_alias_decl(decl)
        elif isinstance(decl, ast.TraitDecl):
            self._format_trait_decl(decl)
        elif isinstance(decl, ast.ImplDecl):
            self._format_impl_decl(decl)
        else:
            self._emit(f"# (unknown decl: {type(decl).__name__})")
        self._apply_trailing_comment(decl)

    def _format_function_decl(self, decl: ast.FunctionDecl) -> None:
        pub = "pub " if decl.is_public else ""
        tparams = self._format_type_params(decl.type_params)
        params = ", ".join(self._format_param(p) for p in decl.params)
        ret = f" -> {self._format_type(decl.return_type)}" if decl.return_type else ""
        self._emit(f"{pub}fn {decl.name}{tparams}({params}){ret}:")
        self._indent()
        for stmt in decl.body:
            self._format_stmt(stmt)
        self._dedent()

    def _format_param(self, param: ast.ParamDecl) -> str:
        if param.type_annotation:
            return f"{param.name}: {self._format_type(param.type_annotation)}"
        return param.name

    def _format_let_decl(self, decl: ast.LetDecl) -> None:
        pub = "pub " if decl.is_public else ""
        mut = "mut " if decl.is_mutable else ""
        ann = f": {self._format_type(decl.type_annotation)}" if decl.type_annotation else ""
        val = self._format_expr(decl.initializer)
        self._emit(f"{pub}{mut}{decl.name}{ann} := {val}")

    def _format_import_decl(self, decl: ast.ImportDecl) -> None:
        module_str = ".".join(decl.module.parts)
        if decl.alias:
            self._emit(f"use {module_str} as {decl.alias}")
        elif decl.imports:
            names = ", ".join(decl.imports)
            self._emit(f"use {module_str}: {names}")
        else:
            self._emit(f"use {module_str}")

    def _format_type_alias_decl(self, decl: ast.TypeAliasDecl) -> None:
        pub = "pub " if decl.is_public else ""
        params = self._format_type_params(decl.type_params)
        type_str = self._format_type(decl.type_expr)
        self._emit(f"{pub}typealias {decl.name}{params} = {type_str}")

    def _format_trait_decl(self, decl: ast.TraitDecl) -> None:
        pub = "pub " if decl.is_public else ""
        params = self._format_type_params(decl.type_params)
        self._emit(f"{pub}trait {decl.name}{params}:")
        self._indent()
        for m in decl.members:
            self._emit(self._format_function_sig(m))
        self._dedent()

    def _format_function_sig(self, sig: ast.FunctionSig) -> str:
        params = ", ".join(self._format_param(p) for p in sig.params)
        ret = f" -> {self._format_type(sig.return_type)}" if sig.return_type else ""
        return f"fn {sig.name}({params}){ret}"

    def _format_type_params(self, params: list[ast.TypeParam]) -> str:
        if not params:
            return ""
        parts: list[str] = []
        for p in params:
            if p.bounds:
                bounds = " + ".join(self._format_type(b) for b in p.bounds)
                parts.append(f"{p.name}: {bounds}")
            else:
                parts.append(p.name)
        return f"[{', '.join(parts)}]"

    def _format_impl_decl(self, decl: ast.ImplDecl) -> None:
        head = "impl "
        if decl.trait is None:
            head += self._format_type(decl.target)
        else:
            head += f"{self._format_type(decl.trait)} for {self._format_type(decl.target)}"
        self._emit(f"{head}:")
        self._indent()
        for m in decl.members:
            self._format_function_decl(m)
        self._dedent()

    # ------------------------------------------------------------------
    # Statements

    def _format_stmt(self, stmt: ast.Stmt) -> None:
        self._emit_leading_comments(stmt)
        self._format_stmt_inner(stmt)
        self._apply_trailing_comment(stmt)

    def _format_stmt_inner(self, stmt: ast.Stmt) -> None:
        if isinstance(stmt, ast.LetStmt):
            mut = "mut " if stmt.is_mutable else ""
            ann = f": {self._format_type(stmt.type_annotation)}" if stmt.type_annotation else ""
            val = self._format_expr(stmt.initializer)
            self._emit(f"{mut}{self._format_pattern(stmt.pattern)}{ann} := {val}")
        elif isinstance(stmt, ast.AssignStmt):
            target = self._format_expr(stmt.target)
            val = self._format_expr(stmt.value)
            self._emit(f"{target} <- {val}")
        elif isinstance(stmt, ast.ReturnStmt):
            if stmt.value is not None:
                self._emit(f"return {self._format_expr(stmt.value)}")
            else:
                self._emit("return")
        elif isinstance(stmt, ast.IfStmt):
            self._format_if_stmt(stmt)
        elif isinstance(stmt, ast.WhileStmt):
            self._emit(f"while {self._format_expr(stmt.condition)}:")
            self._indent()
            for s in stmt.body:
                self._format_stmt(s)
            self._dedent()
        elif isinstance(stmt, ast.ForStmt):
            iterable = self._format_expr(stmt.iterable)
            self._emit(f"for {stmt.variable} in {iterable}:")
            self._indent()
            for s in stmt.body:
                self._format_stmt(s)
            self._dedent()
        elif isinstance(stmt, ast.BreakStmt):
            self._emit("break")
        elif isinstance(stmt, ast.ContinueStmt):
            self._emit("continue")
        elif isinstance(stmt, ast.MatchStmt):
            self._format_match_stmt(stmt)
        elif isinstance(stmt, ast.ExprStmt):
            self._emit(self._format_expr(stmt.expr))
        else:
            self._emit(f"# (unknown stmt: {type(stmt).__name__})")

    def _format_match_stmt(self, stmt: ast.MatchStmt) -> None:
        self._emit(f"match {self._format_expr(stmt.subject)}:")
        self._indent()
        for arm in stmt.arms:
            self._emit_leading_comments(arm)
            pat = self._format_pattern(arm.pattern)
            # Single inline ExprStmt arm → keep on one line
            if len(arm.body) == 1 and isinstance(arm.body[0], ast.ExprStmt):
                val = self._format_expr(arm.body[0].expr)
                self._emit(f"{pat}: {val}")
            else:
                self._emit(f"{pat}:")
                self._indent()
                for s in arm.body:
                    self._format_stmt(s)
                self._dedent()
            self._apply_trailing_comment(arm)
        self._dedent()

    def _format_pattern(self, pattern: ast.Pattern) -> str:
        if isinstance(pattern, ast.WildcardPattern):
            return "_"
        if isinstance(pattern, ast.BindingPattern):
            return pattern.name
        if isinstance(pattern, ast.LiteralPattern):
            return self._format_expr(pattern.literal)
        if isinstance(pattern, ast.OrPattern):
            return " | ".join(self._format_pattern(option) for option in pattern.alternatives)
        if isinstance(pattern, ast.RestPattern):
            return f"*{pattern.name}"
        if isinstance(pattern, ast.TuplePattern):
            inner = ", ".join(self._format_pattern(element) for element in pattern.elements)
            return f"({inner})"
        if isinstance(pattern, ast.ListPattern):
            inner = ", ".join(self._format_pattern(element) for element in pattern.elements)
            return f"[{inner}]"
        if isinstance(pattern, ast.RecordPattern):
            fields = []
            for field in pattern.fields:
                if (
                    isinstance(field.pattern, ast.BindingPattern)
                    and field.pattern.name == field.name
                ):
                    fields.append(field.name)
                else:
                    fields.append(f"{field.name}: {self._format_pattern(field.pattern)}")
            return "{" + ", ".join(fields) + "}"
        return "(# unknown pattern #)"

    def _format_if_stmt(self, stmt: ast.IfStmt) -> None:
        self._emit(f"if {self._format_expr(stmt.condition)}:")
        self._indent()
        for s in stmt.then_block:
            self._format_stmt(s)
        self._dedent()
        if stmt.else_block:
            # Check for else-if chaining
            if len(stmt.else_block) == 1 and isinstance(stmt.else_block[0], ast.IfStmt):
                nested = stmt.else_block[0]
                self._emit(f"else if {self._format_expr(nested.condition)}:")
                self._indent()
                for s in nested.then_block:
                    self._format_stmt(s)
                self._dedent()
                # Recurse for further chaining
                if nested.else_block:
                    self._emit("else:")
                    self._indent()
                    for s in nested.else_block:
                        self._format_stmt(s)
                    self._dedent()
            else:
                self._emit("else:")
                self._indent()
                for s in stmt.else_block:
                    self._format_stmt(s)
                self._dedent()

    # ------------------------------------------------------------------
    # Expressions

    def _format_expr(self, expr: ast.Expr) -> str:
        if isinstance(expr, ast.IntegerLiteral):
            return str(expr.value)
        if isinstance(expr, ast.StringLiteral):
            escaped = (
                expr.value.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
                .replace("\t", "\\t")
            )
            return f'"{escaped}"'
        if isinstance(expr, ast.BoolLiteral):
            return "true" if expr.value else "false"
        if isinstance(expr, ast.NilLiteral):
            return "nil"
        if isinstance(expr, ast.Identifier):
            return expr.name
        if isinstance(expr, ast.QualifiedName):
            return ".".join(expr.parts)
        if isinstance(expr, ast.BinaryExpr):
            left = self._format_expr_with_parens(expr.left, expr.operator)
            right = self._format_expr_with_parens(expr.right, expr.operator)
            return f"{left} {expr.operator} {right}"
        if isinstance(expr, ast.UnaryExpr):
            operand = self._format_expr(expr.operand)
            if expr.operator == "not":
                return f"not {operand}"
            return f"{expr.operator}{operand}"
        if isinstance(expr, ast.BorrowExpr):
            mut = "mut " if expr.is_mutable else ""
            return f"&{mut}{self._format_expr(expr.target)}"
        if isinstance(expr, ast.CallExpr):
            func = self._format_expr(expr.func)
            args = ", ".join(self._format_expr(a) for a in expr.args)
            return f"{func}({args})"
        if isinstance(expr, ast.IndexExpr):
            obj = self._format_expr(expr.obj)
            idx = self._format_expr(expr.index)
            return f"{obj}[{idx}]"
        if isinstance(expr, ast.MemberExpr):
            obj = self._format_expr(expr.obj)
            return f"{obj}.{expr.member}"
        if isinstance(expr, ast.TupleExpr):
            elements = ", ".join(self._format_expr(e) for e in expr.elements)
            return f"({elements})"
        if isinstance(expr, ast.ListExpr):
            elements = ", ".join(self._format_expr(e) for e in expr.elements)
            return f"[{elements}]"
        if isinstance(expr, ast.RecordExpr):
            fields = ", ".join(f"{f.name}: {self._format_expr(f.value)}" for f in expr.fields)
            return "{" + fields + "}"
        if isinstance(expr, ast.ParenExpr):
            return f"({self._format_expr(expr.expr)})"
        if isinstance(expr, ast.LambdaExpr):
            return self._format_lambda(expr)
        return f"(# unknown expr: {type(expr).__name__} #)"

    # Operator precedence for parenthesisation
    _PRECEDENCE: dict[str, int] = {
        "or": 1,
        "and": 2,
        "|": 3,
        "^": 4,
        "&": 5,
        "==": 6,
        "!=": 6,
        "<": 6,
        ">": 6,
        "<=": 6,
        ">=": 6,
        "<<": 7,
        ">>": 7,
        "+": 8,
        "-": 8,
        "*": 9,
        "/": 9,
        "%": 9,
        "**": 7,
    }

    def _prec(self, op: str) -> int:
        return self._PRECEDENCE.get(op, 0)

    def _format_expr_with_parens(self, expr: ast.Expr, parent_op: str) -> str:
        """Format expr, adding parens if its precedence is lower than parent_op."""
        if isinstance(expr, ast.BinaryExpr):
            child_prec = self._prec(expr.operator)
            parent_prec = self._prec(parent_op)
            formatted = self._format_expr(expr)
            if child_prec < parent_prec:
                return f"({formatted})"
            return formatted
        return self._format_expr(expr)

    def _format_lambda(self, expr: ast.LambdaExpr) -> str:
        params = ", ".join(
            f"{p.name}: {self._format_type(p.type_annotation)}" if p.type_annotation else p.name
            for p in expr.params
        )
        if isinstance(expr.body, list):
            # Multi-statement body - not expressible inline; emit a placeholder
            return f"({params}) -> ..."
        return f"({params}) -> {self._format_expr(expr.body)}"

    # ------------------------------------------------------------------
    # Type expressions

    def _format_type(self, type_expr: ast.TypeExpr) -> str:
        if isinstance(type_expr, ast.SimpleType):
            name = ".".join(type_expr.name.parts)
            if type_expr.type_args:
                args = ", ".join(self._format_type(t) for t in type_expr.type_args)
                return f"{name}[{args}]"
            return name
        if isinstance(type_expr, ast.FunctionType):
            params = ", ".join(self._format_type(t) for t in type_expr.param_types)
            ret = self._format_type(type_expr.return_type)
            return f"Fn({params}) -> {ret}"
        if isinstance(type_expr, ast.BorrowTypeExpr):
            inner = self._format_type(type_expr.inner)
            return f"&mut {inner}" if type_expr.is_mutable else f"&{inner}"
        if isinstance(type_expr, ast.PointerTypeExpr):
            inner = self._format_type(type_expr.inner)
            return f"*{type_expr.pointer_kind} {inner}"
        return f"(# unknown type: {type(type_expr).__name__} #)"


def format_source(source: str) -> str:
    """Parse and reformat Aster source code into canonical form."""
    module = parse_module(source)
    return Formatter().format_module(module)
