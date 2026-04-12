"""Tests for the Aster documentation generator."""

from __future__ import annotations

from pathlib import Path

from aster_lang.cli import main
from aster_lang.doc_gen import (
    ModuleDoc,
    extract_module_doc,
    generate_docs,
    render_markdown,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_PUB_FN = """\
## Add two integers together.
pub fn add(a: Int, b: Int) -> Int:
    return a + b
"""

_PUB_TYPEALIAS = """\
## A list of integers.
pub typealias IntList = List[Int]
"""

_PUB_BINDING = """\
## The answer to everything.
pub ANSWER: Int := 42
"""

_PRIVATE_ONLY = """\
fn helper():
    pass
"""

_NO_DOC_COMMENT = """\
pub fn no_doc() -> Int:
    return 0
"""

_MULTI_PARAGRAPH = """\
## First paragraph.
##
## Second paragraph.
pub fn documented():
    pass
"""

_MIXED_COMMENTS = """\
# Regular comment — ignored.
## Doc comment kept.
pub fn mixed():
    pass
"""


# ---------------------------------------------------------------------------
# extract_module_doc
# ---------------------------------------------------------------------------


class TestExtractModuleDoc:
    def test_extracts_pub_fn(self) -> None:
        doc = extract_module_doc(_PUB_FN, "math")
        assert len(doc.items) == 1
        item = doc.items[0]
        assert item.kind == "fn"
        assert item.name == "add"
        assert "Add two integers" in item.doc

    def test_extracts_pub_typealias(self) -> None:
        doc = extract_module_doc(_PUB_TYPEALIAS, "types")
        assert len(doc.items) == 1
        assert doc.items[0].kind == "typealias"
        assert doc.items[0].name == "IntList"

    def test_extracts_pub_binding(self) -> None:
        doc = extract_module_doc(_PUB_BINDING, "consts")
        assert len(doc.items) == 1
        assert doc.items[0].kind == "binding"
        assert doc.items[0].name == "ANSWER"

    def test_skips_private_declarations(self) -> None:
        doc = extract_module_doc(_PRIVATE_ONLY, "mod")
        assert len(doc.items) == 0

    def test_no_doc_comment_gives_empty_doc(self) -> None:
        doc = extract_module_doc(_NO_DOC_COMMENT, "mod")
        assert len(doc.items) == 1
        assert doc.items[0].doc == ""

    def test_multi_paragraph_doc_comment(self) -> None:
        doc = extract_module_doc(_MULTI_PARAGRAPH, "mod")
        assert len(doc.items) == 1
        text = doc.items[0].doc
        assert "First paragraph" in text
        assert "Second paragraph" in text
        # Paragraphs are separated
        assert text.index("First") < text.index("Second")

    def test_regular_comments_ignored(self) -> None:
        doc = extract_module_doc(_MIXED_COMMENTS, "mod")
        assert len(doc.items) == 1
        assert "Regular comment" not in doc.items[0].doc
        assert "Doc comment kept" in doc.items[0].doc

    def test_module_name_recorded(self) -> None:
        doc = extract_module_doc(_PUB_FN, "my_module")
        assert doc.module_name == "my_module"

    def test_fn_signature_includes_params_and_return(self) -> None:
        doc = extract_module_doc(_PUB_FN, "mod")
        sig = doc.items[0].signature
        assert "add" in sig
        assert "a: Int" in sig
        assert "b: Int" in sig
        assert "-> Int" in sig

    def test_binding_signature_includes_type_annotation(self) -> None:
        doc = extract_module_doc(_PUB_BINDING, "mod")
        sig = doc.items[0].signature
        assert "ANSWER" in sig
        assert "Int" in sig


# ---------------------------------------------------------------------------
# render_markdown
# ---------------------------------------------------------------------------


class TestRenderMarkdown:
    def test_empty_module_message(self) -> None:
        md = render_markdown(ModuleDoc(module_name="empty"))
        assert "No public declarations" in md

    def test_module_name_in_heading(self) -> None:
        md = render_markdown(ModuleDoc(module_name="mymod"))
        assert "mymod" in md

    def test_fn_section_heading(self) -> None:
        doc = extract_module_doc(_PUB_FN, "mod")
        md = render_markdown(doc)
        assert "## Functions" in md

    def test_typealias_section_heading(self) -> None:
        doc = extract_module_doc(_PUB_TYPEALIAS, "mod")
        md = render_markdown(doc)
        assert "## Type Aliases" in md

    def test_binding_section_heading(self) -> None:
        doc = extract_module_doc(_PUB_BINDING, "mod")
        md = render_markdown(doc)
        assert "## Bindings" in md

    def test_code_block_contains_signature(self) -> None:
        doc = extract_module_doc(_PUB_FN, "mod")
        md = render_markdown(doc)
        assert "```aster" in md
        assert "pub fn add" in md

    def test_doc_text_appears_after_code_block(self) -> None:
        doc = extract_module_doc(_PUB_FN, "mod")
        md = render_markdown(doc)
        assert "Add two integers" in md


# ---------------------------------------------------------------------------
# generate_docs (file I/O)
# ---------------------------------------------------------------------------


class TestGenerateDocs:
    def test_writes_markdown_file(self, tmp_path: Path) -> None:
        src = tmp_path / "utils.aster"
        src.write_text("pub fn greet():\n    pass\n", encoding="utf-8")
        out = generate_docs(src, out_dir=tmp_path / "docs")
        assert out.exists()
        assert out.suffix == ".md"

    def test_output_filename_matches_module(self, tmp_path: Path) -> None:
        src = tmp_path / "mylib.aster"
        src.write_text("pub fn foo():\n    pass\n", encoding="utf-8")
        out = generate_docs(src)
        assert out.name == "mylib.md"

    def test_default_out_dir_is_aster_docs(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.aster"
        src.write_text("pub fn x():\n    pass\n", encoding="utf-8")
        out = generate_docs(src)
        assert "__aster_docs__" in str(out)

    def test_custom_out_dir(self, tmp_path: Path) -> None:
        src = tmp_path / "mod.aster"
        src.write_text("pub fn x():\n    pass\n", encoding="utf-8")
        out_dir = tmp_path / "custom_docs"
        out = generate_docs(src, out_dir=out_dir)
        assert out.parent == out_dir


# ---------------------------------------------------------------------------
# CLI: aster doc
# ---------------------------------------------------------------------------


class TestCLIDocCommand:
    def test_basic_invocation(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        src = tmp_path / "hello.aster"
        src.write_text("## Say hello.\npub fn greet():\n    pass\n", encoding="utf-8")
        assert main(["doc", str(src)]) == 0
        out = capsys.readouterr().out
        assert "Docs written to" in out

    def test_out_dir_flag(self, tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
        src = tmp_path / "lib.aster"
        src.write_text("pub fn f():\n    pass\n", encoding="utf-8")
        out_dir = tmp_path / "output"
        assert main(["doc", str(src), "--out-dir", str(out_dir)]) == 0
        assert (out_dir / "lib.md").exists()
