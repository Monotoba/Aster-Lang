from __future__ import annotations

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
from aster_lang.vm_runtime import VM, VMError

__all__ = [
    "VM",
    "VMError",
    "compile_to_bytecode",
    "compile_path_to_bytecode",
    "run_source_vm",
    "run_path_vm",
]


class _Compiler:
    def __init__(self) -> None:
        self._consts: list[object] = []
        self._functions: dict[str, BCFunction] = {}
        self._modules: dict[str, ModuleSpec] = {}
        self._lambda_counter = 0
        # module_label -> fn_name -> per-param borrow mutability (None means not a borrow param)
        self._module_fn_param_borrows: dict[str, dict[str, list[bool | None]]] = {}

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
        self._module_fn_param_borrows[label] = {}
        for decl in module.declarations:
            if not isinstance(decl, ast.FunctionDecl):
                continue
            borrows: list[bool | None] = []
            for p in decl.params:
                if isinstance(p.type_annotation, ast.BorrowTypeExpr):
                    borrows.append(p.type_annotation.is_mutable)
                else:
                    borrows.append(None)
            self._module_fn_param_borrows[label][decl.name] = borrows

        global_mutable: dict[str, bool] = {}
        global_ref_mutable: dict[str, bool] = {}
        for decl in module.declarations:
            if isinstance(decl, ast.LetDecl):
                global_mutable[decl.name] = decl.is_mutable
                if isinstance(decl.initializer, ast.BorrowExpr):
                    global_ref_mutable[decl.name] = decl.initializer.is_mutable

        init_id = f"{label}::__init__"
        init_fn, export_spec = self._compile_module_init(
            label,
            module,
            init_id,
            global_mutable=global_mutable,
            global_ref_mutable=global_ref_mutable,
        )
        self._functions[init_id] = init_fn
        self._modules[label] = ModuleSpec(label=label, init_fn=init_id, exports=export_spec)

        for decl in module.declarations:
            if isinstance(decl, ast.FunctionDecl):
                fn_id = f"{label}::{decl.name}"
                self._functions[fn_id] = self._compile_function(
                    decl,
                    fn_id,
                    global_mutable=global_mutable,
                    global_ref_mutable=global_ref_mutable,
                )

    def _compile_module_init(
        self,
        label: str,
        module: ast.Module,
        init_id: str,
        *,
        global_mutable: dict[str, bool],
        global_ref_mutable: dict[str, bool],
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
                    type_params=[],
                    params=[],
                    return_type=None,
                    body=[ast.ReturnStmt(decl.initializer)],
                )
                expr_fn = self._compile_function(
                    fn,
                    "__expr_tmp__",
                    globals_only=True,
                    global_mutable=global_mutable,
                    global_ref_mutable=global_ref_mutable,
                )
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
        global_mutable: dict[str, bool] | None = None,
        global_ref_mutable: dict[str, bool] | None = None,
        free_mutable: set[str] | None = None,
        free_ref_mutable: set[str] | None = None,
        free_ref_slots: set[str] | None = None,
    ) -> BCFunction:
        free_map = {} if free_map is None else dict(free_map)
        global_mutable = {} if global_mutable is None else dict(global_mutable)
        global_ref_mutable = {} if global_ref_mutable is None else dict(global_ref_mutable)
        free_mutable = set() if free_mutable is None else set(free_mutable)
        free_ref_mutable = set() if free_ref_mutable is None else set(free_ref_mutable)
        free_ref_slots = set() if free_ref_slots is None else set(free_ref_slots)
        module_label = fn_id.split("::", 1)[0]
        scopes: list[dict[str, int]] = [{}]
        next_local = 0
        mut_slots: set[int] = set()  # slots allowed to be reassigned via <-
        ref_slots: set[int] = set()
        ref_mutable_slots: set[int] = set()
        # Slots initialized from borrow expressions are immutable bindings but support `p <- v`
        # by writing through the referenced cell instead of rebinding the slot.

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

        def define(
            name: str,
            *,
            is_mutable: bool = False,
            is_ref: bool = False,
            is_ref_mutable: bool = False,
        ) -> int:
            nonlocal next_local
            if name in scopes[-1]:
                raise VMError(f"Duplicate definition '{name}' in VM backend")
            idx = next_local
            next_local += 1
            scopes[-1][name] = idx
            if is_mutable:
                mut_slots.add(idx)
            if is_ref:
                ref_slots.add(idx)
                if is_ref_mutable:
                    ref_mutable_slots.add(idx)
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

        def emit_name_ref(name: str, *, ref_is_mutable: bool) -> None:
            if name in free_map:
                emit(Op.REF_FREE, (free_map[name], ref_is_mutable))
                return
            if globals_only:
                emit(Op.REF_GLOBAL, (self._const(name), ref_is_mutable))
                return
            try:
                emit(Op.REF_LOCAL, (lookup(name), ref_is_mutable))
            except VMError:
                emit(Op.REF_GLOBAL, (self._const(name), ref_is_mutable))

        def _check_mutable_borrow(name: str) -> None:
            if name in free_map:
                if name in free_ref_slots:
                    if name not in free_ref_mutable:
                        raise VMError(f"Cannot take &mut of immutable reference '{name}'")
                    return
                if name not in free_mutable:
                    raise VMError(f"Cannot take &mut of immutable variable '{name}'")
                return
            if globals_only:
                if name in global_ref_mutable:
                    if not global_ref_mutable[name]:
                        raise VMError(f"Cannot take &mut of immutable reference '{name}'")
                    return
                if not global_mutable.get(name, False):
                    raise VMError(f"Cannot take &mut of immutable variable '{name}'")
                return
            try:
                slot = lookup(name)
            except VMError:
                if name in global_ref_mutable:
                    if not global_ref_mutable[name]:
                        raise VMError(f"Cannot take &mut of immutable reference '{name}'") from None
                    return
                if not global_mutable.get(name, False):
                    raise VMError(f"Cannot take &mut of immutable variable '{name}'") from None
                return
            if slot in ref_slots:
                if slot not in ref_mutable_slots:
                    raise VMError(f"Cannot take &mut of immutable reference '{name}'")
                return
            if slot not in mut_slots:
                raise VMError(f"Cannot take &mut of immutable variable '{name}'")

        def compile_lvalue_ref(
            target: ast.Expr,
            *,
            allow_temporary_root: bool = False,
            require_mutable_base: bool = False,
            ref_is_mutable: bool = False,
        ) -> None:
            if isinstance(target, ast.Identifier):
                if require_mutable_base:
                    _check_mutable_borrow(target.name)
                emit_name_ref(target.name, ref_is_mutable=ref_is_mutable)
                return
            if isinstance(target, ast.MemberExpr):
                compile_lvalue_ref(
                    target.obj,
                    allow_temporary_root=True,
                    require_mutable_base=require_mutable_base,
                    ref_is_mutable=ref_is_mutable,
                )
                emit(Op.REF_MEMBER, self._const(target.member))
                return
            if isinstance(target, ast.IndexExpr):
                compile_lvalue_ref(
                    target.obj,
                    allow_temporary_root=True,
                    require_mutable_base=require_mutable_base,
                    ref_is_mutable=ref_is_mutable,
                )
                compile_expr(target.index)
                emit(Op.REF_INDEX)
                return
            if allow_temporary_root:
                compile_expr(target)
                emit(Op.BOX, ref_is_mutable)
                return
            raise VMError("VM backend only supports lvalue borrow and assignment targets for now")

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
            if isinstance(expr, ast.BorrowExpr):
                # Borrow expressions produce a cell reference.
                compile_lvalue_ref(
                    expr.target,
                    require_mutable_base=expr.is_mutable,
                    ref_is_mutable=expr.is_mutable,
                )
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
                    "&": Op.BIT_AND,
                    "|": Op.BIT_OR,
                    "^": Op.BIT_XOR,
                    "<<": Op.SHL,
                    ">>": Op.SHR,
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
                if expr.operator == "*":
                    # Deref is only meaningful for non-identifier operands like *(&x).
                    # Identifiers are implicitly deref'd when they contain a cell reference.
                    if isinstance(expr.operand, ast.Identifier):
                        compile_expr(expr.operand)
                        return
                    compile_expr(expr.operand)
                    emit(Op.DEREF)
                    return
                compile_expr(expr.operand)
                if expr.operator == "-":
                    emit(Op.NEG)
                    return
                if expr.operator == "not":
                    emit(Op.NOT)
                    return
                if expr.operator == "~":
                    emit(Op.BIT_NOT)
                    return
                raise VMError(f"Unsupported unary operator in VM backend: {expr.operator}")
            if isinstance(expr, ast.CallExpr):
                # Support calling identifiers and member expressions (module namespaces).
                #
                # For direct calls to module-local functions, we can compile a CALL by name and
                # pass reference arguments for &T/&mut T parameters.
                if isinstance(expr.func, ast.Identifier):
                    fn_name = expr.func.name
                    sig = self._module_fn_param_borrows.get(module_label, {}).get(fn_name)
                    if sig is not None:
                        fn_target = f"{module_label}::{fn_name}"
                        for a, borrow_mut in zip(expr.args, sig, strict=False):
                            if borrow_mut is None:
                                compile_expr(a)
                                continue
                            # Borrow parameter: pass a cell reference.
                            if isinstance(a, ast.BorrowExpr):
                                compile_expr(a)
                                continue
                            if not isinstance(a, ast.Identifier):
                                raise VMError(
                                    "Borrow arguments must be identifiers in this prototype"
                                )
                            name = a.name
                            if name in free_map:
                                emit(Op.REF_FREE, free_map[name])
                                continue
                            if globals_only:
                                emit(Op.REF_GLOBAL, self._const(name))
                                continue
                            try:
                                emit(Op.REF_LOCAL, lookup(name))
                            except VMError:
                                emit(Op.REF_GLOBAL, self._const(name))
                        emit(Op.CALL, (self._const(fn_target), len(expr.args)))
                        return

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
                        if isinstance(e, ast.BorrowExpr):
                            walk_expr(e.target)
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
                        raise VMError(f"Unsupported expression in VM backend: {type(e).__name__}")

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
                lambda_free_mutable: set[str] = set()
                lambda_free_ref_mutable: set[str] = set()
                lambda_free_ref_slots: set[str] = set()
                for name in sorted(lexical_free):
                    if name in free_map:
                        captures.append(("free", free_map[name]))
                        lambda_free_map[name] = len(captures) - 1
                        if name in free_ref_slots:
                            lambda_free_ref_slots.add(name)
                            if name in free_ref_mutable:
                                lambda_free_ref_mutable.add(name)
                        elif name in free_mutable:
                            lambda_free_mutable.add(name)
                        continue
                    try:
                        slot = lookup(name)
                    except VMError:
                        continue  # globals are read dynamically; no capture needed
                    captures.append(("local", slot))
                    lambda_free_map[name] = len(captures) - 1
                    if slot in ref_slots:
                        lambda_free_ref_slots.add(name)
                        if slot in ref_mutable_slots:
                            lambda_free_ref_mutable.add(name)
                    elif slot in mut_slots:
                        lambda_free_mutable.add(name)

                # Compile lambda body as a synthetic function.
                params = [ast.ParamDecl(p.name, p.type_annotation) for p in expr.params]
                if isinstance(expr.body, list):
                    body_stmts = list(expr.body)
                else:
                    body_stmts = [ast.ReturnStmt(expr.body)]
                fn_decl = ast.FunctionDecl(
                    name=lambda_id,
                    type_params=[],
                    params=params,
                    return_type=None,
                    body=body_stmts,
                )
                self._functions[lambda_id] = self._compile_function(
                    fn_decl,
                    lambda_id,
                    globals_only=False,
                    free_map=lambda_free_map,
                    global_mutable=global_mutable,
                    global_ref_mutable=global_ref_mutable,
                    free_mutable=lambda_free_mutable,
                    free_ref_mutable=lambda_free_ref_mutable,
                    free_ref_slots=lambda_free_ref_slots,
                )

                # Build closure: push captured cell refs, then MAKE_CLOSURE.
                for kind, ref in captures:
                    if kind == "local":
                        emit(Op.REF_LOCAL, (ref, None))
                    elif kind == "free":
                        emit(Op.REF_FREE, (ref, None))
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
                    is_ref = isinstance(stmt.initializer, ast.BorrowExpr)
                    is_ref_mutable = (
                        stmt.initializer.is_mutable
                        if isinstance(stmt.initializer, ast.BorrowExpr)
                        else False
                    )
                    emit(
                        Op.STORE,
                        define(
                            stmt.pattern.name,
                            is_mutable=stmt.is_mutable,
                            is_ref=is_ref,
                            is_ref_mutable=is_ref_mutable,
                        ),
                    )
                else:
                    src_slot = alloc_temp()
                    emit(Op.STORE, src_slot)
                    _compile_destructure(stmt.pattern, src_slot, is_mutable=stmt.is_mutable)
                return

            def _emit_store_name(name: str) -> None:
                if name in free_map:
                    if name in free_ref_slots:
                        if name not in free_ref_mutable:
                            raise VMError(f"Cannot assign through immutable reference '{name}'")
                        emit(Op.STORE_FREE, free_map[name])
                        return
                    if name not in free_mutable:
                        raise VMError(f"Cannot assign to immutable binding '{name}'")
                    emit(Op.STORE_FREE, free_map[name])
                    return
                try:
                    slot = lookup(name)
                    if slot not in mut_slots and slot not in ref_slots:
                        raise VMError(f"Cannot assign to immutable binding '{name}'")
                    if slot in ref_slots and slot not in ref_mutable_slots:
                        raise VMError(f"Cannot assign through immutable reference '{name}'")
                    emit(Op.STORE, slot)
                    return
                except VMError as exc:
                    if "immutable" in str(exc):
                        raise
                    if name in global_ref_mutable and not global_ref_mutable[name]:
                        raise VMError(
                            f"Cannot assign through immutable reference '{name}'"
                        ) from None
                    if name in global_mutable and not global_mutable[name]:
                        raise VMError(f"Cannot assign to immutable variable '{name}'") from None
                    emit(Op.STORE_GLOBAL, self._const(name))
                    return

            if isinstance(stmt, ast.AssignStmt):
                if isinstance(stmt.target, ast.Identifier):
                    compile_expr(stmt.value)
                    _emit_store_name(stmt.target.name)
                    return
                if isinstance(stmt.target, ast.UnaryExpr) and stmt.target.operator == "*":
                    # Deref assignment: *p <- v
                    op = stmt.target.operand
                    if isinstance(op, ast.Identifier):
                        # Same behavior as `p <- v` in the implicit-deref model.
                        compile_expr(stmt.value)
                        _emit_store_name(op.name)
                        return
                    compile_expr(op)  # push cell
                    compile_expr(stmt.value)  # push value
                    emit(Op.STORE_DEREF)
                    return
                if isinstance(stmt.target, ast.MemberExpr):
                    compile_lvalue_ref(
                        stmt.target,
                        require_mutable_base=True,
                        ref_is_mutable=True,
                    )
                    compile_expr(stmt.value)
                    emit(Op.STORE_DEREF)
                    return
                if isinstance(stmt.target, ast.IndexExpr):
                    compile_lvalue_ref(
                        stmt.target,
                        require_mutable_base=True,
                        ref_is_mutable=True,
                    )
                    compile_expr(stmt.value)
                    emit(Op.STORE_DEREF)
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
                            f"Unsupported match pattern in VM backend: {type(pattern).__name__}"
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
