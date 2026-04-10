"""Interpreter for the Aster language.

This module provides runtime execution for Aster programs.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from aster_lang import ast
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
class FunctionValue(Value):
    """Function value with closure."""

    params: tuple[str, ...]
    body: tuple[ast.Stmt, ...]
    closure: Any  # Environment (can't be frozen, so use Any)

    def __str__(self) -> str:
        return "<function>"


@dataclass(frozen=True)
class BuiltinFunction(Value):
    """Built-in function."""

    name: str
    func: Callable[[Value], Value]

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

    def __init__(self) -> None:
        self.global_env = Environment()
        self.current_env = self.global_env
        self.output: list[str] = []
        self._initialize_builtins()

    def _initialize_builtins(self) -> None:
        """Initialize built-in functions."""

        def builtin_print(arg: Value) -> Value:
            self.output.append(str(arg))
            return NIL

        def builtin_str(arg: Value) -> Value:
            return StringValue(str(arg))

        def builtin_int(arg: Value) -> Value:
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

        def builtin_len(arg: Value) -> Value:
            if isinstance(arg, StringValue):
                return IntValue(len(arg.value))
            if isinstance(arg, ListValue):
                return IntValue(len(arg.elements))
            if isinstance(arg, TupleValue):
                return IntValue(len(arg.elements))
            raise InterpreterError(f"len() not supported for {type(arg).__name__}")

        self.global_env.define("print", BuiltinFunction("print", builtin_print))
        self.global_env.define("str", BuiltinFunction("str", builtin_str))
        self.global_env.define("int", BuiltinFunction("int", builtin_int))
        self.global_env.define("len", BuiltinFunction("len", builtin_len))

    def interpret(self, module: ast.Module) -> None:
        """Interpret a module."""
        for decl in module.declarations:
            self.execute_declaration(decl)

        # If main() function exists, call it
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
            # TODO: Implement module imports
            pass
        elif isinstance(decl, ast.TypeAliasDecl):
            # Type aliases are compile-time only
            pass

    def execute_function_decl(self, decl: ast.FunctionDecl) -> None:
        """Execute a function declaration."""
        param_names = tuple(p.name for p in decl.params)
        func = FunctionValue(params=param_names, body=tuple(decl.body), closure=self.current_env)
        self.current_env.define(decl.name, func)

    def execute_statement(self, stmt: ast.Stmt) -> None:
        """Execute a statement."""
        if isinstance(stmt, ast.LetStmt):
            value = self.evaluate_expr(stmt.initializer)
            self.current_env.define(stmt.name, value, stmt.is_mutable)

        elif isinstance(stmt, ast.AssignStmt):
            value = self.evaluate_expr(stmt.value)
            if isinstance(stmt.target, ast.Identifier):
                self.current_env.set(stmt.target.name, value)
            else:
                # TODO: Handle member access and index assignment
                raise InterpreterError("Complex assignment targets not yet supported", stmt)

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
            binding_name, matched = self._match_pattern(arm.pattern, subject)
            if matched:
                self.current_env = self.current_env.create_child()
                try:
                    if binding_name is not None:
                        self.current_env.define(binding_name, subject, is_mutable=False)
                    for s in arm.body:
                        self.execute_statement(s)
                finally:
                    assert self.current_env.parent is not None
                    self.current_env = self.current_env.parent
                return
        # No arm matched — no error, execution continues

    def _match_pattern(self, pattern: ast.Pattern, value: Value) -> tuple[str | None, bool]:
        """Return (binding_name_or_None, matched)."""
        if isinstance(pattern, ast.WildcardPattern):
            return (None, True)
        if isinstance(pattern, ast.BindingPattern):
            return (pattern.name, True)
        if isinstance(pattern, ast.LiteralPattern):
            lit = pattern.literal
            if isinstance(lit, ast.IntegerLiteral):
                return (None, isinstance(value, IntValue) and value.value == lit.value)
            if isinstance(lit, ast.StringLiteral):
                return (None, isinstance(value, StringValue) and value.value == lit.value)
            if isinstance(lit, ast.BoolLiteral):
                return (None, isinstance(value, BoolValue) and value.value == lit.value)
            if isinstance(lit, ast.NilLiteral):
                return (None, isinstance(value, NilValue))
        return (None, False)

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

        # Logical operators
        elif expr.operator == "and":
            if not isinstance(left, BoolValue) or not isinstance(right, BoolValue):
                raise InterpreterError("Logical operators require booleans", expr)
            return BoolValue(left.value and right.value)

        elif expr.operator == "or":
            if not isinstance(left, BoolValue) or not isinstance(right, BoolValue):
                raise InterpreterError("Logical operators require booleans", expr)
            return BoolValue(left.value or right.value)

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
            if len(args) != 1:
                msg = f"Built-in {func.name} expects 1 argument, got {len(args)}"
                raise InterpreterError(msg, expr)
            return func.func(args[0])

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


def interpret_source(source: str) -> InterpretationResult:
    """Interpret Aster source code."""
    try:
        module = parse_module(source)
        interpreter = Interpreter()
        interpreter.interpret(module)
        output = "\n".join(interpreter.output)
        return InterpretationResult(output=output)
    except InterpreterError as e:
        return InterpretationResult(error=str(e))
    except Exception as e:
        return InterpretationResult(error=f"Internal error: {e}")
