"""Interpreter for the Aster language.

This module provides runtime execution for Aster programs.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aster_lang import ast
from aster_lang.module_resolution import ModuleResolutionError, resolve_module_path
from aster_lang.parser import parse_module

# Runtime Values


@dataclass(frozen=True)
class Value:
    """Base class for runtime values."""

    pass


@dataclass(frozen=True)
class IntValue(Value):
    """Integer value."""

    value: int

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class StringValue(Value):
    """String value."""

    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class BoolValue(Value):
    """Boolean value."""

    value: bool

    def __str__(self) -> str:
        return "true" if self.value else "false"


@dataclass(frozen=True)
class NilValue(Value):
    """Nil value."""

    def __str__(self) -> str:
        return "nil"


@dataclass(frozen=True)
class ListValue(Value):
    """List value."""

    elements: tuple[Value, ...]

    def __str__(self) -> str:
        elements_str = ", ".join(str(e) for e in self.elements)
        return f"[{elements_str}]"


@dataclass(frozen=True)
class TupleValue(Value):
    """Tuple value."""

    elements: tuple[Value, ...]

    def __str__(self) -> str:
        elements_str = ", ".join(str(e) for e in self.elements)
        return f"({elements_str})"


@dataclass(frozen=True)
class RecordValue(Value):
    """Record value."""

    fields: dict[str, Value]

    def __str__(self) -> str:
        fields_str = ", ".join(f"{k}: {v}" for k, v in self.fields.items())
        return f"{{{fields_str}}}"


@dataclass(frozen=True)
class ModuleValue(Value):
    """Module namespace value."""

    name: str
    exports: dict[str, Value]

    def __str__(self) -> str:
        return f"<module {self.name}>"


@dataclass(frozen=True)
class FunctionValue(Value):
    """Function value with closure."""

    params: tuple[str, ...]
    body: tuple[ast.Stmt, ...]
    closure: Any  # Environment (can't be frozen, so use Any)

    def __str__(self) -> str:
        return "<function>"


@dataclass(frozen=True)
class BuiltinFunction(Value):
    """Built-in function.

    ``func`` receives the full argument list; ``arity`` is the expected count
    (-1 means variadic).
    """

    name: str
    func: Callable[[list[Value]], Value]
    arity: int = -1

    def __str__(self) -> str:
        return f"<builtin {self.name}>"


NIL = NilValue()


# Runtime Errors


class InterpreterError(Exception):
    """Runtime error during interpretation."""

    def __init__(self, message: str, node: ast.Node | None = None) -> None:
        super().__init__(message)
        self.node = node


class ReturnException(Exception):
    """Exception used for return statement control flow."""

    def __init__(self, value: Value) -> None:
        self.value = value


class BreakException(Exception):
    """Exception used for break statement control flow."""

    pass


class ContinueException(Exception):
    """Exception used for continue statement control flow."""

    pass


# Environment


class Environment:
    """Runtime environment for variable bindings."""

    def __init__(self, parent: Environment | None = None) -> None:
        self.parent = parent
        self.bindings: dict[str, Value] = {}
        self.mutable: set[str] = set()  # Track which variables are mutable

    def define(self, name: str, value: Value, is_mutable: bool = False) -> None:
        """Define a new variable."""
        self.bindings[name] = value
        if is_mutable:
            self.mutable.add(name)

    def get(self, name: str) -> Value:
        """Get a variable value."""
        if name in self.bindings:
            return self.bindings[name]
        if self.parent:
            return self.parent.get(name)
        raise InterpreterError(f"Undefined variable '{name}'")

    def set(self, name: str, value: Value) -> None:
        """Set a variable value (mutation)."""
        if name in self.bindings:
            if name not in self.mutable:
                raise InterpreterError(f"Cannot assign to immutable variable '{name}'")
            self.bindings[name] = value
            return
        if self.parent:
            self.parent.set(name, value)
            return
        raise InterpreterError(f"Undefined variable '{name}'")

    def create_child(self) -> Environment:
        """Create a child environment."""
        return Environment(parent=self)


# Interpreter


class Interpreter:
    """Interpreter for Aster programs."""

    def __init__(
        self,
        *,
        base_dir: Path | None = None,
        dep_overrides: dict[str, Path] | None = None,
        extra_roots: tuple[Path, ...] = (),
        module_cache: dict[Path, ModuleValue] | None = None,
        loading_modules: set[Path] | None = None,
        output: list[str] | None = None,
    ) -> None:
        self.base_dir = base_dir
        self.dep_overrides: dict[str, Path] = dep_overrides or {}
        self.extra_roots: tuple[Path, ...] = extra_roots
        self.module_cache = {} if module_cache is None else module_cache
        self.loading_modules = set() if loading_modules is None else loading_modules
        self.global_env = Environment()
        self.current_env = self.global_env
        self.output = [] if output is None else output
        self._initialize_builtins()

    def _initialize_builtins(self) -> None:
        """Initialize built-in functions."""

        def builtin_print(args: list[Value]) -> Value:
            self.output.append(str(args[0]))
            return NIL

        def builtin_str(args: list[Value]) -> Value:
            return StringValue(str(args[0]))

        def builtin_int(args: list[Value]) -> Value:
            arg = args[0]
            if isinstance(arg, IntValue):
                return arg
            if isinstance(arg, StringValue):
                try:
                    return IntValue(int(arg.value))
                except ValueError as exc:
                    raise InterpreterError(f"Cannot convert {arg.value!r} to Int") from exc
            if isinstance(arg, BoolValue):
                return IntValue(1 if arg.value else 0)
            raise InterpreterError(f"Cannot convert {type(arg).__name__} to Int")

        def builtin_len(args: list[Value]) -> Value:
            arg = args[0]
            if isinstance(arg, StringValue):
                return IntValue(len(arg.value))
            if isinstance(arg, ListValue):
                return IntValue(len(arg.elements))
            if isinstance(arg, TupleValue):
                return IntValue(len(arg.elements))
            raise InterpreterError(f"len() not supported for {type(arg).__name__}")

        def builtin_abs(args: list[Value]) -> Value:
            arg = args[0]
            if not isinstance(arg, IntValue):
                raise InterpreterError("abs() requires an integer")
            return IntValue(abs(arg.value))

        def builtin_max(args: list[Value]) -> Value:
            a, b = args[0], args[1]
            if not isinstance(a, IntValue) or not isinstance(b, IntValue):
                raise InterpreterError("max() requires integers")
            return IntValue(max(a.value, b.value))

        def builtin_min(args: list[Value]) -> Value:
            a, b = args[0], args[1]
            if not isinstance(a, IntValue) or not isinstance(b, IntValue):
                raise InterpreterError("min() requires integers")
            return IntValue(min(a.value, b.value))

        def builtin_range(args: list[Value]) -> Value:
            if len(args) == 1:
                n = args[0]
                if not isinstance(n, IntValue):
                    raise InterpreterError("range() requires integers")
                return ListValue(tuple(IntValue(i) for i in range(n.value)))
            if len(args) == 2:
                start, stop = args[0], args[1]
                if not isinstance(start, IntValue) or not isinstance(stop, IntValue):
                    raise InterpreterError("range() requires integers")
                return ListValue(tuple(IntValue(i) for i in range(start.value, stop.value)))
            raise InterpreterError(f"range() takes 1 or 2 arguments, got {len(args)}")

        self.global_env.define("print", BuiltinFunction("print", builtin_print, arity=1))
        self.global_env.define("str", BuiltinFunction("str", builtin_str, arity=1))
        self.global_env.define("int", BuiltinFunction("int", builtin_int, arity=1))
        self.global_env.define("len", BuiltinFunction("len", builtin_len, arity=1))
        self.global_env.define("abs", BuiltinFunction("abs", builtin_abs, arity=1))
        self.global_env.define("max", BuiltinFunction("max", builtin_max, arity=2))
        self.global_env.define("min", BuiltinFunction("min", builtin_min, arity=2))
        self.global_env.define("range", BuiltinFunction("range", builtin_range, arity=-1))

    def interpret(self, module: ast.Module, *, auto_call_main: bool = True) -> None:
        """Interpret a module."""
        for decl in module.declarations:
            self.execute_declaration(decl)

        # If main() function exists, call it
        if not auto_call_main:
            return

        main_func = None
        with suppress(InterpreterError):
            main_func = self.current_env.get("main")

        is_callable_main = (
            main_func is not None
            and isinstance(main_func, FunctionValue)
            and len(main_func.params) == 0
        )
        if is_callable_main:
            assert isinstance(main_func, FunctionValue)  # For mypy
            func_env = main_func.closure.create_child()
            saved_env = self.current_env
            self.current_env = func_env
            try:
                for stmt in main_func.body:
                    self.execute_statement(stmt)
            except ReturnException:
                pass  # main() returned
            finally:
                self.current_env = saved_env

    def execute_declaration(self, decl: ast.Decl) -> None:
        """Execute a declaration."""
        if isinstance(decl, ast.FunctionDecl):
            self.execute_function_decl(decl)
        elif isinstance(decl, ast.LetDecl):
            value = self.evaluate_expr(decl.initializer)
            self.current_env.define(decl.name, value, decl.is_mutable)
        elif isinstance(decl, ast.ImportDecl):
            self.execute_import_decl(decl)
        elif isinstance(decl, ast.TypeAliasDecl):
            # Type aliases are compile-time only
            pass

    def execute_function_decl(self, decl: ast.FunctionDecl) -> None:
        """Execute a function declaration."""
        param_names = tuple(p.name for p in decl.params)
        func = FunctionValue(params=param_names, body=tuple(decl.body), closure=self.current_env)
        self.current_env.define(decl.name, func)

    def execute_import_decl(self, decl: ast.ImportDecl) -> None:
        """Execute an import declaration."""
        module_value = self._load_module(decl.module)

        if decl.imports:
            for name in decl.imports:
                if name not in module_value.exports:
                    raise InterpreterError(
                        f"Module '{module_value.name}' has no public export '{name}'",
                        decl,
                    )
                self.current_env.define(name, module_value.exports[name])
            return

        binding_name = decl.alias if decl.alias is not None else decl.module.parts[-1]
        self.current_env.define(binding_name, module_value)

    def _load_module(self, module_name: ast.QualifiedName) -> ModuleValue:
        """Load a module from a sibling .aster file."""
        module_path = self._resolve_module_path(module_name)
        if module_path in self.module_cache:
            return self.module_cache[module_path]
        if module_path in self.loading_modules:
            module_label = ".".join(module_name.parts)
            raise InterpreterError(f"Cyclic import detected for module '{module_label}'")

        self.loading_modules.add(module_path)
        try:
            source = module_path.read_text(encoding="utf-8")
            module = parse_module(source)
            module_interpreter = Interpreter(
                base_dir=module_path.parent,
                module_cache=self.module_cache,
                loading_modules=self.loading_modules,
                output=self.output,
            )
            module_interpreter.interpret(module, auto_call_main=False)

            exports: dict[str, Value] = {}
            for decl in module.declarations:
                export_name = self._export_name(decl)
                if export_name is None:
                    continue
                exports[export_name] = module_interpreter.global_env.get(export_name)

            module_value = ModuleValue(".".join(module_name.parts), exports)
            self.module_cache[module_path] = module_value
            return module_value
        finally:
            self.loading_modules.remove(module_path)

    def _resolve_module_path(self, module_name: ast.QualifiedName) -> Path:
        """Resolve a dotted module name from the current base directory."""
        try:
            return resolve_module_path(
                self.base_dir,
                module_name.parts,
                dep_overrides=self.dep_overrides or None,
                extra_roots=self.extra_roots,
            )
        except ModuleResolutionError as exc:
            raise InterpreterError(str(exc)) from exc

    def _export_name(self, decl: ast.Decl) -> str | None:
        """Return the runtime export name for a declaration."""
        if isinstance(decl, ast.FunctionDecl | ast.LetDecl) and decl.is_public:
            return decl.name
        return None

    def execute_statement(self, stmt: ast.Stmt) -> None:
        """Execute a statement."""
        if isinstance(stmt, ast.LetStmt):
            value = self.evaluate_expr(stmt.initializer)
            self._bind_pattern(stmt.pattern, value, stmt.is_mutable, stmt)

        elif isinstance(stmt, ast.AssignStmt):
            value = self.evaluate_expr(stmt.value)
            if isinstance(stmt.target, ast.Identifier):
                self.current_env.set(stmt.target.name, value)
                return

            if isinstance(stmt.target, ast.MemberExpr):
                # Only support `x.field <- v` where x is an identifier.
                if not isinstance(stmt.target.obj, ast.Identifier):
                    raise InterpreterError(
                        "Member assignment only supported on identifier receivers",
                        stmt,
                    )
                base = stmt.target.obj.name
                base_val = self.current_env.get(base)
                if not isinstance(base_val, RecordValue):
                    got = type(base_val).__name__
                    raise InterpreterError(f"Member assignment requires a record, got {got}", stmt)
                new_fields = dict(base_val.fields)
                new_fields[stmt.target.member] = value
                self.current_env.set(base, RecordValue(new_fields))
                return

            if isinstance(stmt.target, ast.IndexExpr):
                # Only support `x[i] <- v` where x is an identifier.
                if not isinstance(stmt.target.obj, ast.Identifier):
                    raise InterpreterError(
                        "Index assignment only supported on identifier receivers",
                        stmt,
                    )
                base = stmt.target.obj.name
                base_val = self.current_env.get(base)
                idx_val = self.evaluate_expr(stmt.target.index)
                if isinstance(base_val, ListValue) and isinstance(idx_val, IntValue):
                    idx = idx_val.value
                    if idx < 0 or idx >= len(base_val.elements):
                        raise InterpreterError(f"List index out of bounds: {idx}", stmt)
                    elems = list(base_val.elements)
                    elems[idx] = value
                    self.current_env.set(base, ListValue(tuple(elems)))
                    return
                if isinstance(base_val, RecordValue) and isinstance(idx_val, StringValue):
                    new_fields = dict(base_val.fields)
                    new_fields[idx_val.value] = value
                    self.current_env.set(base, RecordValue(new_fields))
                    return
                got_obj = type(base_val).__name__
                got_idx = type(idx_val).__name__
                raise InterpreterError(
                    f"Unsupported index assignment: {got_obj}[{got_idx}]",
                    stmt,
                )

            raise InterpreterError("Unsupported assignment target", stmt)

        elif isinstance(stmt, ast.ReturnStmt):
            value = self.evaluate_expr(stmt.value) if stmt.value else NIL
            raise ReturnException(value)

        elif isinstance(stmt, ast.IfStmt):
            condition = self.evaluate_expr(stmt.condition)
            if not isinstance(condition, BoolValue):
                cond_type = type(condition).__name__
                raise InterpreterError(f"If condition must be Bool, got {cond_type}", stmt)

            if condition.value:
                self.execute_block(stmt.then_block)
            elif stmt.else_block:
                self.execute_block(stmt.else_block)

        elif isinstance(stmt, ast.WhileStmt):
            while True:
                condition = self.evaluate_expr(stmt.condition)
                if not isinstance(condition, BoolValue):
                    cond_type = type(condition).__name__
                    raise InterpreterError(f"While condition must be Bool, got {cond_type}", stmt)

                if not condition.value:
                    break

                try:
                    self.execute_block(stmt.body)
                except BreakException:
                    break
                except ContinueException:
                    continue

        elif isinstance(stmt, ast.ForStmt):
            iterable = self.evaluate_expr(stmt.iterable)
            if not isinstance(iterable, ListValue):
                iter_type = type(iterable).__name__
                raise InterpreterError(f"For loop requires iterable, got {iter_type}", stmt)

            # Enter loop scope
            self.current_env = self.current_env.create_child()
            try:
                for element in iterable.elements:
                    self.current_env.define(stmt.variable, element)
                    try:
                        for s in stmt.body:
                            self.execute_statement(s)
                    except BreakException:
                        break
                    except ContinueException:
                        continue
            finally:
                # Exit loop scope
                assert self.current_env.parent is not None
                self.current_env = self.current_env.parent

        elif isinstance(stmt, ast.BreakStmt):
            raise BreakException()

        elif isinstance(stmt, ast.ContinueStmt):
            raise ContinueException()

        elif isinstance(stmt, ast.MatchStmt):
            self._execute_match(stmt)

        elif isinstance(stmt, ast.ExprStmt):
            self.evaluate_expr(stmt.expr)

    def _execute_match(self, stmt: ast.MatchStmt) -> None:
        """Execute a match statement."""
        subject = self.evaluate_expr(stmt.subject)
        for arm in stmt.arms:
            bindings: dict[str, Value] = {}
            matched = self._match_pattern(arm.pattern, subject, bindings)
            if matched:
                self.current_env = self.current_env.create_child()
                try:
                    for binding_name, binding_value in bindings.items():
                        self.current_env.define(binding_name, binding_value, is_mutable=False)
                    for s in arm.body:
                        self.execute_statement(s)
                finally:
                    assert self.current_env.parent is not None
                    self.current_env = self.current_env.parent
                return
        # No arm matched — no error, execution continues

    def _match_pattern(
        self,
        pattern: ast.Pattern,
        value: Value,
        bindings: dict[str, Value],
    ) -> bool:
        """Return whether a pattern matches and populate any bindings."""
        if isinstance(pattern, ast.WildcardPattern):
            return True
        if isinstance(pattern, ast.BindingPattern):
            bindings[pattern.name] = value
            return True
        if isinstance(pattern, ast.OrPattern):
            checkpoint = dict(bindings)
            for alternative in pattern.alternatives:
                trial_bindings = dict(checkpoint)
                if self._match_pattern(alternative, value, trial_bindings):
                    bindings.clear()
                    bindings.update(trial_bindings)
                    return True
            bindings.clear()
            bindings.update(checkpoint)
            return False
        if isinstance(pattern, ast.RestPattern):
            bindings[pattern.name] = value
            return True
        if isinstance(pattern, ast.LiteralPattern):
            lit = pattern.literal
            if isinstance(lit, ast.IntegerLiteral):
                return isinstance(value, IntValue) and value.value == lit.value
            if isinstance(lit, ast.StringLiteral):
                return isinstance(value, StringValue) and value.value == lit.value
            if isinstance(lit, ast.BoolLiteral):
                return isinstance(value, BoolValue) and value.value == lit.value
            if isinstance(lit, ast.NilLiteral):
                return isinstance(value, NilValue)
        if isinstance(pattern, ast.TuplePattern):
            if not isinstance(value, TupleValue):
                return False
            rest_index = self._rest_index(pattern.elements)
            if rest_index is None and len(pattern.elements) != len(value.elements):
                return False
            if rest_index is not None and len(value.elements) < len(pattern.elements) - 1:
                return False

            checkpoint = dict(bindings)
            if rest_index is None:
                for subpattern, subvalue in zip(pattern.elements, value.elements, strict=False):
                    if not self._match_pattern(subpattern, subvalue, bindings):
                        bindings.clear()
                        bindings.update(checkpoint)
                        return False
            else:
                prefix = pattern.elements[:rest_index]
                suffix = pattern.elements[rest_index + 1 :]
                for subpattern, subvalue in zip(prefix, value.elements[:rest_index], strict=False):
                    if not self._match_pattern(subpattern, subvalue, bindings):
                        bindings.clear()
                        bindings.update(checkpoint)
                        return False
                tuple_rest_value = TupleValue(
                    value.elements[rest_index : len(value.elements) - len(suffix)]
                )
                if not self._match_pattern(
                    pattern.elements[rest_index],
                    tuple_rest_value,
                    bindings,
                ):
                    bindings.clear()
                    bindings.update(checkpoint)
                    return False
                suffix_values = value.elements[len(value.elements) - len(suffix) :]
                for subpattern, subvalue in zip(suffix, suffix_values, strict=False):
                    if not self._match_pattern(subpattern, subvalue, bindings):
                        bindings.clear()
                        bindings.update(checkpoint)
                        return False
            return True
        if isinstance(pattern, ast.ListPattern):
            if not isinstance(value, ListValue):
                return False
            rest_index = self._rest_index(pattern.elements)
            if rest_index is None and len(pattern.elements) != len(value.elements):
                return False
            if rest_index is not None and len(value.elements) < len(pattern.elements) - 1:
                return False

            checkpoint = dict(bindings)
            if rest_index is None:
                for subpattern, subvalue in zip(pattern.elements, value.elements, strict=False):
                    if not self._match_pattern(subpattern, subvalue, bindings):
                        bindings.clear()
                        bindings.update(checkpoint)
                        return False
            else:
                prefix = pattern.elements[:rest_index]
                suffix = pattern.elements[rest_index + 1 :]
                for subpattern, subvalue in zip(prefix, value.elements[:rest_index], strict=False):
                    if not self._match_pattern(subpattern, subvalue, bindings):
                        bindings.clear()
                        bindings.update(checkpoint)
                        return False
                list_rest_value = ListValue(
                    value.elements[rest_index : len(value.elements) - len(suffix)]
                )
                if not self._match_pattern(
                    pattern.elements[rest_index],
                    list_rest_value,
                    bindings,
                ):
                    bindings.clear()
                    bindings.update(checkpoint)
                    return False
                suffix_values = value.elements[len(value.elements) - len(suffix) :]
                for subpattern, subvalue in zip(suffix, suffix_values, strict=False):
                    if not self._match_pattern(subpattern, subvalue, bindings):
                        bindings.clear()
                        bindings.update(checkpoint)
                        return False
            return True
        if isinstance(pattern, ast.RecordPattern):
            if not isinstance(value, RecordValue):
                return False

            checkpoint = dict(bindings)
            for field in pattern.fields:
                if field.name not in value.fields:
                    bindings.clear()
                    bindings.update(checkpoint)
                    return False
                if not self._match_pattern(field.pattern, value.fields[field.name], bindings):
                    bindings.clear()
                    bindings.update(checkpoint)
                    return False
            return True
        return False

    def _rest_index(self, elements: list[ast.Pattern]) -> int | None:
        """Return the index of a rest pattern if one is present."""
        for index, element in enumerate(elements):
            if isinstance(element, ast.RestPattern):
                return index
        return None

    def _bind_pattern(
        self,
        pattern: ast.Pattern,
        value: Value,
        is_mutable: bool,
        node: ast.Node,
    ) -> None:
        """Bind a value to a local binding pattern."""
        bindings: dict[str, Value] = {}
        if not self._match_pattern(pattern, value, bindings):
            raise InterpreterError("Binding pattern does not match initializer", node)
        for name, bound_value in bindings.items():
            self.current_env.define(name, bound_value, is_mutable)

    def execute_block(self, statements: list[ast.Stmt]) -> None:
        """Execute a block of statements."""
        # Enter new scope
        self.current_env = self.current_env.create_child()
        try:
            for stmt in statements:
                self.execute_statement(stmt)
        finally:
            # Exit scope
            assert self.current_env.parent is not None
            self.current_env = self.current_env.parent

    def evaluate_expr(self, expr: ast.Expr) -> Value:
        """Evaluate an expression."""
        if isinstance(expr, ast.IntegerLiteral):
            return IntValue(expr.value)

        elif isinstance(expr, ast.StringLiteral):
            return StringValue(expr.value)

        elif isinstance(expr, ast.BoolLiteral):
            return BoolValue(expr.value)

        elif isinstance(expr, ast.NilLiteral):
            return NIL

        elif isinstance(expr, ast.Identifier):
            return self.current_env.get(expr.name)

        elif isinstance(expr, ast.LambdaExpr):
            param_names = tuple(p.name for p in expr.params)
            # Expression lambdas implicitly return the expression value.
            body = tuple(expr.body) if isinstance(expr.body, list) else (ast.ReturnStmt(expr.body),)
            return FunctionValue(params=param_names, body=body, closure=self.current_env)

        elif isinstance(expr, ast.BinaryExpr):
            return self.evaluate_binary_expr(expr)

        elif isinstance(expr, ast.UnaryExpr):
            return self.evaluate_unary_expr(expr)

        elif isinstance(expr, ast.CallExpr):
            return self.evaluate_call_expr(expr)

        elif isinstance(expr, ast.ListExpr):
            elements = tuple(self.evaluate_expr(e) for e in expr.elements)
            return ListValue(elements)

        elif isinstance(expr, ast.TupleExpr):
            elements = tuple(self.evaluate_expr(e) for e in expr.elements)
            return TupleValue(elements)

        elif isinstance(expr, ast.RecordExpr):
            fields = {f.name: self.evaluate_expr(f.value) for f in expr.fields}
            return RecordValue(fields)

        elif isinstance(expr, ast.ParenExpr):
            return self.evaluate_expr(expr.expr)

        elif isinstance(expr, ast.MemberExpr):
            obj = self.evaluate_expr(expr.obj)
            if isinstance(obj, RecordValue):
                if expr.member not in obj.fields:
                    raise InterpreterError(f"Record has no field '{expr.member}'", expr)
                return obj.fields[expr.member]
            if isinstance(obj, ModuleValue):
                if expr.member not in obj.exports:
                    raise InterpreterError(
                        f"Module '{obj.name}' has no export '{expr.member}'",
                        expr,
                    )
                return obj.exports[expr.member]
            raise InterpreterError(f"Cannot access member of {type(obj).__name__}", expr)

        elif isinstance(expr, ast.IndexExpr):
            obj = self.evaluate_expr(expr.obj)
            index = self.evaluate_expr(expr.index)

            if isinstance(obj, ListValue) and isinstance(index, IntValue):
                idx = index.value
                if idx < 0 or idx >= len(obj.elements):
                    raise InterpreterError(f"List index out of bounds: {idx}", expr)
                return obj.elements[idx]
            elif isinstance(obj, TupleValue) and isinstance(index, IntValue):
                idx = index.value
                if idx < 0 or idx >= len(obj.elements):
                    raise InterpreterError(f"Tuple index out of bounds: {idx}", expr)
                return obj.elements[idx]
            obj_type = type(obj).__name__
            index_type = type(index).__name__
            raise InterpreterError(f"Cannot index {obj_type} with {index_type}", expr)

        raise InterpreterError(f"Unsupported expression type: {type(expr).__name__}", expr)

    def evaluate_binary_expr(self, expr: ast.BinaryExpr) -> Value:
        """Evaluate a binary expression."""
        if expr.operator == "and":
            left = self.evaluate_expr(expr.left)
            if not isinstance(left, BoolValue):
                raise InterpreterError("Logical operators require booleans", expr)
            if not left.value:
                return BoolValue(False)
            right = self.evaluate_expr(expr.right)
            if not isinstance(right, BoolValue):
                raise InterpreterError("Logical operators require booleans", expr)
            return BoolValue(right.value)

        if expr.operator == "or":
            left = self.evaluate_expr(expr.left)
            if not isinstance(left, BoolValue):
                raise InterpreterError("Logical operators require booleans", expr)
            if left.value:
                return BoolValue(True)
            right = self.evaluate_expr(expr.right)
            if not isinstance(right, BoolValue):
                raise InterpreterError("Logical operators require booleans", expr)
            return BoolValue(right.value)

        left = self.evaluate_expr(expr.left)
        right = self.evaluate_expr(expr.right)

        # Arithmetic operators
        if expr.operator in ("+", "-", "*", "/", "%"):
            # String concatenation
            if expr.operator == "+" and isinstance(left, StringValue):
                if isinstance(right, StringValue):
                    return StringValue(left.value + right.value)
                raise InterpreterError("String + requires a string on the right", expr)
            if not isinstance(left, IntValue) or not isinstance(right, IntValue):
                raise InterpreterError("Arithmetic requires integers (or strings for +)", expr)

            if expr.operator == "+":
                return IntValue(left.value + right.value)
            elif expr.operator == "-":
                return IntValue(left.value - right.value)
            elif expr.operator == "*":
                return IntValue(left.value * right.value)
            elif expr.operator == "/":
                if right.value == 0:
                    raise InterpreterError("Division by zero", expr)
                return IntValue(left.value // right.value)
            elif expr.operator == "%":
                if right.value == 0:
                    raise InterpreterError("Modulo by zero", expr)
                return IntValue(left.value % right.value)

        # Comparison operators
        elif expr.operator in ("<", "<=", ">", ">="):
            if not isinstance(left, IntValue) or not isinstance(right, IntValue):
                raise InterpreterError("Comparison requires integers", expr)

            if expr.operator == "<":
                return BoolValue(left.value < right.value)
            elif expr.operator == "<=":
                return BoolValue(left.value <= right.value)
            elif expr.operator == ">":
                return BoolValue(left.value > right.value)
            elif expr.operator == ">=":
                return BoolValue(left.value >= right.value)

        # Equality operators
        elif expr.operator in ("==", "!="):
            equal = self.values_equal(left, right)
            return BoolValue(equal if expr.operator == "==" else not equal)

        raise InterpreterError(f"Unknown binary operator: {expr.operator}", expr)

    def evaluate_unary_expr(self, expr: ast.UnaryExpr) -> Value:
        """Evaluate a unary expression."""
        operand = self.evaluate_expr(expr.operand)

        if expr.operator == "-":
            if not isinstance(operand, IntValue):
                raise InterpreterError("Negation requires integer", expr)
            return IntValue(-operand.value)

        elif expr.operator == "not":
            if not isinstance(operand, BoolValue):
                raise InterpreterError("Logical not requires boolean", expr)
            return BoolValue(not operand.value)

        raise InterpreterError(f"Unknown unary operator: {expr.operator}", expr)

    def evaluate_call_expr(self, expr: ast.CallExpr) -> Value:
        """Evaluate a function call."""
        func = self.evaluate_expr(expr.func)

        # Evaluate arguments
        args = [self.evaluate_expr(arg) for arg in expr.args]

        # Built-in function
        if isinstance(func, BuiltinFunction):
            if func.arity >= 0 and len(args) != func.arity:
                msg = f"Built-in {func.name} expects {func.arity} argument(s), got {len(args)}"
                raise InterpreterError(msg, expr)
            return func.func(args)

        # User-defined function
        elif isinstance(func, FunctionValue):
            if len(args) != len(func.params):
                msg = f"Function expects {len(func.params)} arguments, got {len(args)}"
                raise InterpreterError(msg, expr)

            # Create new environment for function execution
            func_env = func.closure.create_child()
            for param, arg in zip(func.params, args, strict=False):
                func_env.define(param, arg)

            # Execute function body
            saved_env = self.current_env
            self.current_env = func_env
            try:
                for stmt in func.body:
                    self.execute_statement(stmt)
                # If no return statement, return nil
                return NIL
            except ReturnException as ret:
                return ret.value
            finally:
                self.current_env = saved_env

        raise InterpreterError(f"Cannot call {type(func).__name__}", expr)

    def values_equal(self, left: Value, right: Value) -> bool:
        """Check if two values are equal."""
        if type(left) is not type(right):
            return False

        if isinstance(left, IntValue | StringValue | BoolValue):
            return left.value == right.value  # type: ignore
        elif isinstance(left, NilValue):
            return True
        # TODO: Implement equality for lists, tuples, records

        return False


@dataclass(slots=True)
class InterpretationResult:
    """Result of interpreting a program."""

    output: str = ""
    error: str | None = None


def interpret_source(
    source: str,
    *,
    base_dir: Path | None = None,
    dep_overrides: dict[str, Path] | None = None,
    extra_roots: tuple[Path, ...] = (),
) -> InterpretationResult:
    """Interpret Aster source code."""
    try:
        module = parse_module(source)
        interpreter = Interpreter(
            base_dir=base_dir,
            dep_overrides=dep_overrides,
            extra_roots=extra_roots,
        )
        interpreter.interpret(module)
        output = "\n".join(interpreter.output)
        return InterpretationResult(output=output)
    except InterpreterError as e:
        return InterpretationResult(error=str(e))
    except Exception as e:
        return InterpretationResult(error=f"Internal error: {e}")
