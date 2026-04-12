"""Documentation generator for Aster source files.

Extracts ``##``-prefixed doc comments from public declarations and emits
Markdown documentation.

Doc comment syntax::

    ## Single-line doc comment.
    ## Continuation lines are joined with a space.
    pub fn my_function(x: Int) -> Int:
        ...

    ## Multi-paragraph docs are separated by a blank ## line.
    ##
    ## This becomes a new paragraph.
    pub fn another():
        ...

Only ``pub`` top-level declarations are included:
  - ``pub fn``  — functions
  - ``pub typealias``  — type aliases
  - ``pub mut?`` bindings  — top-level constants/variables

Usage (CLI)::

    aster doc <path> [--out-dir DIR]
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from aster_lang import ast
from aster_lang.formatter import format_type_expr
from aster_lang.parser import parse_module


@dataclass
class DocItem:
    """A single documented public declaration."""

    kind: str  # "fn", "typealias", "binding"
    name: str
    signature: str  # human-readable signature line
    doc: str  # extracted doc text (empty string if none)


@dataclass
class ModuleDoc:
    """Documentation extracted from one source module."""

    module_name: str
    items: list[DocItem] = field(default_factory=list)


def _extract_doc(leading_comments: list[str]) -> str:
    """Convert a list of leading comment strings into doc text.

    Only ``##``-prefixed comments are treated as doc comments; regular
    ``#`` comments are ignored.  Consecutive ``##`` lines are joined;
    a bare ``##`` (no text after the prefix) becomes a paragraph break.
    """
    doc_lines: list[str] = []
    for raw in leading_comments:
        stripped = raw.strip()
        if stripped.startswith("##"):
            content = stripped[2:].strip()
            doc_lines.append(content)
        # Regular # comments are skipped silently.
    if not doc_lines:
        return ""
    # Join runs, turning bare lines into paragraph breaks.
    paragraphs: list[list[str]] = [[]]
    for line in doc_lines:
        if line == "":
            if paragraphs[-1]:
                paragraphs.append([])
        else:
            paragraphs[-1].append(line)
    return "\n\n".join(" ".join(p) for p in paragraphs if p)


def _fn_signature(decl: ast.FunctionDecl) -> str:
    """Format a function declaration as a one-line signature."""
    params = ", ".join(
        f"{p.name}: {format_type_expr(p.type_annotation)}" if p.type_annotation else p.name
        for p in decl.params
    )
    ret = f" -> {format_type_expr(decl.return_type)}" if decl.return_type else ""
    pub = "pub " if decl.is_public else ""
    return f"{pub}fn {decl.name}({params}){ret}"


def _typealias_signature(decl: ast.TypeAliasDecl) -> str:
    pub = "pub " if decl.is_public else ""
    return f"{pub}typealias {decl.name} = {format_type_expr(decl.type_expr)}"


def _binding_signature(decl: ast.LetDecl) -> str:
    pub = "pub " if decl.is_public else ""
    mut = "mut " if decl.is_mutable else ""
    ann = f": {format_type_expr(decl.type_annotation)}" if decl.type_annotation else ""
    return f"{pub}{mut}{decl.name}{ann}"


def extract_module_doc(source: str, module_name: str) -> ModuleDoc:
    """Parse *source* and extract documentation for all public declarations."""
    module = parse_module(source)
    doc = ModuleDoc(module_name=module_name)

    for decl in module.declarations:
        if isinstance(decl, ast.FunctionDecl) and decl.is_public:
            doc.items.append(
                DocItem(
                    kind="fn",
                    name=decl.name,
                    signature=_fn_signature(decl),
                    doc=_extract_doc(decl.leading_comments),
                )
            )
        elif isinstance(decl, ast.TypeAliasDecl) and decl.is_public:
            doc.items.append(
                DocItem(
                    kind="typealias",
                    name=decl.name,
                    signature=_typealias_signature(decl),
                    doc=_extract_doc(decl.leading_comments),
                )
            )
        elif isinstance(decl, ast.LetDecl) and decl.is_public:
            doc.items.append(
                DocItem(
                    kind="binding",
                    name=decl.name,
                    signature=_binding_signature(decl),
                    doc=_extract_doc(decl.leading_comments),
                )
            )

    return doc


def render_markdown(doc: ModuleDoc) -> str:
    """Render a ModuleDoc as a Markdown string."""
    lines: list[str] = [f"# Module `{doc.module_name}`", ""]

    if not doc.items:
        lines.append("*No public declarations.*")
        return "\n".join(lines)

    # Group by kind
    fns = [i for i in doc.items if i.kind == "fn"]
    aliases = [i for i in doc.items if i.kind == "typealias"]
    bindings = [i for i in doc.items if i.kind == "binding"]

    def _render_section(title: str, items: list[DocItem]) -> None:
        if not items:
            return
        lines.append(f"## {title}")
        lines.append("")
        for item in items:
            lines.append(f"### `{item.name}`")
            lines.append("")
            lines.append("```aster")
            lines.append(item.signature)
            lines.append("```")
            lines.append("")
            if item.doc:
                lines.append(item.doc)
                lines.append("")

    _render_section("Functions", fns)
    _render_section("Type Aliases", aliases)
    _render_section("Bindings", bindings)

    return "\n".join(lines)


def generate_docs(
    source_path: Path,
    *,
    out_dir: Path | None = None,
) -> Path:
    """Generate Markdown documentation for *source_path*.

    Returns the path of the written ``.md`` file.
    """
    source = source_path.read_text(encoding="utf-8")
    module_name = source_path.stem
    doc = extract_module_doc(source, module_name)
    md = render_markdown(doc)

    dest_dir = out_dir or source_path.parent / "__aster_docs__"
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest_dir / f"{module_name}.md"
    out_path.write_text(md, encoding="utf-8")
    return out_path
