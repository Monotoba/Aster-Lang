from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aster_lang import ast
from aster_lang.bytecode import BCFunction, BCProgram, Instr, ModuleSpec, Op
from aster_lang.module_resolution import (
    ModuleResolutionError,
    ModuleSearchConfig,
    resolve_module_path,
)
from aster_lang.parser import parse_module
from aster_lang.semantic import SemanticAnalyzer


class VMError(Exception):
    pass


@dataclass(slots=True)
class _Cell:
    value: object


@dataclass(slots=True, frozen=True)
class _Closure:
    fn_id: str
    free: tuple[_Cell, ...]


@dataclass(slots=True)
class _Frame:
    fn: BCFunction
    ip: int
    locals: list[_Cell]
    free: list[_Cell]
    stack: list[object]
    globals: dict[str, _Cell]
    module_label: str


class _Compiler:
    def __init__(self) -> None:
        self._consts: list[object] = []
        self._functions: dict[str, BCFunction] = {}
        self._modules: dict[str, ModuleSpec] = {}
        self._lambda_counter = 0

    def _const(self, value: object) -> int:
        # Simple linear dedup is fine at this stage.
        try:
            return self._consts.index(value)
        except ValueError:
            self._consts.append(value)
            return len(self._consts) - 1

    def compile_project(
        self,
        *,
        entry_path: Path,
        dep_overrides: dict[str, Path] | None = None,
        extra_roots: tuple[Path, ...] = (),
        resolver_config: ModuleSearchConfig | None = None,
    ) -> BCProgram:
        dep_overrides = dep_overrides or {}
        compiled: set[str] = set()
        compiling: set[str] = set()

        entry_source = entry_path.read_text(encoding="utf-8")
        entry_ast = parse_module(entry_source)
        entry_label = "__entry__"

        def compile_named_module(label: str, *, module_path: Path, module_ast: ast.Module) -> None:
            if label in compiled:
                return
            if label in compiling:
                raise VMError(f"Cyclic import detected for module '{label}'")
            compiling.add(label)
            try:
                # Recurse on imports first.
                for decl in module_ast.declarations:
                    if not isinstance(decl, ast.ImportDecl):
                        continue
                    parts = decl.module.parts
                    import_label = ".".join(parts)
                    try:
                        import_path = resolve_module_path(
                            module_path.parent,
                            parts,
                            dep_overrides=dep_overrides,
                            extra_roots=extra_roots,
                            config=resolver_config,
                        )
                    except ModuleResolutionError as exc:
                        raise VMError(str(exc)) from exc
                    import_ast = parse_module(import_path.read_text(encoding="utf-8"))
                    compile_named_module(
                        import_label,
                        module_path=import_path,
                        module_ast=import_ast,
                    )

                self._compile_module(label, module_ast)
                compiled.add(label)
            finally:
                compiling.remove(label)

        # Compile dependencies of the entry module using entry directory for resolution.
        for decl in entry_ast.declarations:
            if not isinstance(decl, ast.ImportDecl):
                continue
            parts = decl.module.parts
            import_label = ".".join(parts)
            try:
                import_path = resolve_module_path(
                    entry_path.parent,
                    parts,
                    dep_overrides=dep_overrides,
                    extra_roots=extra_roots,
                    config=resolver_config,
                )
            except ModuleResolutionError as exc:
                raise VMError(str(exc)) from exc
            import_ast = parse_module(import_path.read_text(encoding="utf-8"))
            compile_named_module(import_label, module_path=import_path, module_ast=import_ast)

        # Compile the entry module last.
        self._compile_module(entry_label, entry_ast)

        return BCProgram(
            constants=tuple(self._consts),
            functions=dict(self._functions),
            modules=dict(self._modules),
            entry_module=entry_label,
        )

    def compile_single_source(self, source: str) -> BCProgram:
        """Compile a single-source snippet as an entry module only."""
        entry_ast = parse_module(source)
        entry_label = "__entry__"
        self._compile_module(entry_label, entry_ast)
        return BCProgram(
            constants=tuple(self._consts),
            functions=dict(self._functions),
            modules=dict(self._modules),
            entry_module=entry_label,
        )

    def _compile_module(self, label: str, module: ast.Module) -> None:
        init_id = f"{label}::__init__"
        init_fn, export_spec = self._compile_module_init(label, module, init_id)
        self._functions[init_id] = init_fn
        self._modules[label] = ModuleSpec(label=label, init_fn=init_id, exports=export_spec)

        for decl in module.declarations:
            if isinstance(decl, ast.FunctionDecl):
                fn_id = f"{label}::{decl.name}"
                self._functions[fn_id] = self._compile_function(decl, fn_id)

    def _compile_module_init(
        self,
        label: str,
        module: ast.Module,
        init_id: str,
    ) -> tuple[BCFunction, dict[str, tuple[str, str]]]:
        # Module init is a regular function with access to globals via LOAD/STORE_GLOBAL.
        # It handles: imports and top-level let declarations.
        scopes: list[dict[str, int]] = [{}]
        next_local = 0

        def alloc_temp() -> int:
            nonlocal next_local
            idx = next_local
            next_local += 1
            return idx

        def define(name: str) -> int:
            nonlocal next_local
            if name in scopes[-1]:
                raise VMError(f"Duplicate definition '{name}' in VM backend")
            idx = next_local
            next_local += 1
            scopes[-1][name] = idx
            return idx

        code: list[Instr] = []

        def emit(op: Op, arg: object | None = None) -> None:
            code.append(Instr(op, arg))

        # Exports: pub fns and pub lets.
        exports: dict[str, tuple[str, str]] = {}
        for decl in module.declarations:
            if isinstance(decl, ast.FunctionDecl) and decl.is_public:
                exports[decl.name] = ("fn", f"{label}::{decl.name}")
            if isinstance(decl, ast.LetDecl) and decl.is_public:
                exports[decl.name] = ("var", decl.name)

        # Bind top-level functions into the module global env so unqualified calls work.
        for decl in module.declarations:
            if isinstance(decl, ast.FunctionDecl):
                emit(Op.CONST, self._const(f"{label}::{decl.name}"))
                emit(Op.STORE_GLOBAL, self._const(decl.name))

        # Compile imports and lets.
        for decl in module.declarations:
            if isinstance(decl, ast.ImportDecl):
                import_label = ".".join(decl.module.parts)
                binding_name = decl.alias if decl.alias is not None else decl.module.parts[-1]
                if decl.imports is None:
                    emit(Op.IMPORT_MODULE, self._const(import_label))
                    emit(Op.STORE_GLOBAL, self._const(binding_name))
                else:
                    # Import named exports.
                    tmp = define(f"__mod_{binding_name}")
                    emit(Op.IMPORT_MODULE, self._const(import_label))
                    emit(Op.STORE, tmp)
                    for name in decl.imports:
                        emit(Op.LOAD, tmp)
                        emit(Op.MEMBER, self._const(name))
                        emit(Op.STORE_GLOBAL, self._const(name))
            elif isinstance(decl, ast.LetDecl):
                # Use the same expression compiler as functions, but globals for identifiers.
                # We'll compile via a small inner compiler that emits to STORE_GLOBAL.
                fn = ast.FunctionDecl(
                    name="__init__",
                    params=[],
                    return_type=None,
                    body=[ast.ReturnStmt(decl.initializer)],
                )
                expr_fn = self._compile_function(fn, "__expr_tmp__", globals_only=True)
                # Inline: compile the expression by reusing its bytecode, dropping final RETURN.
                # This is clunky but keeps semantics consistent with the function compiler subset.
                # expr_fn always ends with CONST None; RETURN, so we strip those and strip RETURN.
                for ins in expr_fn.code:
                    if ins.op == Op.RETURN:
                        # value is already on stack
                        break
                    code.append(ins)
                emit(Op.STORE_GLOBAL, self._const(decl.name))

        emit(Op.CONST, self._const(None))
        emit(Op.RETURN)

        return (
            BCFunction(
                name=init_id,
                params=(),
                code=tuple(code),
                local_count=next_local,
            ),
            exports,
        )

    def _compile_function(
        self,
        decl: ast.FunctionDecl,
        fn_id: str,
        *,
        globals_only: bool = False,
        free_map: dict[str, int] | None = None,
    ) -> BCFunction:
        free_map = {} if free_map is None else dict(free_map)
        scopes: list[dict[str, int]] = [{}]
        next_local = 0
        mut_slots: set[int] = set()  # slots allowed to be reassigned via <-

        def push_scope() -> None:
            scopes.append({})

        def pop_scope() -> None:
            if len(scopes) == 1:
                raise VMError("Internal error: cannot pop root scope")
            scopes.pop()

        def alloc_temp() -> int:
            nonlocal next_local
            idx = next_local
            next_local += 1
            return idx

        def define(name: str, *, is_mutable: bool = False) -> int:
            nonlocal next_local
            if name in scopes[-1]:
                raise VMError(f"Duplicate definition '{name}' in VM backend")
            idx = next_local
            next_local += 1
            scopes[-1][name] = idx
            if is_mutable:
                mut_slots.add(idx)
            return idx

        def lookup(name: str) -> int:
            for scope in reversed(scopes):
                found = scope.get(name)
                if found is not None:
                    return found
            raise VMError(f"Undefined local '{name}' in VM backend")

        # Allocate param slots first (params are mutable by convention for now).
        for p in decl.params:
            define(p.name, is_mutable=True)

        code: list[Instr] = []

        def emit(op: Op, arg: object | None = None) -> None:
            code.append(Instr(op, arg))

        @dataclass(slots=True)
        class _LoopCtx:
            break_sites: list[int]
            continue_sites: list[int]

        loop_stack: list[_LoopCtx] = []

        def emit_jump(op: Op) -> int:
            if op not in (Op.JMP, Op.JMP_IF_FALSE):
                raise VMError(f"emit_jump called with non-jump opcode: {op}")
            code.append(Instr(op, -1))
            return len(code) - 1

        def patch_jump(at: int, target: int) -> None:
            ins = code[at]
            if ins.op not in (Op.JMP, Op.JMP_IF_FALSE):
                raise VMError("Can only patch jump instructions")
            code[at] = Instr(ins.op, target)

        def compile_expr(expr: ast.Expr) -> None:
            if isinstance(expr, ast.IntegerLiteral):
                emit(Op.CONST, self._const(expr.value))
                return
            if isinstance(expr, ast.StringLiteral):
                emit(Op.CONST, self._const(expr.value))
                return
            if isinstance(expr, ast.BoolLiteral):
                emit(Op.CONST, self._const(expr.value))
                return
            if isinstance(expr, ast.NilLiteral):
                emit(Op.CONST, self._const(None))
                return
            if isinstance(expr, ast.Identifier):
                if expr.name in free_map:
                    emit(Op.LOAD_FREE, free_map[expr.name])
                    return
                if globals_only:
                    emit(Op.LOAD_GLOBAL, self._const(expr.name))
                else:
                    try:
                        emit(Op.LOAD, lookup(expr.name))
                    except VMError:
                        emit(Op.LOAD_GLOBAL, self._const(expr.name))
                return
            if isinstance(expr, ast.ParenExpr):
                compile_expr(expr.expr)
                return
            if isinstance(expr, ast.BinaryExpr):
                if expr.operator == "and":
                    compile_expr(expr.left)
                    jmp_false = emit_jump(Op.JMP_IF_FALSE)
                    compile_expr(expr.right)
                    jmp_end = emit_jump(Op.JMP)
                    false_label = len(code)
                    patch_jump(jmp_false, false_label)
                    emit(Op.CONST, self._const(False))
                    end_label = len(code)
                    patch_jump(jmp_end, end_label)
                    return

                if expr.operator == "or":
                    compile_expr(expr.left)
                    emit(Op.NOT)
                    jmp_true = emit_jump(Op.JMP_IF_FALSE)  # if left was true
                    compile_expr(expr.right)
                    jmp_end = emit_jump(Op.JMP)
                    true_label = len(code)
                    patch_jump(jmp_true, true_label)
                    emit(Op.CONST, self._const(True))
                    end_label = len(code)
                    patch_jump(jmp_end, end_label)
                    return

                compile_expr(expr.left)
                compile_expr(expr.right)
                op_map = {
                    "+": Op.ADD,
                    "-": Op.SUB,
                    "*": Op.MUL,
                    "/": Op.DIV,
                    "%": Op.MOD,
                    "==": Op.EQ,
                    "!=": Op.NE,
                    "<": Op.LT,
                    "<=": Op.LE,
                    ">": Op.GT,
                    ">=": Op.GE,
                }
                op = op_map.get(expr.operator)
                if op is None:
                    raise VMError(f"Unsupported binary operator in VM backend: {expr.operator}")
                emit(op)
                return
            if isinstance(expr, ast.UnaryExpr):
                compile_expr(expr.operand)
                if expr.operator == "-":
                    emit(Op.NEG)
                    return
                if expr.operator == "not":
                    emit(Op.NOT)
                    return
                raise VMError(f"Unsupported unary operator in VM backend: {expr.operator}")
            if isinstance(expr, ast.CallExpr):
                # Support calling identifiers and member expressions (module namespaces).
                compile_expr(expr.func)
                for a in expr.args:
                    compile_expr(a)
                emit(Op.CALL_VALUE, len(expr.args))
                return
            if isinstance(expr, ast.ListExpr):
                for e in expr.elements:
                    compile_expr(e)
                emit(Op.BUILD_LIST, len(expr.elements))
                return
            if isinstance(expr, ast.TupleExpr):
                for e in expr.elements:
                    compile_expr(e)
                emit(Op.BUILD_TUPLE, len(expr.elements))
                return
            if isinstance(expr, ast.RecordExpr):
                field_names: list[str] = []
                for f in expr.fields:
                    field_names.append(f.name)
                    compile_expr(f.value)
                emit(Op.BUILD_RECORD, tuple(field_names))
                return
            if isinstance(expr, ast.MemberExpr):
                compile_expr(expr.obj)
                emit(Op.MEMBER, self._const(expr.member))
                return
            if isinstance(expr, ast.IndexExpr):
                compile_expr(expr.obj)
                compile_expr(expr.index)
                emit(Op.INDEX)
                return
            if isinstance(expr, ast.LambdaExpr):
                self._lambda_counter += 1
                lambda_id = f"{fn_id}::__lambda{self._lambda_counter}"

                def _pattern_names(pattern: ast.Pattern) -> set[str]:
                    if isinstance(pattern, ast.BindingPattern):
                        return {pattern.name}
                    if isinstance(pattern, ast.RestPattern):
                        return {pattern.name}
                    if isinstance(pattern, ast.OrPattern):
                        out: set[str] = set()
                        for alt in pattern.alternatives:
                            out |= _pattern_names(alt)
                        return out
                    if isinstance(pattern, ast.TuplePattern | ast.ListPattern):
                        out = set()
                        for el in pattern.elements:
                            out |= _pattern_names(el)
                        return out
                    if isinstance(pattern, ast.RecordPattern):
                        out = set()
                        for f in pattern.fields:
                            out |= _pattern_names(f.pattern)
                        return out
                    return set()

                def _free_names_lambda(lam: ast.LambdaExpr) -> set[str]:
                    defined: set[str] = {p.name for p in lam.params}
                    used: set[str] = set()

                    def walk_expr(e: ast.Expr) -> None:
                        if isinstance(e, ast.Identifier):
                            used.add(e.name)
                            return
                        if isinstance(e, ast.LambdaExpr):
                            used.update(_free_names_lambda(e))
                            return
                        if isinstance(e, ast.ParenExpr):
                            walk_expr(e.expr)
                            return
                        if isinstance(e, ast.BinaryExpr):
                            walk_expr(e.left)
                            walk_expr(e.right)
                            return
                        if isinstance(e, ast.UnaryExpr):
                            walk_expr(e.operand)
                            return
                        if isinstance(e, ast.CallExpr):
                            walk_expr(e.func)
                            for a in e.args:
                                walk_expr(a)
                            return
                        if isinstance(e, ast.ListExpr | ast.TupleExpr):
                            for el in e.elements:
                                walk_expr(el)
                            return
                        if isinstance(e, ast.RecordExpr):
                            for f in e.fields:
                                walk_expr(f.value)
                            return
                        if isinstance(e, ast.MemberExpr):
                            walk_expr(e.obj)
                            return
                        if isinstance(e, ast.IndexExpr):
                            walk_expr(e.obj)
                            walk_expr(e.index)
                            return
                        if isinstance(
                            e,
                            ast.IntegerLiteral
                            | ast.StringLiteral
                            | ast.BoolLiteral
                            | ast.NilLiteral,
                        ):
                            return
                        raise VMError(
                            "Unsupported expression in VM backend: " f"{type(e).__name__}"
                        )

                    def walk_stmt(s: ast.Stmt) -> None:
                        if isinstance(s, ast.LetStmt):
                            defined.update(_pattern_names(s.pattern))
                            walk_expr(s.initializer)
                            return
                        if isinstance(s, ast.AssignStmt):
                            walk_expr(s.target)
                            walk_expr(s.value)
                            return
                        if isinstance(s, ast.ReturnStmt):
                            if s.value is not None:
                                walk_expr(s.value)
                            return
                        if isinstance(s, ast.ExprStmt):
                            walk_expr(s.expr)
                            return
                        if isinstance(s, ast.IfStmt):
                            walk_expr(s.condition)
                            for ss in s.then_block:
                                walk_stmt(ss)
                            if s.else_block:
                                for ss in s.else_block:
                                    walk_stmt(ss)
                            return
                        if isinstance(s, ast.WhileStmt):
                            walk_expr(s.condition)
                            for ss in s.body:
                                walk_stmt(ss)
                            return
                        if isinstance(s, ast.ForStmt):
                            defined.add(s.variable)
                            walk_expr(s.iterable)
                            for ss in s.body:
                                walk_stmt(ss)
                            return
                        if isinstance(s, ast.MatchStmt):
                            walk_expr(s.subject)
                            for arm in s.arms:
                                defined.update(_pattern_names(arm.pattern))
                                for ss in arm.body:
                                    walk_stmt(ss)
                            return
                        if isinstance(s, ast.BreakStmt | ast.ContinueStmt):
                            return
                        raise VMError(f"Unsupported statement in VM backend: {type(s).__name__}")

                    if isinstance(lam.body, list):
                        for ss in lam.body:
                            walk_stmt(ss)
                    else:
                        walk_expr(lam.body)

                    return used - defined

                lexical_free = _free_names_lambda(expr)

                captures: list[tuple[str, int]] = []
                lambda_free_map: dict[str, int] = {}
                for name in sorted(lexical_free):
                    if name in free_map:
                        captures.append(("free", free_map[name]))
                        lambda_free_map[name] = len(captures) - 1
                        continue
                    try:
                        slot = lookup(name)
                    except VMError:
                        continue  # globals are read dynamically; no capture needed
                    captures.append(("local", slot))
                    lambda_free_map[name] = len(captures) - 1

                # Compile lambda body as a synthetic function.
                params = [ast.ParamDecl(p.name, p.type_annotation) for p in expr.params]
                if isinstance(expr.body, list):
                    body_stmts = list(expr.body)
                else:
                    body_stmts = [ast.ReturnStmt(expr.body)]
                fn_decl = ast.FunctionDecl(
                    name=lambda_id,
                    params=params,
                    return_type=None,
                    body=body_stmts,
                )
                self._functions[lambda_id] = self._compile_function(
                    fn_decl,
                    lambda_id,
                    globals_only=False,
                    free_map=lambda_free_map,
                )

                # Build closure: push captured cell refs, then MAKE_CLOSURE.
                for kind, ref in captures:
                    if kind == "local":
                        emit(Op.REF_LOCAL, ref)
                    elif kind == "free":
                        emit(Op.REF_FREE, ref)
                    else:
                        raise VMError("Internal error: invalid capture kind")
                emit(Op.MAKE_CLOSURE, (self._const(lambda_id), len(captures)))
                return
            raise VMError(f"Unsupported expression in VM backend: {type(expr).__name__}")

        def _compile_destructure(pattern: ast.Pattern, src_slot: int, *, is_mutable: bool) -> None:
            """Emit bindings from a destructuring pattern against a value already in src_slot."""
            if isinstance(pattern, ast.BindingPattern):
                emit(Op.LOAD, src_slot)
                emit(Op.STORE, define(pattern.name, is_mutable=is_mutable))
                return
            if isinstance(pattern, ast.WildcardPattern):
                return  # no binding needed
            if isinstance(pattern, ast.ListPattern | ast.TuplePattern):
                elements = pattern.elements
                for i, elem in enumerate(elements):
                    if isinstance(elem, ast.RestPattern):
                        # rest gets obj[rest_index:]
                        rest_slot = alloc_temp()
                        emit(Op.LOAD, src_slot)
                        emit(Op.SLICE_FROM, i)
                        emit(Op.STORE, rest_slot)
                        _compile_destructure(elem, rest_slot, is_mutable=is_mutable)
                    else:
                        elem_slot = alloc_temp()
                        emit(Op.LOAD, src_slot)
                        emit(Op.CONST, self._const(i))
                        emit(Op.INDEX)
                        emit(Op.STORE, elem_slot)
                        _compile_destructure(elem, elem_slot, is_mutable=is_mutable)
                return
            if isinstance(pattern, ast.RecordPattern):
                for field in pattern.fields:
                    field_slot = alloc_temp()
                    emit(Op.LOAD, src_slot)
                    emit(Op.MEMBER, self._const(field.name))
                    emit(Op.STORE, field_slot)
                    _compile_destructure(field.pattern, field_slot, is_mutable=is_mutable)
                return
            if isinstance(pattern, ast.RestPattern):
                emit(Op.LOAD, src_slot)
                emit(Op.STORE, define(pattern.name, is_mutable=is_mutable))
                return
            raise VMError(
                f"VM backend does not support destructuring pattern: {type(pattern).__name__}"
            )

        def compile_stmt(stmt: ast.Stmt) -> None:
            if isinstance(stmt, ast.LetStmt):
                compile_expr(stmt.initializer)
                if isinstance(stmt.pattern, ast.BindingPattern):
                    emit(Op.STORE, define(stmt.pattern.name, is_mutable=stmt.is_mutable))
                else:
                    src_slot = alloc_temp()
                    emit(Op.STORE, src_slot)
                    _compile_destructure(stmt.pattern, src_slot, is_mutable=stmt.is_mutable)
                return
            if isinstance(stmt, ast.AssignStmt):
                if isinstance(stmt.target, ast.Identifier):
                    compile_expr(stmt.value)
                    if stmt.target.name in free_map:
                        emit(Op.STORE_FREE, free_map[stmt.target.name])
                        return
                    try:
                        slot = lookup(stmt.target.name)
                        if slot not in mut_slots:
                            raise VMError(
                                f"Cannot assign to immutable binding '{stmt.target.name}'"
                            )
                        emit(Op.STORE, slot)
                    except VMError as exc:
                        if "immutable" in str(exc):
                            raise
                        emit(Op.STORE_GLOBAL, self._const(stmt.target.name))
                    return
                if isinstance(stmt.target, ast.MemberExpr):
                    # Only support `x.field <- v` where x is an identifier (local/global).
                    if not isinstance(stmt.target.obj, ast.Identifier):
                        raise VMError("VM backend only supports member assignment on identifiers")
                    compile_expr(stmt.value)  # push value
                    key_k = self._const(stmt.target.member)
                    try:
                        slot = lookup(stmt.target.obj.name)
                        emit(Op.SET_MEMBER, (key_k, "local", slot))
                    except VMError:
                        emit(Op.SET_MEMBER, (key_k, "global", self._const(stmt.target.obj.name)))
                    return
                if isinstance(stmt.target, ast.IndexExpr):
                    # Only support `x[i] <- v` where x is an identifier.
                    if not isinstance(stmt.target.obj, ast.Identifier):
                        raise VMError("VM backend only supports index assignment on identifiers")
                    compile_expr(stmt.target.index)  # push index
                    compile_expr(stmt.value)  # push value
                    try:
                        slot = lookup(stmt.target.obj.name)
                        emit(Op.SET_INDEX, ("local", slot))
                    except VMError:
                        emit(Op.SET_INDEX, ("global", self._const(stmt.target.obj.name)))
                    return
                raise VMError("Unsupported assignment target in VM backend")
            if isinstance(stmt, ast.ReturnStmt):
                if stmt.value is None:
                    emit(Op.CONST, self._const(None))
                else:
                    compile_expr(stmt.value)
                emit(Op.RETURN)
                return
            if isinstance(stmt, ast.ExprStmt):
                compile_expr(stmt.expr)
                emit(Op.POP)
                return
            if isinstance(stmt, ast.IfStmt):
                compile_expr(stmt.condition)
                jmp_else = emit_jump(Op.JMP_IF_FALSE)
                push_scope()
                for s in stmt.then_block:
                    compile_stmt(s)
                pop_scope()

                if stmt.else_block:
                    jmp_end = emit_jump(Op.JMP)
                    else_target = len(code)
                    patch_jump(jmp_else, else_target)
                    push_scope()
                    for s in stmt.else_block:
                        compile_stmt(s)
                    pop_scope()
                    end_target = len(code)
                    patch_jump(jmp_end, end_target)
                else:
                    end_target = len(code)
                    patch_jump(jmp_else, end_target)
                return
            if isinstance(stmt, ast.WhileStmt):
                loop_start = len(code)
                compile_expr(stmt.condition)
                jmp_end = emit_jump(Op.JMP_IF_FALSE)
                ctx = _LoopCtx(break_sites=[], continue_sites=[])
                loop_stack.append(ctx)
                push_scope()
                for s in stmt.body:
                    compile_stmt(s)
                pop_scope()
                emit(Op.JMP, loop_start)
                end_target = len(code)
                patch_jump(jmp_end, end_target)
                for site in ctx.break_sites:
                    patch_jump(site, end_target)
                for site in ctx.continue_sites:
                    patch_jump(site, loop_start)
                loop_stack.pop()
                return
            if isinstance(stmt, ast.ForStmt):
                # for x in iterable: body
                push_scope()
                loop_var_slot = define(stmt.variable, is_mutable=True)
                iter_slot = alloc_temp()
                idx_slot = alloc_temp()

                compile_expr(stmt.iterable)
                emit(Op.STORE, iter_slot)
                emit(Op.CONST, self._const(0))
                emit(Op.STORE, idx_slot)

                loop_check = len(code)
                emit(Op.LOAD, idx_slot)
                emit(Op.LOAD, iter_slot)
                emit(Op.LEN)
                emit(Op.LT)
                jmp_end = emit_jump(Op.JMP_IF_FALSE)

                # loop var = iterable[idx]
                emit(Op.LOAD, iter_slot)
                emit(Op.LOAD, idx_slot)
                emit(Op.INDEX)
                emit(Op.STORE, loop_var_slot)

                ctx = _LoopCtx(break_sites=[], continue_sites=[])
                loop_stack.append(ctx)

                for s in stmt.body:
                    compile_stmt(s)

                inc_label = len(code)
                # continue in a for-loop skips to the increment step
                for site in ctx.continue_sites:
                    patch_jump(site, inc_label)

                emit(Op.LOAD, idx_slot)
                emit(Op.CONST, self._const(1))
                emit(Op.ADD)
                emit(Op.STORE, idx_slot)

                emit(Op.JMP, loop_check)

                end_label = len(code)
                patch_jump(jmp_end, end_label)
                for site in ctx.break_sites:
                    patch_jump(site, end_label)
                loop_stack.pop()
                pop_scope()
                return
            if isinstance(stmt, ast.BreakStmt | ast.ContinueStmt):
                if not loop_stack:
                    raise VMError("break/continue used outside of a loop in VM backend")
                ctx = loop_stack[-1]
                site = emit_jump(Op.JMP)
                if isinstance(stmt, ast.BreakStmt):
                    ctx.break_sites.append(site)
                else:
                    ctx.continue_sites.append(site)
                return
            if isinstance(stmt, ast.MatchStmt):
                # Evaluate the subject once and store it in a hidden temp slot.
                subj_slot = alloc_temp()
                compile_expr(stmt.subject)
                emit(Op.STORE, subj_slot)

                jmp_end_sites: list[int] = []

                for arm in stmt.arms:
                    push_scope()

                    def collect_names(p: ast.Pattern) -> set[str]:
                        if isinstance(p, ast.BindingPattern):
                            return {p.name}
                        if isinstance(p, ast.RestPattern):
                            return {p.name}
                        if isinstance(p, ast.OrPattern):
                            out: set[str] = set()
                            for a in p.alternatives:
                                out |= collect_names(a)
                            return out
                        if isinstance(p, ast.TuplePattern | ast.ListPattern):
                            out = set()
                            for e in p.elements:
                                out |= collect_names(e)
                            return out
                        if isinstance(p, ast.RecordPattern):
                            out = set()
                            for f in p.fields:
                                out |= collect_names(f.pattern)
                            return out
                        return set()

                    def bind_from_slot(
                        value_slot: int,
                        name: str,
                        *,
                        bind_slots: dict[str, int] | None,
                    ) -> None:
                        emit(Op.LOAD, value_slot)
                        if bind_slots is not None:
                            emit(Op.STORE, bind_slots[name])
                        else:
                            emit(Op.STORE, define(name, is_mutable=True))

                    def compile_pattern(
                        pattern: ast.Pattern,
                        value_slot: int,
                        *,
                        bind_slots: dict[str, int] | None = None,
                    ) -> list[int]:
                        fail_sites: list[int] = []

                        def guard_is(op: Op) -> None:
                            emit(Op.LOAD, value_slot)
                            emit(op)
                            fail_sites.append(emit_jump(Op.JMP_IF_FALSE))

                        def guard_len_exact(n: int) -> None:
                            emit(Op.LOAD, value_slot)
                            emit(Op.LEN)
                            emit(Op.CONST, self._const(n))
                            emit(Op.EQ)
                            fail_sites.append(emit_jump(Op.JMP_IF_FALSE))

                        def guard_len_at_least(n: int) -> None:
                            emit(Op.LOAD, value_slot)
                            emit(Op.LEN)
                            emit(Op.CONST, self._const(n))
                            emit(Op.GE)
                            fail_sites.append(emit_jump(Op.JMP_IF_FALSE))

                        def guard_has_key(name: str) -> None:
                            emit(Op.LOAD, value_slot)
                            emit(Op.HAS_KEY, self._const(name))
                            fail_sites.append(emit_jump(Op.JMP_IF_FALSE))

                        if isinstance(pattern, ast.WildcardPattern):
                            return fail_sites
                        if isinstance(pattern, ast.BindingPattern):
                            bind_from_slot(value_slot, pattern.name, bind_slots=bind_slots)
                            return fail_sites
                        if isinstance(pattern, ast.RestPattern):
                            bind_from_slot(value_slot, pattern.name, bind_slots=bind_slots)
                            return fail_sites
                        if isinstance(pattern, ast.LiteralPattern):
                            emit(Op.LOAD, value_slot)
                            compile_expr(pattern.literal)
                            emit(Op.EQ)
                            fail_sites.append(emit_jump(Op.JMP_IF_FALSE))
                            return fail_sites
                        if isinstance(pattern, ast.OrPattern):
                            alt_names = (
                                collect_names(pattern.alternatives[0])
                                if pattern.alternatives
                                else set()
                            )
                            for a in pattern.alternatives[1:]:
                                if collect_names(a) != alt_names:
                                    raise VMError(
                                        "Or-pattern alternatives must bind the same names "
                                        "in VM backend"
                                    )

                            # Pre-allocate binding slots once and assign within each alternative.
                            slots: dict[str, int] = {}
                            for name in sorted(alt_names):
                                slots[name] = define(name, is_mutable=True)

                            jmp_to_success: list[int] = []
                            for i, alt in enumerate(pattern.alternatives):
                                alt_fail_sites = compile_pattern(alt, value_slot, bind_slots=slots)
                                if i != len(pattern.alternatives) - 1:
                                    jmp_to_success.append(emit_jump(Op.JMP))
                                    next_alt = len(code)
                                    for site in alt_fail_sites:
                                        patch_jump(site, next_alt)
                                else:
                                    # Last alternative: bubble failures up.
                                    fail_sites.extend(alt_fail_sites)

                            success_label = len(code)
                            for s in jmp_to_success:
                                patch_jump(s, success_label)
                            return fail_sites

                        if isinstance(pattern, ast.TuplePattern):
                            guard_is(Op.IS_TUPLE)
                            rest_index = None
                            for idx, e in enumerate(pattern.elements):
                                if isinstance(e, ast.RestPattern):
                                    rest_index = idx
                                    break
                            if rest_index is None:
                                guard_len_exact(len(pattern.elements))
                                for idx, sub in enumerate(pattern.elements):
                                    tmp = alloc_temp()
                                    emit(Op.LOAD, value_slot)
                                    emit(Op.CONST, self._const(idx))
                                    emit(Op.INDEX)
                                    emit(Op.STORE, tmp)
                                    fail_sites.extend(
                                        compile_pattern(sub, tmp, bind_slots=bind_slots)
                                    )
                            else:
                                guard_len_at_least(len(pattern.elements) - 1)
                                for idx, sub in enumerate(pattern.elements):
                                    if idx == rest_index:
                                        # Capture tuple rest.
                                        if not isinstance(sub, ast.RestPattern):
                                            raise VMError("Internal error: expected RestPattern")
                                        emit(Op.LOAD, value_slot)
                                        emit(Op.SLICE_FROM, rest_index)
                                        if bind_slots is not None:
                                            emit(Op.STORE, bind_slots[sub.name])
                                        else:
                                            emit(Op.STORE, define(sub.name, is_mutable=True))
                                        continue
                                    tmp = alloc_temp()
                                    emit(Op.LOAD, value_slot)
                                    emit(Op.CONST, self._const(idx))
                                    emit(Op.INDEX)
                                    emit(Op.STORE, tmp)
                                    fail_sites.extend(
                                        compile_pattern(sub, tmp, bind_slots=bind_slots)
                                    )
                            return fail_sites

                        if isinstance(pattern, ast.ListPattern):
                            guard_is(Op.IS_LIST)
                            rest_index = None
                            for idx, e in enumerate(pattern.elements):
                                if isinstance(e, ast.RestPattern):
                                    rest_index = idx
                                    break
                            if rest_index is None:
                                guard_len_exact(len(pattern.elements))
                                for idx, sub in enumerate(pattern.elements):
                                    tmp = alloc_temp()
                                    emit(Op.LOAD, value_slot)
                                    emit(Op.CONST, self._const(idx))
                                    emit(Op.INDEX)
                                    emit(Op.STORE, tmp)
                                    fail_sites.extend(
                                        compile_pattern(sub, tmp, bind_slots=bind_slots)
                                    )
                            else:
                                guard_len_at_least(len(pattern.elements) - 1)
                                for idx, sub in enumerate(pattern.elements):
                                    if idx == rest_index:
                                        if not isinstance(sub, ast.RestPattern):
                                            raise VMError("Internal error: expected RestPattern")
                                        emit(Op.LOAD, value_slot)
                                        emit(Op.SLICE_FROM, rest_index)
                                        if bind_slots is not None:
                                            emit(Op.STORE, bind_slots[sub.name])
                                        else:
                                            emit(Op.STORE, define(sub.name, is_mutable=True))
                                        continue
                                    tmp = alloc_temp()
                                    emit(Op.LOAD, value_slot)
                                    emit(Op.CONST, self._const(idx))
                                    emit(Op.INDEX)
                                    emit(Op.STORE, tmp)
                                    fail_sites.extend(
                                        compile_pattern(sub, tmp, bind_slots=bind_slots)
                                    )
                            return fail_sites

                        if isinstance(pattern, ast.RecordPattern):
                            guard_is(Op.IS_RECORD)
                            for f in pattern.fields:
                                guard_has_key(f.name)
                                tmp = alloc_temp()
                                emit(Op.LOAD, value_slot)
                                emit(Op.MEMBER, self._const(f.name))
                                emit(Op.STORE, tmp)
                                fail_sites.extend(
                                    compile_pattern(f.pattern, tmp, bind_slots=bind_slots)
                                )
                            return fail_sites

                        raise VMError(
                            "Unsupported match pattern in VM backend: " f"{type(pattern).__name__}"
                        )

                    fail_sites = compile_pattern(arm.pattern, subj_slot)

                    for s in arm.body:
                        compile_stmt(s)

                    pop_scope()

                    # Arm matched; skip remaining arms.
                    jmp_end_sites.append(emit_jump(Op.JMP))

                    next_arm_label = len(code)
                    for site in fail_sites:
                        patch_jump(site, next_arm_label)

                end_label = len(code)
                for site in jmp_end_sites:
                    patch_jump(site, end_label)
                return
            raise VMError(f"Unsupported statement in VM backend: {type(stmt).__name__}")

        for s in decl.body:
            compile_stmt(s)

        # Implicit return nil if control reaches end.
        emit(Op.CONST, self._const(None))
        emit(Op.RETURN)

        return BCFunction(
            name=fn_id,
            params=tuple(p.name for p in decl.params),
            code=tuple(code),
            local_count=next_local,
        )


