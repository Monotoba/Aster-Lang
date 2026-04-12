"""Interpreter for the Aster language.

This module provides runtime execution for Aster programs.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

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
class BitsValue(Value):
    """Fixed-width unsigned integer value (Nibble/Byte/Word/DWord/QWord)."""

    bits: int
    value: int

    def __post_init__(self) -> None:
        mask = (1 << self.bits) - 1
        object.__setattr__(self, "value", self.value & mask)

    def __str__(self) -> str:
        # Print as a plain number by default to keep the language feel lightweight.
        return str(self.value)

    @property
    def mask(self) -> int:
        return (1 << self.bits) - 1


def _bits_from_name(type_name: str) -> int | None:
    return {
        "Nibble": 4,
        "Byte": 8,
        "Word": 16,
        "DWord": 32,
        "QWord": 64,
    }.get(type_name)


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
    param_type_annotations: tuple[ast.TypeExpr | None, ...]
    body: tuple[ast.Stmt, ...]
    closure: Any  # Environment (can't be frozen, so use Any)

    def __str__(self) -> str:
        return "<function>"


class RefValue(Value):
    """A runtime reference (to a binding, member, or indexed slot)."""

    is_mutable: bool

    def read(self) -> Value:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError

    def write(self, value: Value) -> None:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError

    def __str__(self) -> str:
        try:
            return str(self.read())
        except Exception:
            return "<ref ?>"


@dataclass(frozen=True)
class BindingRef(RefValue):
    env: Any
    name: str
    is_mutable: bool = False

    def read(self) -> Value:
        return cast(Value, self.env.get(self.name))

    def write(self, value: Value) -> None:
        self.env.set(self.name, value)


@dataclass(frozen=True)
class TempRef(RefValue):
    cell: list[Value]
    is_mutable: bool = False

    def read(self) -> Value:
        return self.cell[0]

    def write(self, value: Value) -> None:
        self.cell[0] = value


@dataclass(frozen=True)
class MemberRef(RefValue):
    base_ref: RefValue
    member: str
    is_mutable: bool = False

    def read(self) -> Value:
        base_val = self.base_ref.read()
        if isinstance(base_val, RecordValue):
            if self.member not in base_val.fields:
                raise InterpreterError(f"Record has no field '{self.member}'")
            return base_val.fields[self.member]
        raise InterpreterError("Member reference requires a record")

    def write(self, value: Value) -> None:
        base_val = self.base_ref.read()
        if not isinstance(base_val, RecordValue):
            raise InterpreterError("Member reference requires a record")
        new_fields = dict(base_val.fields)
        new_fields[self.member] = value
        self.base_ref.write(RecordValue(new_fields))


@dataclass(frozen=True)
class IndexRef(RefValue):
    base_ref: RefValue
    index: int | str
    is_mutable: bool = False

    def read(self) -> Value:
        base_val = self.base_ref.read()
        if isinstance(base_val, ListValue) and isinstance(self.index, int):
            idx = self.index
            if idx < 0 or idx >= len(base_val.elements):
                raise InterpreterError(f"List index out of bounds: {idx}")
            return base_val.elements[idx]
        if isinstance(base_val, TupleValue) and isinstance(self.index, int):
            idx = self.index
            if idx < 0 or idx >= len(base_val.elements):
                raise InterpreterError(f"Tuple index out of bounds: {idx}")
            return base_val.elements[idx]
        if isinstance(base_val, RecordValue) and isinstance(self.index, str):
            if self.index not in base_val.fields:
                raise InterpreterError(f"Missing record field '{self.index}'")
            return base_val.fields[self.index]
        raise InterpreterError("Unsupported index reference")

    def write(self, value: Value) -> None:
        base_val = self.base_ref.read()
        if isinstance(base_val, ListValue) and isinstance(self.index, int):
            idx = self.index
            if idx < 0 or idx >= len(base_val.elements):
                raise InterpreterError(f"List index out of bounds: {idx}")
            elems = list(base_val.elements)
            elems[idx] = value
            self.base_ref.write(ListValue(tuple(elems)))
            return
        if isinstance(base_val, RecordValue) and isinstance(self.index, str):
            new_fields = dict(base_val.fields)
            new_fields[self.index] = value
            self.base_ref.write(RecordValue(new_fields))
            return
        raise InterpreterError("Unsupported index reference assignment")


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

    def resolve(self, name: str) -> tuple[Environment, Value]:
        """Resolve ``name`` to the environment that owns its binding."""
        if name in self.bindings:
            return self, self.bindings[name]
        if self.parent:
            return self.parent.resolve(name)
        raise InterpreterError(f"Undefined variable '{name}'")

    def set(self, name: str, value: Value) -> None:
        """Set a variable value (mutation)."""
        if name in self.bindings:
            current = self.bindings[name]
            # Writing to a borrowed binding writes through the reference (even if the local
            # variable itself is immutable), since the binding isn't changing.
            if isinstance(current, RefValue):
                if not current.is_mutable:
                    raise InterpreterError(f"Cannot assign through immutable reference '{name}'")
                current.write(value)
                return

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
            if isinstance(arg, BitsValue):
                return IntValue(arg.value)
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
            if isinstance(arg, RecordValue):
                return IntValue(len(arg.fields))
            raise InterpreterError(f"len() not supported for {type(arg).__name__}")

        def builtin_abs(args: list[Value]) -> Value:
            arg = args[0]
            if isinstance(arg, IntValue):
                return IntValue(abs(arg.value))
            if isinstance(arg, BitsValue):
                return BitsValue(arg.bits, arg.value)  # already unsigned
            raise InterpreterError("abs() requires an integer")

        def builtin_max(args: list[Value]) -> Value:
            a, b = args[0], args[1]
            if isinstance(a, IntValue | BitsValue) and isinstance(b, IntValue | BitsValue):
                av = a.value if isinstance(a, IntValue) else a.value
                bv = b.value if isinstance(b, IntValue) else b.value
                return IntValue(max(av, bv))
            raise InterpreterError("max() requires integers")

        def builtin_min(args: list[Value]) -> Value:
            a, b = args[0], args[1]
            if isinstance(a, IntValue | BitsValue) and isinstance(b, IntValue | BitsValue):
                av = a.value if isinstance(a, IntValue) else a.value
                bv = b.value if isinstance(b, IntValue) else b.value
                return IntValue(min(av, bv))
            raise InterpreterError("min() requires integers")

        def builtin_range(args: list[Value]) -> Value:
            if len(args) == 1:
                n = args[0]
                if isinstance(n, BitsValue):
                    n = IntValue(n.value)
                if not isinstance(n, IntValue):
                    raise InterpreterError("range() requires integers")
                return ListValue(tuple(IntValue(i) for i in range(n.value)))
            if len(args) == 2:
                start, stop = args[0], args[1]
                if isinstance(start, BitsValue):
                    start = IntValue(start.value)
                if isinstance(stop, BitsValue):
                    stop = IntValue(stop.value)
                if not isinstance(start, IntValue) or not isinstance(stop, IntValue):
                    raise InterpreterError("range() requires integers")
                return ListValue(tuple(IntValue(i) for i in range(start.value, stop.value)))
            raise InterpreterError(f"range() takes 1 or 2 arguments, got {len(args)}")

        def builtin_ord(args: list[Value]) -> Value:
            if not isinstance(args[0], StringValue):
                raise InterpreterError("ord() expects String")
            s = args[0].value
            if len(s) != 1:
                raise InterpreterError("ord() expects a single-character String")
            return IntValue(ord(s))

        def builtin_ascii_bytes(args: list[Value]) -> Value:
            if not isinstance(args[0], StringValue):
                raise InterpreterError("ascii_bytes() expects String")
            out: list[Value] = []
            for ch in args[0].value:
                code = ord(ch)
                if code > 0x7F:
                    raise InterpreterError(
                        f"ascii_bytes() only supports ASCII; got codepoint {code}"
                    )
                out.append(BitsValue(8, code))
            return ListValue(tuple(out))

        def builtin_unicode_bytes(args: list[Value]) -> Value:
            if not isinstance(args[0], StringValue):
                raise InterpreterError("unicode_bytes() expects String")
            encoded = args[0].value.encode("utf-8")
            return ListValue(tuple(BitsValue(8, b) for b in encoded))

        def _cast_bits(bits: int) -> BuiltinFunction:
            def _fn(args: list[Value]) -> Value:
                x = args[0]
                if isinstance(x, BitsValue):
                    return BitsValue(bits, x.value)
                if isinstance(x, IntValue):
                    return BitsValue(bits, x.value)
                if isinstance(x, BoolValue):
                    return BitsValue(bits, 1 if x.value else 0)
                if isinstance(x, StringValue):
                    try:
                        return BitsValue(bits, int(x.value))
                    except ValueError as exc:
                        raise InterpreterError(f"Cannot convert {x.value!r} to bits") from exc
                raise InterpreterError(f"Cannot convert {type(x).__name__} to bits")

            return BuiltinFunction(f"<bits{bits}>", _fn, arity=1)

        self.global_env.define("print", BuiltinFunction("print", builtin_print, arity=1))
        self.global_env.define("str", BuiltinFunction("str", builtin_str, arity=1))
        self.global_env.define("int", BuiltinFunction("int", builtin_int, arity=1))
        self.global_env.define("len", BuiltinFunction("len", builtin_len, arity=1))
        self.global_env.define("abs", BuiltinFunction("abs", builtin_abs, arity=1))
        self.global_env.define("max", BuiltinFunction("max", builtin_max, arity=2))
        self.global_env.define("min", BuiltinFunction("min", builtin_min, arity=2))
        self.global_env.define("range", BuiltinFunction("range", builtin_range, arity=-1))
        self.global_env.define("ord", BuiltinFunction("ord", builtin_ord, arity=1))
        self.global_env.define(
            "ascii_bytes",
            BuiltinFunction("ascii_bytes", builtin_ascii_bytes, arity=1),
        )
        self.global_env.define(
            "unicode_bytes",
            BuiltinFunction("unicode_bytes", builtin_unicode_bytes, arity=1),
        )
        self.global_env.define("nibble", _cast_bits(4))
        self.global_env.define("byte", _cast_bits(8))
        self.global_env.define("word", _cast_bits(16))
        self.global_env.define("dword", _cast_bits(32))
        self.global_env.define("qword", _cast_bits(64))

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
            if decl.type_annotation is not None:
                value = self._coerce_value_for_type(decl.type_annotation, value, decl)
            self.current_env.define(decl.name, value, decl.is_mutable)
        elif isinstance(decl, ast.ImportDecl):
            self.execute_import_decl(decl)
        elif isinstance(decl, ast.TypeAliasDecl):
            # Type aliases are compile-time only
            pass
        elif isinstance(decl, ast.TraitDecl | ast.ImplDecl):
            # Traits/impls are compile-time only in this prototype.
            pass

    def execute_function_decl(self, decl: ast.FunctionDecl) -> None:
        """Execute a function declaration."""
        param_names = tuple(p.name for p in decl.params)
        param_types = tuple(p.type_annotation for p in decl.params)
        func = FunctionValue(
            params=param_names,
            param_type_annotations=param_types,
            body=tuple(decl.body),
            closure=self.current_env,
        )
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

    def _coerce_value_for_type(
        self, type_expr: ast.TypeExpr, value: Value, node: ast.Node | None
    ) -> Value:
        """Coerce runtime values for fixed-width integer annotations."""
        if isinstance(type_expr, ast.SimpleType) and len(type_expr.name.parts) == 1:
            type_name = type_expr.name.parts[0]
            bits = _bits_from_name(type_name)
            if bits is None:
                return value

            mask = (1 << bits) - 1
            raw: int
            if isinstance(value, BitsValue | IntValue):
                raw = value.value
            elif isinstance(value, BoolValue):
                raw = 1 if value.value else 0
            elif isinstance(value, StringValue):
                try:
                    raw = int(value.value)
                except ValueError as exc:
                    raise InterpreterError(
                        f"Cannot convert {value.value!r} to {type_name}", node
                    ) from exc
            else:
                raise InterpreterError(
                    f"Cannot convert {type(value).__name__} to {type_name}", node
                )

            if raw < 0 or raw > mask:
                cast = type_name.lower()
                raise InterpreterError(
                    (
                        f"Value {raw} does not fit in {type_name} (0..{mask}). "
                        f"Use `{cast}({raw})` to wrap explicitly."
                    ),
                    node,
                )
            return BitsValue(bits, raw)

        return value

    def execute_statement(self, stmt: ast.Stmt) -> None:
        """Execute a statement."""
        if isinstance(stmt, ast.LetStmt):
            value = self.evaluate_expr(stmt.initializer)
            if stmt.type_annotation is not None and isinstance(stmt.pattern, ast.BindingPattern):
                value = self._coerce_value_for_type(stmt.type_annotation, value, stmt)
            self._bind_pattern(stmt.pattern, value, stmt.is_mutable, stmt)

        elif isinstance(stmt, ast.AssignStmt):
            value = self.evaluate_expr(stmt.value)
            if isinstance(stmt.target, ast.Identifier):
                self.current_env.set(stmt.target.name, value)
                return
            if isinstance(stmt.target, ast.UnaryExpr) and stmt.target.operator == "*":
                # Deref assignment: *p <- v
                op = stmt.target.operand
                raw: Value
                if isinstance(op, ast.Identifier):
                    raw = self.current_env.get(op.name)
                else:
                    raw = self.evaluate_expr(op)
                if not isinstance(raw, RefValue):
                    raise InterpreterError("Deref assignment requires a reference", stmt)
                if not raw.is_mutable:
                    raise InterpreterError("Cannot assign through immutable reference", stmt)
                raw.write(value)
                return

            if isinstance(stmt.target, ast.MemberExpr):
                ref = self._make_lvalue_ref(
                    stmt.target,
                    require_mutable_base=True,
                    node=stmt,
                )
                if not ref.is_mutable:
                    raise InterpreterError("Cannot assign through immutable reference", stmt)
                ref.write(value)
                return

            if isinstance(stmt.target, ast.IndexExpr):
                ref = self._make_lvalue_ref(
                    stmt.target,
                    require_mutable_base=True,
                    node=stmt,
                )
                if not ref.is_mutable:
                    raise InterpreterError("Cannot assign through immutable reference", stmt)
                ref.write(value)
                return

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

    def _make_lvalue_ref(
        self,
        target: ast.Expr,
        *,
        require_mutable_base: bool,
        node: ast.Node,
        allow_temporary_root: bool = False,
    ) -> RefValue:
        if isinstance(target, ast.Identifier):
            target_env, current = self.current_env.resolve(target.name)
            if require_mutable_base and target.name not in target_env.mutable:
                raise InterpreterError(
                    f"Cannot take &mut of immutable variable '{target.name}'",
                    node,
                )
            if isinstance(current, RefValue):
                if require_mutable_base and not current.is_mutable:
                    raise InterpreterError(
                        f"Cannot take &mut of immutable reference '{target.name}'",
                        node,
                    )
                return current
            return BindingRef(env=target_env, name=target.name, is_mutable=require_mutable_base)

        if isinstance(target, ast.MemberExpr):
            return MemberRef(
                base_ref=self._make_lvalue_ref(
                    target.obj,
                    require_mutable_base=require_mutable_base,
                    node=node,
                    allow_temporary_root=True,
                ),
                member=target.member,
                is_mutable=require_mutable_base,
            )

        if isinstance(target, ast.IndexExpr):
            idx_v = self.evaluate_expr(target.index)
            if isinstance(idx_v, IntValue):
                idx_key: int | str = idx_v.value
            elif isinstance(idx_v, StringValue):
                idx_key = idx_v.value
            else:
                raise InterpreterError("Index reference requires Int or String index", node)
            return IndexRef(
                base_ref=self._make_lvalue_ref(
                    target.obj,
                    require_mutable_base=require_mutable_base,
                    node=node,
                    allow_temporary_root=True,
                ),
                index=idx_key,
                is_mutable=require_mutable_base,
            )

        if allow_temporary_root:
            return TempRef(cell=[self.evaluate_expr(target)], is_mutable=require_mutable_base)

        raise InterpreterError(
            "Borrow and assignment targets must be lvalues in this prototype",
            node,
        )

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
            v = self.current_env.get(expr.name)
            # Implicit deref: borrowed bindings behave like the underlying value.
            while isinstance(v, RefValue):
                v = v.read()
            return v

        elif isinstance(expr, ast.BorrowExpr):
            return self._make_lvalue_ref(
                expr.target,
                require_mutable_base=expr.is_mutable,
                node=expr,
            )

        elif isinstance(expr, ast.LambdaExpr):
            param_names = tuple(p.name for p in expr.params)
            param_types = tuple(p.type_annotation for p in expr.params)
            # Expression lambdas implicitly return the expression value.
            body = tuple(expr.body) if isinstance(expr.body, list) else (ast.ReturnStmt(expr.body),)
            return FunctionValue(
                params=param_names,
                param_type_annotations=param_types,
                body=body,
                closure=self.current_env,
            )

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
            elif isinstance(obj, RecordValue) and isinstance(index, StringValue):
                key = index.value
                if key not in obj.fields:
                    raise InterpreterError(f"Missing record field '{key}'", expr)
                return obj.fields[key]
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

        def is_int(v: Value) -> bool:
            return isinstance(v, IntValue | BitsValue)

        def as_py_int(v: Value) -> int:
            if isinstance(v, IntValue):
                return v.value
            if isinstance(v, BitsValue):
                return v.value
            raise InterpreterError(f"Expected integer, got {type(v).__name__}", expr)

        def bits_width(v: Value) -> int | None:
            return v.bits if isinstance(v, BitsValue) else None

        def make_bits(width: int, n: int) -> BitsValue:
            return BitsValue(width, n)

        def widest_bits(a: Value, b: Value) -> int | None:
            # Only wrap when both operands are fixed-width.
            if isinstance(a, BitsValue) and isinstance(b, BitsValue):
                return max(a.bits, b.bits)
            return None

        # Arithmetic operators
        if expr.operator in ("+", "-", "*", "/", "%"):
            # String concatenation
            if expr.operator == "+" and isinstance(left, StringValue):
                if isinstance(right, StringValue):
                    return StringValue(left.value + right.value)
                raise InterpreterError("String + requires a string on the right", expr)
            if not is_int(left) or not is_int(right):
                raise InterpreterError("Arithmetic requires integers (or strings for +)", expr)

            lv = as_py_int(left)
            rv = as_py_int(right)

            out_bits = widest_bits(left, right)
            if out_bits is None:
                if expr.operator == "+":
                    return IntValue(lv + rv)
                if expr.operator == "-":
                    return IntValue(lv - rv)
                if expr.operator == "*":
                    return IntValue(lv * rv)
                if expr.operator == "/":
                    if rv == 0:
                        raise InterpreterError("Division by zero", expr)
                    return IntValue(lv // rv)
                if expr.operator == "%":
                    if rv == 0:
                        raise InterpreterError("Modulo by zero", expr)
                    return IntValue(lv % rv)

            # Fixed-width arithmetic wraps modulo 2^N.
            assert out_bits is not None
            if expr.operator == "+":
                return make_bits(out_bits, lv + rv)
            if expr.operator == "-":
                return make_bits(out_bits, lv - rv)
            if expr.operator == "*":
                return make_bits(out_bits, lv * rv)
            if expr.operator == "/":
                if rv == 0:
                    raise InterpreterError("Division by zero", expr)
                return make_bits(out_bits, lv // rv)
            if expr.operator == "%":
                if rv == 0:
                    raise InterpreterError("Modulo by zero", expr)
                return make_bits(out_bits, lv % rv)

        # Bitwise operators
        elif expr.operator in ("&", "|", "^", "<<", ">>"):
            if not is_int(left) or not is_int(right):
                raise InterpreterError("Bitwise operators require integers", expr)
            lv = as_py_int(left)
            rv = as_py_int(right)

            if expr.operator == "<<":
                out_bits = bits_width(left)
                if out_bits is None:
                    return IntValue(lv << rv)
                assert out_bits is not None
                return make_bits(out_bits, lv << rv)
            if expr.operator == ">>":
                out_bits = bits_width(left)
                if out_bits is None:
                    return IntValue(lv >> rv)
                assert out_bits is not None
                return make_bits(out_bits, lv >> rv)

            out_bits2 = widest_bits(left, right)
            if out_bits2 is None:
                if expr.operator == "&":
                    return IntValue(lv & rv)
                if expr.operator == "|":
                    return IntValue(lv | rv)
                return IntValue(lv ^ rv)

            if expr.operator == "&":
                return make_bits(out_bits2, lv & rv)
            if expr.operator == "|":
                return make_bits(out_bits2, lv | rv)
            return make_bits(out_bits2, lv ^ rv)

        # Comparison operators
        elif expr.operator in ("<", "<=", ">", ">="):
            if not is_int(left) or not is_int(right):
                raise InterpreterError("Comparison requires integers", expr)
            lv = as_py_int(left)
            rv = as_py_int(right)

            if expr.operator == "<":
                return BoolValue(lv < rv)
            elif expr.operator == "<=":
                return BoolValue(lv <= rv)
            elif expr.operator == ">":
                return BoolValue(lv > rv)
            elif expr.operator == ">=":
                return BoolValue(lv >= rv)

        # Equality operators
        elif expr.operator in ("==", "!="):
            equal = self.values_equal(left, right)
            return BoolValue(equal if expr.operator == "==" else not equal)

        raise InterpreterError(f"Unknown binary operator: {expr.operator}", expr)

    def evaluate_unary_expr(self, expr: ast.UnaryExpr) -> Value:
        """Evaluate a unary expression."""
        if expr.operator == "*":
            # Dereference: *p. Identifiers are implicitly deref'd in normal expression evaluation,
            # so use the raw binding value here.
            raw: Value
            if isinstance(expr.operand, ast.Identifier):
                raw = self.current_env.get(expr.operand.name)
            else:
                raw = self.evaluate_expr(expr.operand)
            if not isinstance(raw, RefValue):
                raise InterpreterError("Deref requires a reference", expr)
            v: Value = raw.read()
            while isinstance(v, RefValue):
                v = v.read()
            return v

        operand = self.evaluate_expr(expr.operand)

        if expr.operator == "-":
            if not isinstance(operand, IntValue):
                raise InterpreterError("Negation requires integer", expr)
            return IntValue(-operand.value)

        elif expr.operator == "not":
            if not isinstance(operand, BoolValue):
                raise InterpreterError("Logical not requires boolean", expr)
            return BoolValue(not operand.value)

        elif expr.operator == "~":
            if isinstance(operand, IntValue):
                return IntValue(~operand.value)
            if isinstance(operand, BitsValue):
                return BitsValue(operand.bits, (~operand.value) & operand.mask)
            raise InterpreterError("Bitwise not requires integer", expr)

        raise InterpreterError(f"Unknown unary operator: {expr.operator}", expr)

    def evaluate_call_expr(self, expr: ast.CallExpr) -> Value:
        """Evaluate a function call."""
        func = self.evaluate_expr(expr.func)

        # Built-in function
        if isinstance(func, BuiltinFunction):
            args = [self.evaluate_expr(arg) for arg in expr.args]
            if func.arity >= 0 and len(args) != func.arity:
                msg = f"Built-in {func.name} expects {func.arity} argument(s), got {len(args)}"
                raise InterpreterError(msg, expr)
            return func.func(args)

        # User-defined function
        elif isinstance(func, FunctionValue):
            if len(expr.args) != len(func.params):
                msg = f"Function expects {len(func.params)} arguments, got {len(expr.args)}"
                raise InterpreterError(msg, expr)

            # Create new environment for function execution
            func_env = func.closure.create_child()
            for i, (param, arg_expr) in enumerate(zip(func.params, expr.args, strict=False)):
                expected = func.param_type_annotations[i]
                if isinstance(expected, ast.BorrowTypeExpr):
                    # Implicit-borrow model: allow passing an identifier to an &T or &mut T
                    # parameter without requiring explicit & / &mut in call sites.
                    if isinstance(arg_expr, ast.BorrowExpr):
                        arg_v = self.evaluate_expr(arg_expr)
                    elif isinstance(arg_expr, ast.Identifier):
                        arg_v = self.evaluate_expr(
                            ast.BorrowExpr(target=arg_expr, is_mutable=expected.is_mutable)
                        )
                    else:
                        raise InterpreterError(
                            "Borrow arguments must be identifiers in this prototype",
                            arg_expr,
                        )
                    if not isinstance(arg_v, RefValue):
                        raise InterpreterError("Borrow argument must be a reference", arg_expr)
                    if expected.is_mutable and not arg_v.is_mutable:
                        raise InterpreterError(
                            "Cannot pass immutable reference where &mut is expected",
                            arg_expr,
                        )
                    func_env.define(param, arg_v)
                    continue

                v = self.evaluate_expr(arg_expr)
                # Passing a reference to a value parameter passes the referent.
                while isinstance(v, RefValue):
                    v = v.read()
                func_env.define(param, v)

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
        # Numeric equality: allow comparing Int and fixed-width integers by value.
        if isinstance(left, IntValue | BitsValue) and isinstance(right, IntValue | BitsValue):
            lv = left.value if isinstance(left, IntValue) else left.value
            rv = right.value if isinstance(right, IntValue) else right.value
            return lv == rv

        if type(left) is not type(right):
            return False

        if isinstance(left, IntValue | StringValue | BoolValue):
            return left.value == right.value  # type: ignore
        elif isinstance(left, NilValue):
            return True
        elif isinstance(left, ListValue):
            assert isinstance(right, ListValue)
            if len(left.elements) != len(right.elements):
                return False
            return all(
                self.values_equal(a, b) for a, b in zip(left.elements, right.elements, strict=True)
            )
        elif isinstance(left, TupleValue):
            assert isinstance(right, TupleValue)
            if len(left.elements) != len(right.elements):
                return False
            return all(
                self.values_equal(a, b) for a, b in zip(left.elements, right.elements, strict=True)
            )
        elif isinstance(left, RecordValue):
            assert isinstance(right, RecordValue)
            if left.fields.keys() != right.fields.keys():
                return False
            return all(self.values_equal(left.fields[k], right.fields[k]) for k in left.fields)

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
