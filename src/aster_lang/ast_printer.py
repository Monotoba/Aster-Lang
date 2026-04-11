"""Pretty-printer for Aster AST nodes.

Produces an indented text tree suitable for debugging parser output.

Example output::

    Module
      FunctionDecl name='sum_to'
        ParamDecl name='n'
          SimpleType 'Int'
        SimpleType 'Int'          # return type
        LetStmt mut
          BindingPattern 'total'
          IntegerLiteral 0
        WhileStmt
          BinaryExpr '<='
            Identifier 'i'
            Identifier 'n'
          ...
"""

from __future__ import annotations

import dataclasses

from aster_lang import ast


def dump(node: ast.Node, _depth: int = 0) -> str:
    """Return an indented text representation of *node* and its children."""
    lines: list[str] = []
    _collect(node, _depth, lines)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_INDENT = "  "


def _collect(node: ast.Node, depth: int, lines: list[str]) -> None:
    """Append lines for *node* at the given *depth* into *lines*."""
    indent = _INDENT * depth
    header, children = _describe(node)
    lines.append(indent + header)
    for child in children:
        _collect(child, depth + 1, lines)


def _describe(node: ast.Node) -> tuple[str, list[ast.Node]]:
    """Return (header_string, child_nodes) for *node*."""
    # Special-case nodes with a compact natural representation.
    if isinstance(node, ast.QualifiedName):
        return f"QualifiedName '{node}'", []
    if isinstance(node, ast.SimpleType):
        base = f"SimpleType '{node.name}'"
        children: list[ast.Node] = list(node.type_args)
        return base, children
    if isinstance(node, ast.FunctionType):
        return "FunctionType", [*node.param_types, node.return_type]

    # Generic walk: pull scalar fields into the header, node fields into children.
    node_type = type(node).__name__
    inline: list[str] = []
    children = []

    try:
        fields = dataclasses.fields(node)
    except TypeError:
        return node_type, []

    for f in fields:
        val = getattr(node, f.name)
        _render_field(f.name, val, inline, children)

    header = node_type
    if inline:
        header += " " + " ".join(inline)
    return header, children


def _render_field(
    name: str,
    val: object,
    inline: list[str],
    children: list[ast.Node],
) -> None:
    """Dispatch a single field value into inline tokens or child nodes."""
    if val is None:
        return
    if isinstance(val, bool):
        # Only show flags when they are True to reduce noise.
        if val:
            inline.append(name)
        return
    if isinstance(val, int):
        inline.append(repr(val))
        return
    if isinstance(val, str):
        inline.append(repr(val))
        return
    if isinstance(val, ast.Node):
        children.append(val)
        return
    if isinstance(val, list):
        if not val:
            return
        if all(isinstance(v, str) for v in val):
            # Compact list-of-strings (e.g. ImportDecl.imports, type_params)
            inline.append(repr(val))
            return
        for item in val:
            if isinstance(item, ast.Node):
                children.append(item)
        return