class VM:
    def __init__(self, program: BCProgram) -> None:
        self.program = program
        self.output: list[str] = []
        self._frames: list[_Frame] = []
        self._module_envs: dict[str, dict[str, _Cell]] = {}
        self._module_exports: dict[str, dict[str, object]] = {}
        self._initializing: set[str] = set()

        BuiltinFn = Callable[[list[object]], object]

        def _fmt_value(v: object) -> str:
            if v is None:
                return "nil"
            if v is True:
                return "true"
            if v is False:
                return "false"
            if isinstance(v, list):
                return "[" + ", ".join(_fmt_value(x) for x in v) + "]"
            if isinstance(v, tuple):
                return "(" + ", ".join(_fmt_value(x) for x in v) + ")"
            if isinstance(v, dict):
                items = ", ".join(f"{k}: {_fmt_value(val)}" for k, val in v.items())
                return "{" + items + "}"
            return str(v)

        def builtin_print(args: list[object]) -> object:
            self.output.append(" ".join(_fmt_value(a) for a in args))
            return None

        def builtin_len(args: list[object]) -> object:
            return len(args[0])  # type: ignore[arg-type]

        def builtin_str(args: list[object]) -> object:
            return str(args[0])

        def builtin_int(args: list[object]) -> object:
            return int(args[0])  # type: ignore[call-overload]

        def builtin_abs(args: list[object]) -> object:
            return abs(args[0])  # type: ignore[arg-type]

        def builtin_max(args: list[object]) -> object:
            return max(args)  # type: ignore[type-var]

        def builtin_min(args: list[object]) -> object:
            return min(args)  # type: ignore[type-var]

        def builtin_range(args: list[object]) -> object:
            if len(args) == 1:
                stop = args[0]
                if type(stop) is not int:
                    raise VMError("range() expects Int arguments")
                return list(range(stop))
            if len(args) == 2:
                start, stop = args
                if type(start) is not int or type(stop) is not int:
                    raise VMError("range() expects Int arguments")
                return list(range(start, stop))
            raise VMError(f"range() takes 1 or 2 arguments, got {len(args)}")

        self._builtins: dict[str, tuple[int, BuiltinFn]] = {
            "print": (-1, builtin_print),
            "len": (1, builtin_len),
            "str": (1, builtin_str),
            "int": (1, builtin_int),
            "abs": (1, builtin_abs),
            "max": (-1, builtin_max),
            "min": (-1, builtin_min),
            "range": (-1, builtin_range),
        }

    def run_entry(self) -> None:
        entry_label = self.program.entry_module
        self._ensure_module_initialized(entry_label)
        main_id = f"{entry_label}::main"
        fn = self.program.functions.get(main_id)
        if fn is None:
            raise VMError("No main() function found")
        self._call_user(fn, [], module_label=entry_label)

    def _call_user(
        self,
        fn: BCFunction,
        args: list[object],
        *,
        module_label: str,
        free: tuple[_Cell, ...] = (),
    ) -> object:
        if len(args) != len(fn.params):
            raise VMError(f"{fn.name}() expected {len(fn.params)} args, got {len(args)}")
        locals_: list[_Cell] = [_Cell(None) for _ in range(fn.local_count)]
        for i, v in enumerate(args):
            locals_[i].value = v
        frame = _Frame(
            fn=fn,
            ip=0,
            locals=locals_,
            free=list(free),
            stack=[],
            globals=self._module_envs.setdefault(module_label, {}),
            module_label=module_label,
        )
        self._frames.append(frame)
        try:
            return self._run_frame()
        finally:
            self._frames.pop()

    def _run_frame(self) -> object:
        frame = self._frames[-1]
        consts = self.program.constants
        code = frame.fn.code
        while frame.ip < len(code):
            ins = code[frame.ip]
            frame.ip += 1

            if ins.op == Op.CONST:
                assert isinstance(ins.arg, int)
                frame.stack.append(consts[ins.arg])
                continue
            if ins.op == Op.LOAD:
                assert isinstance(ins.arg, int)
                frame.stack.append(frame.locals[ins.arg].value)
                continue
            if ins.op == Op.STORE:
                assert isinstance(ins.arg, int)
                frame.locals[ins.arg].value = frame.stack.pop()
                continue
            if ins.op == Op.POP:
                frame.stack.pop()
                continue

            if ins.op == Op.REF_LOCAL:
                assert isinstance(ins.arg, int)
                frame.stack.append(frame.locals[ins.arg])
                continue
            if ins.op == Op.REF_FREE:
                assert isinstance(ins.arg, int)
                frame.stack.append(frame.free[ins.arg])
                continue
            if ins.op == Op.REF_GLOBAL:
                assert isinstance(ins.arg, int)
                name_obj = consts[ins.arg]
                if not isinstance(name_obj, str):
                    raise VMError("REF_GLOBAL name constant must be a string")
                cell = frame.globals.get(name_obj)
                if cell is None:
                    cell = _Cell(None)
                    frame.globals[name_obj] = cell
                frame.stack.append(cell)
                continue
            if ins.op == Op.LOAD_FREE:
                assert isinstance(ins.arg, int)
                frame.stack.append(frame.free[ins.arg].value)
                continue
            if ins.op == Op.STORE_FREE:
                assert isinstance(ins.arg, int)
                frame.free[ins.arg].value = frame.stack.pop()
                continue
            if ins.op == Op.MAKE_CLOSURE:
                assert isinstance(ins.arg, tuple) and len(ins.arg) == 2
                fn_idx_obj, free_count_obj = ins.arg
                assert isinstance(fn_idx_obj, int)
                assert isinstance(free_count_obj, int)
                fn_id_obj = consts[fn_idx_obj]
                if not isinstance(fn_id_obj, str):
                    raise VMError("MAKE_CLOSURE fn id constant must be a string")
                free_cells = [frame.stack.pop() for _ in range(free_count_obj)][::-1]
                if any(not isinstance(c, _Cell) for c in free_cells):
                    raise VMError("MAKE_CLOSURE expects captured values to be cell references")
                frame.stack.append(_Closure(fn_id=fn_id_obj, free=tuple(free_cells)))  # type: ignore[arg-type]
                continue

            if ins.op in {
                Op.ADD,
                Op.SUB,
                Op.MUL,
                Op.DIV,
                Op.MOD,
                Op.EQ,
                Op.NE,
                Op.LT,
                Op.LE,
                Op.GT,
                Op.GE,
            }:
                b = frame.stack.pop()
                a = frame.stack.pop()
                frame.stack.append(self._binop(ins.op, a, b))
                continue

            if ins.op == Op.NEG:
                a = frame.stack.pop()
                if type(a) is not int:
                    raise VMError("Unary '-' only supported for Int in VM backend")
                frame.stack.append(-a)
                continue
            if ins.op == Op.NOT:
                a = frame.stack.pop()
                frame.stack.append(not bool(a))
                continue

            if ins.op == Op.JMP:
                assert isinstance(ins.arg, int)
                frame.ip = ins.arg
                continue
            if ins.op == Op.JMP_IF_FALSE:
                cond = frame.stack.pop()
                if not bool(cond):
                    assert isinstance(ins.arg, int)
                    frame.ip = ins.arg
                continue

            if ins.op == Op.CALL:
                assert isinstance(ins.arg, tuple) and len(ins.arg) == 2
                name_idx_obj, argc_obj = ins.arg
                assert isinstance(name_idx_obj, int)
                assert isinstance(argc_obj, int)
                name = consts[name_idx_obj]
                if not isinstance(name, str):
                    raise VMError("CALL name constant must be a string")
                args = [frame.stack.pop() for _ in range(argc_obj)][::-1]
                frame.stack.append(self._call(name, args, module_label=frame.module_label))
                continue
            if ins.op == Op.CALL_VALUE:
                assert isinstance(ins.arg, int)
                argc = ins.arg
                args = [frame.stack.pop() for _ in range(argc)][::-1]
                callee = frame.stack.pop()
                if isinstance(callee, str):
                    frame.stack.append(self._call(callee, args, module_label=frame.module_label))
                    continue
                if isinstance(callee, _Closure):
                    frame.stack.append(
                        self._call_closure(callee, args, module_label=frame.module_label)
                    )
                    continue
                raise VMError("Can only call function ids (strings) or closures in VM backend")

            if ins.op == Op.RETURN:
                return frame.stack.pop()

            if ins.op == Op.BUILD_LIST:
                assert isinstance(ins.arg, int)
                items = [frame.stack.pop() for _ in range(ins.arg)][::-1]
                frame.stack.append(items)
                continue
            if ins.op == Op.BUILD_TUPLE:
                assert isinstance(ins.arg, int)
                items = [frame.stack.pop() for _ in range(ins.arg)][::-1]
                frame.stack.append(tuple(items))
                continue
            if ins.op == Op.BUILD_RECORD:
                assert isinstance(ins.arg, tuple)
                names = ins.arg
                vals = [frame.stack.pop() for _ in range(len(names))][::-1]
                frame.stack.append({str(k): v for k, v in zip(names, vals, strict=True)})
                continue
            if ins.op == Op.MEMBER:
                assert isinstance(ins.arg, int)
                key_obj = consts[ins.arg]
                if not isinstance(key_obj, str):
                    raise VMError("MEMBER key constant must be a string")
                obj = frame.stack.pop()
                if not isinstance(obj, dict):
                    raise VMError("Member access only supported on records in VM backend")
                if key_obj not in obj:
                    raise VMError(f"Missing record field '{key_obj}'")
                frame.stack.append(obj[key_obj])
                continue
            if ins.op == Op.INDEX:
                idx = frame.stack.pop()
                obj = frame.stack.pop()
                if isinstance(obj, list) and type(idx) is int:
                    try:
                        frame.stack.append(obj[idx])
                    except IndexError as exc:
                        raise VMError(f"List index out of bounds: {idx}") from exc
                    continue
                if isinstance(obj, tuple) and type(idx) is int:
                    try:
                        frame.stack.append(obj[idx])
                    except IndexError as exc:
                        raise VMError(f"Tuple index out of bounds: {idx}") from exc
                    continue
                if isinstance(obj, dict) and isinstance(idx, str):
                    if idx not in obj:
                        raise VMError(f"Missing record field '{idx}'")
                    frame.stack.append(obj[idx])
                    continue
                raise VMError("Unsupported index operation in VM backend")
            if ins.op == Op.IS_LIST:
                obj = frame.stack.pop()
                frame.stack.append(isinstance(obj, list))
                continue
            if ins.op == Op.IS_TUPLE:
                obj = frame.stack.pop()
                frame.stack.append(isinstance(obj, tuple))
                continue
            if ins.op == Op.IS_RECORD:
                obj = frame.stack.pop()
                frame.stack.append(isinstance(obj, dict))
                continue
            if ins.op == Op.LEN:
                obj = frame.stack.pop()
                if isinstance(obj, list | tuple | dict):
                    frame.stack.append(len(obj))
                    continue
                raise VMError("len() only supported on list/tuple/record in VM backend")
            if ins.op == Op.HAS_KEY:
                assert isinstance(ins.arg, int)
                key_obj = consts[ins.arg]
                if not isinstance(key_obj, str):
                    raise VMError("HAS_KEY key constant must be a string")
                obj = frame.stack.pop()
                if not isinstance(obj, dict):
                    raise VMError("HAS_KEY only supported on records in VM backend")
                frame.stack.append(key_obj in obj)
                continue
            if ins.op == Op.SLICE_FROM:
                assert isinstance(ins.arg, int)
                obj = frame.stack.pop()
                if isinstance(obj, list | tuple):
                    frame.stack.append(obj[ins.arg :])
                    continue
                raise VMError("Slice only supported on list/tuple in VM backend")
            if ins.op == Op.LOAD_GLOBAL:
                assert isinstance(ins.arg, int)
                name_obj = consts[ins.arg]
                if not isinstance(name_obj, str):
                    raise VMError("LOAD_GLOBAL name constant must be a string")
                if name_obj not in frame.globals:
                    raise VMError(f"Undefined variable '{name_obj}'")
                frame.stack.append(frame.globals[name_obj].value)
                continue
            if ins.op == Op.STORE_GLOBAL:
                assert isinstance(ins.arg, int)
                name_obj = consts[ins.arg]
                if not isinstance(name_obj, str):
                    raise VMError("STORE_GLOBAL name constant must be a string")
                cell = frame.globals.get(name_obj)
                if cell is None:
                    cell = _Cell(None)
                    frame.globals[name_obj] = cell
                cell.value = frame.stack.pop()
                continue
            if ins.op == Op.IMPORT_MODULE:
                assert isinstance(ins.arg, int)
                label_obj = consts[ins.arg]
                if not isinstance(label_obj, str):
                    raise VMError("IMPORT_MODULE label constant must be a string")
                frame.stack.append(self.import_module(label_obj))
                continue
            if ins.op == Op.SET_INDEX:
                assert isinstance(ins.arg, tuple) and len(ins.arg) == 2
                ref_kind, ref = ins.arg
                assert ref_kind in ("local", "global")
                value = frame.stack.pop()
                idx = frame.stack.pop()
                target_cell_index: _Cell
                if ref_kind == "local":
                    assert isinstance(ref, int)
                    target_cell_index = frame.locals[ref]
                else:
                    assert isinstance(ref, int)
                    name_obj = consts[ref]
                    if not isinstance(name_obj, str):
                        raise VMError("SET_INDEX global name constant must be a string")
                    gcell = frame.globals.get(name_obj)
                    if gcell is None:
                        raise VMError(f"Undefined variable '{name_obj}'")
                    target_cell_index = gcell
                obj = target_cell_index.value

                if isinstance(obj, list) and type(idx) is int:
                    if idx < 0 or idx >= len(obj):
                        raise VMError(f"List index out of bounds: {idx}")
                    new_list = list(obj)
                    new_list[idx] = value
                    target_cell_index.value = new_list
                    continue
                if isinstance(obj, dict) and isinstance(idx, str):
                    new_rec = dict(obj)
                    new_rec[idx] = value
                    target_cell_index.value = new_rec
                    continue
                raise VMError("Unsupported index assignment in VM backend")
            if ins.op == Op.SET_MEMBER:
                assert isinstance(ins.arg, tuple) and len(ins.arg) == 3
                key_k, ref_kind, ref = ins.arg
                assert isinstance(key_k, int)
                assert ref_kind in ("local", "global")
                key_obj = consts[key_k]
                if not isinstance(key_obj, str):
                    raise VMError("SET_MEMBER key constant must be a string")
                value = frame.stack.pop()
                target_cell_member: _Cell
                if ref_kind == "local":
                    assert isinstance(ref, int)
                    target_cell_member = frame.locals[ref]
                else:
                    assert isinstance(ref, int)
                    name_obj = consts[ref]
                    if not isinstance(name_obj, str):
                        raise VMError("SET_MEMBER global name constant must be a string")
                    gcell = frame.globals.get(name_obj)
                    if gcell is None:
                        raise VMError(f"Undefined variable '{name_obj}'")
                    target_cell_member = gcell
                obj = target_cell_member.value
                if not isinstance(obj, dict):
                    raise VMError("Member assignment only supported on records in VM backend")
                new_rec = dict(obj)
                new_rec[key_obj] = value
                target_cell_member.value = new_rec
                continue

            raise VMError(f"Unknown opcode: {ins.op}")

        raise VMError("Function ran off end without RETURN")

    def _call(self, name: str, args: list[object], *, module_label: str) -> object:
        bi = self._builtins.get(name)
        if bi is not None:
            arity, fn = bi
            if arity != -1 and arity != len(args):
                raise VMError(f"Builtin {name} expects {arity} args, got {len(args)}")
            return fn(args)

        target = self.program.functions.get(name)
        if target is None:
            raise VMError(f"Unknown function '{name}'")
        callee_module = name.split("::", 1)[0] if "::" in name else module_label
        return self._call_user(target, args, module_label=callee_module)

    def _call_closure(self, closure: _Closure, args: list[object], *, module_label: str) -> object:
        target = self.program.functions.get(closure.fn_id)
        if target is None:
            raise VMError(f"Unknown function '{closure.fn_id}'")
        callee_module = closure.fn_id.split("::", 1)[0] if "::" in closure.fn_id else module_label
        return self._call_user(target, args, module_label=callee_module, free=closure.free)

    def import_module(self, label: str) -> dict[str, object]:
        self._ensure_module_initialized(label)
        return self._module_exports[label]

    def _ensure_module_initialized(self, label: str) -> None:
        if label in self._module_exports:
            return
        spec = self.program.modules.get(label)
        if spec is None:
            raise VMError(f"Unknown module '{label}'")
        if label in self._initializing:
            raise VMError(f"Cyclic import detected for module '{label}'")
        self._initializing.add(label)
        try:
            env = self._module_envs.setdefault(label, {})
            # Make builtins available as callable ids in every module.
            for name in self._builtins:
                env.setdefault(name, _Cell(name))
            # Run init function.
            init_fn = self.program.functions[spec.init_fn]
            self._call_user(init_fn, [], module_label=label)
            exports: dict[str, object] = {}
            for export_name, (kind, value) in spec.exports.items():
                if kind == "fn":
                    exports[export_name] = value
                elif kind == "var":
                    cell = env.get(value)
                    exports[export_name] = None if cell is None else cell.value
                else:
                    raise VMError("Internal error: invalid export kind")
            self._module_exports[label] = exports
        finally:
            self._initializing.remove(label)

    def _binop(self, op: Op, a: object, b: object) -> object:
        if op == Op.ADD:
            if type(a) is int and type(b) is int:
                return a + b
            if type(a) is str and type(b) is str:
                return a + b
            raise VMError("Operator + only supports Int+Int or String+String in VM backend")
        if op == Op.SUB:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator - only supports Int-Int in VM backend")
            return a - b
        if op == Op.MUL:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator * only supports Int*Int in VM backend")
            return a * b
        if op == Op.DIV:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator / only supports Int/Int in VM backend")
            if b == 0:
                raise VMError("Division by zero")
            return a // b
        if op == Op.MOD:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator % only supports Int%Int in VM backend")
            if b == 0:
                raise VMError("Modulo by zero")
            return a % b
        if op == Op.EQ:
            if type(a) is not type(b):
                return False
            return a == b
        if op == Op.NE:
            if type(a) is not type(b):
                return True
            return a != b
        if op == Op.LT:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator < only supports Int<Int in VM backend")
            return a < b
        if op == Op.LE:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator <= only supports Int<=Int in VM backend")
            return a <= b
        if op == Op.GT:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator > only supports Int>Int in VM backend")
            return a > b
        if op == Op.GE:
            if type(a) is not int or type(b) is not int:
                raise VMError("Operator >= only supports Int>=Int in VM backend")
            return a >= b
        raise VMError(f"Unsupported binop {op}")


