"""C backend transpiler for Aster (stub — full code generation not yet implemented)."""

from __future__ import annotations

from aster_lang import hir


class CTranspiler:
    """Transpiles Aster HIR to C source code (stub implementation)."""

    def __init__(self) -> None:
        self.output: list[str] = []

    def transpile(self, module: hir.HModule) -> str:
        """Transpile an Aster HIR module to C source code."""
        self.output = [
            "#include <stdio.h>",
            "#include <stdint.h>",
            "",
            "// Aster runtime types",
            "typedef int64_t aster_int;",
            "",
        ]

        for decl in module.decls:
            if isinstance(decl, hir.HFunction):
                self._emit_function(decl)

        return "\n".join(self.output)

    def _emit_function(self, fn: hir.HFunction) -> None:
        """Emit a C stub for a function declaration."""
        # Stub: emit a comment placeholder for each function
        self.output.append(f"// fn {fn.name}({', '.join(fn.params)})")
        if fn.name == "main":
            self.output.append("int main(void) {")
            self.output.append("    // TODO: emit function body")
            self.output.append("    return 0;")
            self.output.append("}")
        else:
            self.output.append(f"void {fn.name}(void) {{")
            self.output.append("    // TODO: emit function body")
            self.output.append("}")
        self.output.append("")