def compile_to_bytecode(source: str) -> BCProgram:
    module = parse_module(source)
    analyzer = SemanticAnalyzer(allow_external_imports=True)
    ok = analyzer.analyze(module)
    if not ok:
        msgs = "\n".join(str(e) for e in analyzer.errors)
        raise VMError(msgs)
    return _Compiler().compile_single_source(source)


def compile_path_to_bytecode(
    entry_path: Path,
    *,
    dep_overrides: dict[str, Path] | None = None,
    extra_roots: tuple[Path, ...] = (),
    resolver_config: ModuleSearchConfig | None = None,
) -> BCProgram:
    return _Compiler().compile_project(
        entry_path=entry_path,
        dep_overrides=dep_overrides,
        extra_roots=extra_roots,
        resolver_config=resolver_config,
    )


def run_source_vm(source: str) -> str:
    program = compile_to_bytecode(source)
    vm = VM(program)
    vm.run_entry()
    return "\n".join(vm.output)


def run_path_vm(
    entry_path: Path,
    *,
    dep_overrides: dict[str, Path] | None = None,
    extra_roots: tuple[Path, ...] = (),
    resolver_config: ModuleSearchConfig | None = None,
) -> str:
    program = compile_path_to_bytecode(
        entry_path,
        dep_overrides=dep_overrides,
        extra_roots=extra_roots,
        resolver_config=resolver_config,
    )
    vm = VM(program)
    vm.run_entry()
    return "\n".join(vm.output)
