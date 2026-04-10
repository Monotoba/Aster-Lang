"""Semantic analysis for the Aster language.

This module provides symbol tables, type checking, and semantic validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from aster_lang import ast

# Type System


class TypeKind(Enum):
    """Kinds of types in the Aster type system."""

    INT = auto()
    STRING = auto()
    BOOL = auto()
    NIL = auto()
    FUNCTION = auto()
    LIST = auto()
    TUPLE = auto()
    RECORD = auto()
    UNKNOWN = auto()  # For type inference
    ERROR = auto()  # For error recovery


@dataclass(frozen=True)
class Type:
    """Base class for types."""

    kind: TypeKind

    def __str__(self) -> str:
        return self.kind.name.capitalize()


@dataclass(frozen=True)
class IntType(Type):
    """Integer type."""

    def __init__(self) -> None:
        object.__setattr__(self, "kind", TypeKind.INT)

    def __str__(self) -> str:
        return "Int"


@dataclass(frozen=True)
class StringType(Type):
    """String type."""

    def __init__(self) -> None:
        object.__setattr__(self, "kind", TypeKind.STRING)

    def __str__(self) -> str:
        return "String"


@dataclass(frozen=True)
class BoolType(Type):
    """Boolean type."""

    def __init__(self) -> None:
        object.__setattr__(self, "kind", TypeKind.BOOL)

    def __str__(self) -> str:
        return "Bool"


@dataclass(frozen=True)
class NilType(Type):
    """Nil type."""

    def __init__(self) -> None:
        object.__setattr__(self, "kind", TypeKind.NIL)

    def __str__(self) -> str:
        return "Nil"


@dataclass(frozen=True)
class FunctionType(Type):
    """Function type: (T1, T2, ...) -> R"""

    param_types: tuple[Type, ...]
    return_type: Type

    def __init__(self, param_types: tuple[Type, ...], return_type: Type) -> None:
        object.__setattr__(self, "kind", TypeKind.FUNCTION)
        object.__setattr__(self, "param_types", param_types)
        object.__setattr__(self, "return_type", return_type)

    def __str__(self) -> str:
        params = ", ".join(str(t) for t in self.param_types)
        return f"Fn({params}) -> {self.return_type}"


@dataclass(frozen=True)
class ListType(Type):
    """List type: [T]"""

    element_type: Type

    def __init__(self, element_type: Type) -> None:
        object.__setattr__(self, "kind", TypeKind.LIST)
        object.__setattr__(self, "element_type", element_type)

    def __str__(self) -> str:
        return f"[{self.element_type}]"


@dataclass(frozen=True)
class TupleType(Type):
    """Tuple type: (T1, T2, ...)"""

    element_types: tuple[Type, ...]

    def __init__(self, element_types: tuple[Type, ...]) -> None:
        object.__setattr__(self, "kind", TypeKind.TUPLE)
        object.__setattr__(self, "element_types", element_types)

    def __str__(self) -> str:
        elements = ", ".join(str(t) for t in self.element_types)
        return f"({elements})"


@dataclass(frozen=True)
class UnknownType(Type):
    """Unknown type for inference."""

    def __init__(self) -> None:
        object.__setattr__(self, "kind", TypeKind.UNKNOWN)

    def __str__(self) -> str:
        return "?"


@dataclass(frozen=True)
class ErrorType(Type):
    """Error type for error recovery."""

    def __init__(self) -> None:
        object.__setattr__(self, "kind", TypeKind.ERROR)

    def __str__(self) -> str:
        return "<error>"


# Built-in types
INT_TYPE = IntType()
STRING_TYPE = StringType()
BOOL_TYPE = BoolType()
NIL_TYPE = NilType()
UNKNOWN_TYPE = UnknownType()
ERROR_TYPE = ErrorType()


# Symbol Table


class SymbolKind(Enum):
    """Kinds of symbols."""

    VARIABLE = auto()
    FUNCTION = auto()
    PARAMETER = auto()
    TYPE_ALIAS = auto()
    MODULE = auto()


@dataclass
class Symbol:
    """A symbol in the symbol table."""

    name: str
    kind: SymbolKind
    type: Type
    is_mutable: bool = False
    declaration_node: ast.Node | None = None

    def __str__(self) -> str:
        mut = "mut " if self.is_mutable else ""
        return f"{mut}{self.name}: {self.type}"


class Scope:
    """A lexical scope containing symbols."""

    def __init__(self, parent: Scope | None = None, name: str = "<global>") -> None:
        self.name = name
        self.parent = parent
        self.symbols: dict[str, Symbol] = {}
        self.children: list[Scope] = []

    def define(self, symbol: Symbol) -> bool:
        """Define a symbol in this scope. Returns False if already defined."""
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup(self, name: str) -> Symbol | None:
        """Look up a symbol in this scope or parent scopes."""
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name: str) -> Symbol | None:
        """Look up a symbol only in this scope (not parent scopes)."""
        return self.symbols.get(name)

    def create_child(self, name: str = "<block>") -> Scope:
        """Create a child scope."""
        child = Scope(parent=self, name=name)
        self.children.append(child)
        return child

    def __str__(self) -> str:
        symbols_str = ", ".join(self.symbols.keys())
        return f"Scope({self.name}: {symbols_str})"


class SymbolTable:
    """Symbol table managing scopes and symbols."""

    def __init__(self) -> None:
        self.global_scope = Scope(name="<module>")
        self.current_scope = self.global_scope
        self._initialize_builtins()

    def _initialize_builtins(self) -> None:
        """Initialize built-in functions and types."""
        # Built-in function: print
        print_fn = Symbol(
            name="print",
            kind=SymbolKind.FUNCTION,
            type=FunctionType(param_types=(STRING_TYPE,), return_type=NIL_TYPE),
        )
        self.global_scope.define(print_fn)

    def enter_scope(self, name: str = "<block>") -> None:
        """Enter a new nested scope."""
        self.current_scope = self.current_scope.create_child(name)

    def exit_scope(self) -> None:
        """Exit the current scope and return to parent."""
        if self.current_scope.parent:
            self.current_scope = self.current_scope.parent

    def define(self, symbol: Symbol) -> bool:
        """Define a symbol in the current scope."""
        return self.current_scope.define(symbol)

    def lookup(self, name: str) -> Symbol | None:
        """Look up a symbol in current or parent scopes."""
        return self.current_scope.lookup(name)

    def lookup_local(self, name: str) -> Symbol | None:
        """Look up a symbol only in current scope."""
        return self.current_scope.lookup_local(name)


# Semantic Errors


@dataclass
class SemanticError:
    """A semantic error with location information."""

    message: str
    node: ast.Node | None = None

    def __str__(self) -> str:
        return f"Semantic error: {self.message}"


class SemanticAnalyzer:
    """Semantic analyzer for the Aster language.

    Performs:
    - Symbol table construction
    - Name resolution
    - Type checking
    - Basic ownership checking
    """

    def __init__(self) -> None:
        self.symbol_table = SymbolTable()
        self.errors: list[SemanticError] = []
        self.expr_types: dict[int, Type] = {}  # Map AST node id to inferred type

    def error(self, message: str, node: ast.Node | None = None) -> None:
        """Record a semantic error."""
        self.errors.append(SemanticError(message, node))

    def has_errors(self) -> bool:
        """Check if any errors were recorded."""
        return len(self.errors) > 0

    def analyze(self, module: ast.Module) -> bool:
        """Analyze a module. Returns True if no errors."""
        self.analyze_module(module)
        return not self.has_errors()

    # Module and declarations

    def analyze_module(self, module: ast.Module) -> None:
        """Analyze a module."""
        for decl in module.declarations:
            self.analyze_declaration(decl)

    def analyze_declaration(self, decl: ast.Decl) -> None:
        """Analyze a declaration."""
        if isinstance(decl, ast.FunctionDecl):
            self.analyze_function_decl(decl)
        elif isinstance(decl, ast.LetDecl):
            self.analyze_let_decl(decl)
        elif isinstance(decl, ast.ImportDecl):
            self.analyze_import_decl(decl)
        elif isinstance(decl, ast.TypeAliasDecl):
            self.analyze_type_alias_decl(decl)

    def analyze_function_decl(self, decl: ast.FunctionDecl) -> None:
        """Analyze a function declaration."""
        # Resolve parameter types
        param_types = []
        for param in decl.params:
            if param.type_annotation:
                param_type = self.resolve_type_expr(param.type_annotation)
            else:
                param_type = UNKNOWN_TYPE
            param_types.append(param_type)

        # Resolve return type
        return_type = self.resolve_type_expr(decl.return_type) if decl.return_type else NIL_TYPE

        # Create function symbol
        func_type = FunctionType(tuple(param_types), return_type)
        func_symbol = Symbol(
            name=decl.name,
            kind=SymbolKind.FUNCTION,
            type=func_type,
            declaration_node=decl,
        )

        # Define function in current scope
        if not self.symbol_table.define(func_symbol):
            self.error(f"Function '{decl.name}' is already defined", decl)

        # Enter function scope
        self.symbol_table.enter_scope(f"fn {decl.name}")

        # Define parameters
        for param, param_type in zip(decl.params, param_types, strict=False):
            param_symbol = Symbol(
                name=param.name,
                kind=SymbolKind.PARAMETER,
                type=param_type,
                declaration_node=param,
            )
            self.symbol_table.define(param_symbol)

        # Analyze function body
        for stmt in decl.body:
            self.analyze_statement(stmt)

        # Exit function scope
        self.symbol_table.exit_scope()

    def analyze_let_decl(self, decl: ast.LetDecl) -> None:
        """Analyze a let declaration."""
        # Infer type from initializer
        init_type = self.infer_expr_type(decl.initializer)

        # Check against declared type if present
        if decl.type_annotation:
            declared_type = self.resolve_type_expr(decl.type_annotation)
            if not self.types_compatible(init_type, declared_type):
                self.error(
                    f"Type mismatch: cannot assign {init_type} to {declared_type}",
                    decl,
                )
            final_type = declared_type
        else:
            final_type = init_type

        # Define symbol
        symbol = Symbol(
            name=decl.name,
            kind=SymbolKind.VARIABLE,
            type=final_type,
            is_mutable=decl.is_mutable,
            declaration_node=decl,
        )

        if not self.symbol_table.define(symbol):
            self.error(f"Variable '{decl.name}' is already defined", decl)

    def analyze_import_decl(self, decl: ast.ImportDecl) -> None:
        """Analyze an import declaration."""
        # TODO: Implement module loading and import resolution
        pass

    def analyze_type_alias_decl(self, decl: ast.TypeAliasDecl) -> None:
        """Analyze a type alias declaration."""
        # TODO: Implement type alias resolution
        pass

    # Statements

    def analyze_statement(self, stmt: ast.Stmt) -> None:
        """Analyze a statement."""
        if isinstance(stmt, ast.LetStmt):
            self.analyze_let_stmt(stmt)
        elif isinstance(stmt, ast.AssignStmt):
            self.analyze_assign_stmt(stmt)
        elif isinstance(stmt, ast.ReturnStmt):
            self.analyze_return_stmt(stmt)
        elif isinstance(stmt, ast.IfStmt):
            self.analyze_if_stmt(stmt)
        elif isinstance(stmt, ast.WhileStmt):
            self.analyze_while_stmt(stmt)
        elif isinstance(stmt, ast.ForStmt):
            self.analyze_for_stmt(stmt)
        elif isinstance(stmt, ast.BreakStmt | ast.ContinueStmt):
            pass  # No analysis needed
        elif isinstance(stmt, ast.MatchStmt):
            self.analyze_match_stmt(stmt)
        elif isinstance(stmt, ast.ExprStmt):
            self.infer_expr_type(stmt.expr)

    def analyze_let_stmt(self, stmt: ast.LetStmt) -> None:
        """Analyze a let statement."""
        # Infer type from initializer
        init_type = self.infer_expr_type(stmt.initializer)

        # Check against declared type if present
        if stmt.type_annotation:
            declared_type = self.resolve_type_expr(stmt.type_annotation)
            if not self.types_compatible(init_type, declared_type):
                self.error(
                    f"Type mismatch: cannot assign {init_type} to {declared_type}",
                    stmt,
                )
            final_type = declared_type
        else:
            final_type = init_type

        # Define symbol
        symbol = Symbol(
            name=stmt.name,
            kind=SymbolKind.VARIABLE,
            type=final_type,
            is_mutable=stmt.is_mutable,
            declaration_node=stmt,
        )

        if not self.symbol_table.define(symbol):
            self.error(f"Variable '{stmt.name}' is already defined", stmt)

    def analyze_assign_stmt(self, stmt: ast.AssignStmt) -> None:
        """Analyze an assignment statement."""
        # Check that target is a valid lvalue
        if isinstance(stmt.target, ast.Identifier):
            symbol = self.symbol_table.lookup(stmt.target.name)
            if symbol is None:
                self.error(f"Undefined variable '{stmt.target.name}'", stmt)
                return

            # Check mutability
            if not symbol.is_mutable:
                self.error(
                    f"Cannot assign to immutable variable '{stmt.target.name}'",
                    stmt,
                )

            # Type check
            value_type = self.infer_expr_type(stmt.value)
            if not self.types_compatible(value_type, symbol.type):
                self.error(
                    f"Type mismatch: cannot assign {value_type} to {symbol.type}",
                    stmt,
                )
        else:
            # TODO: Handle member access and index expressions
            self.infer_expr_type(stmt.target)
            self.infer_expr_type(stmt.value)

    def analyze_return_stmt(self, stmt: ast.ReturnStmt) -> None:
        """Analyze a return statement."""
        if stmt.value:
            self.infer_expr_type(stmt.value)
        # TODO: Check return type against function signature

    def analyze_if_stmt(self, stmt: ast.IfStmt) -> None:
        """Analyze an if statement."""
        # Check condition type
        cond_type = self.infer_expr_type(stmt.condition)
        if not self.types_compatible(cond_type, BOOL_TYPE):
            self.error(f"If condition must be Bool, got {cond_type}", stmt)

        # Analyze blocks
        self.symbol_table.enter_scope("<then>")
        for s in stmt.then_block:
            self.analyze_statement(s)
        self.symbol_table.exit_scope()

        if stmt.else_block:
            self.symbol_table.enter_scope("<else>")
            for s in stmt.else_block:
                self.analyze_statement(s)
            self.symbol_table.exit_scope()

    def analyze_while_stmt(self, stmt: ast.WhileStmt) -> None:
        """Analyze a while statement."""
        # Check condition type
        cond_type = self.infer_expr_type(stmt.condition)
        if not self.types_compatible(cond_type, BOOL_TYPE):
            self.error(f"While condition must be Bool, got {cond_type}", stmt)

        # Analyze body
        self.symbol_table.enter_scope("<while>")
        for s in stmt.body:
            self.analyze_statement(s)
        self.symbol_table.exit_scope()

    def analyze_for_stmt(self, stmt: ast.ForStmt) -> None:
        """Analyze a for statement."""
        # TODO: Infer element type from iterable
        self.infer_expr_type(stmt.iterable)

        # Enter loop scope and define loop variable
        self.symbol_table.enter_scope("<for>")
        loop_var = Symbol(
            name=stmt.variable,
            kind=SymbolKind.VARIABLE,
            type=UNKNOWN_TYPE,  # TODO: Infer from iterable
            declaration_node=stmt,
        )
        self.symbol_table.define(loop_var)

        # Analyze body
        for s in stmt.body:
            self.analyze_statement(s)

        self.symbol_table.exit_scope()

    def analyze_match_stmt(self, stmt: ast.MatchStmt) -> None:
        """Analyze a match statement."""
        self.infer_expr_type(stmt.subject)
        for arm in stmt.arms:
            self.symbol_table.enter_scope("<match-arm>")
            # If binding pattern, define the bound variable
            if isinstance(arm.pattern, ast.BindingPattern):
                bound = Symbol(
                    name=arm.pattern.name,
                    kind=SymbolKind.VARIABLE,
                    type=UNKNOWN_TYPE,
                    declaration_node=stmt,
                )
                self.symbol_table.define(bound)
            for s in arm.body:
                self.analyze_statement(s)
            self.symbol_table.exit_scope()

    # Type inference

    def infer_expr_type(self, expr: ast.Expr) -> Type:
        """Infer the type of an expression."""
        if isinstance(expr, ast.IntegerLiteral):
            return INT_TYPE
        elif isinstance(expr, ast.StringLiteral):
            return STRING_TYPE
        elif isinstance(expr, ast.BoolLiteral):
            return BOOL_TYPE
        elif isinstance(expr, ast.NilLiteral):
            return NIL_TYPE
        elif isinstance(expr, ast.Identifier):
            symbol = self.symbol_table.lookup(expr.name)
            if symbol is None:
                self.error(f"Undefined variable '{expr.name}'", expr)
                return ERROR_TYPE
            return symbol.type
        elif isinstance(expr, ast.BinaryExpr):
            return self.infer_binary_expr_type(expr)
        elif isinstance(expr, ast.UnaryExpr):
            return self.infer_unary_expr_type(expr)
        elif isinstance(expr, ast.CallExpr):
            return self.infer_call_expr_type(expr)
        elif isinstance(expr, ast.MemberExpr):
            # TODO: Implement member type inference
            self.infer_expr_type(expr.obj)
            return UNKNOWN_TYPE
        elif isinstance(expr, ast.IndexExpr):
            # TODO: Implement index type inference
            self.infer_expr_type(expr.obj)
            self.infer_expr_type(expr.index)
            return UNKNOWN_TYPE
        elif isinstance(expr, ast.ListExpr):
            # TODO: Infer element type
            for elem in expr.elements:
                self.infer_expr_type(elem)
            return ListType(UNKNOWN_TYPE)
        elif isinstance(expr, ast.TupleExpr):
            elem_types = tuple(self.infer_expr_type(e) for e in expr.elements)
            return TupleType(elem_types)
        elif isinstance(expr, ast.ParenExpr):
            return self.infer_expr_type(expr.expr)
        else:
            return UNKNOWN_TYPE

    def infer_binary_expr_type(self, expr: ast.BinaryExpr) -> Type:
        """Infer type of binary expression."""
        left_type = self.infer_expr_type(expr.left)
        right_type = self.infer_expr_type(expr.right)

        # Arithmetic operators
        if expr.operator in ("+", "-", "*", "/", "%"):
            if not self.types_compatible(left_type, INT_TYPE):
                self.error(f"Arithmetic requires Int, got {left_type}", expr)
            if not self.types_compatible(right_type, INT_TYPE):
                self.error(f"Arithmetic requires Int, got {right_type}", expr)
            return INT_TYPE

        # Comparison operators
        elif expr.operator in ("==", "!=", "<", "<=", ">", ">="):
            if not self.types_compatible(left_type, right_type):
                self.error(
                    f"Cannot compare {left_type} with {right_type}",
                    expr,
                )
            return BOOL_TYPE

        # Logical operators
        elif expr.operator in ("and", "or"):
            if not self.types_compatible(left_type, BOOL_TYPE):
                self.error(f"Logical operator requires Bool, got {left_type}", expr)
            if not self.types_compatible(right_type, BOOL_TYPE):
                self.error(f"Logical operator requires Bool, got {right_type}", expr)
            return BOOL_TYPE

        return UNKNOWN_TYPE

    def infer_unary_expr_type(self, expr: ast.UnaryExpr) -> Type:
        """Infer type of unary expression."""
        operand_type = self.infer_expr_type(expr.operand)

        if expr.operator == "-":
            if not self.types_compatible(operand_type, INT_TYPE):
                self.error(f"Negation requires Int, got {operand_type}", expr)
            return INT_TYPE
        elif expr.operator == "not":
            if not self.types_compatible(operand_type, BOOL_TYPE):
                self.error(f"Logical not requires Bool, got {operand_type}", expr)
            return BOOL_TYPE

        return UNKNOWN_TYPE

    def infer_call_expr_type(self, expr: ast.CallExpr) -> Type:
        """Infer type of function call."""
        # Get function type
        if isinstance(expr.func, ast.Identifier):
            symbol = self.symbol_table.lookup(expr.func.name)
            if symbol is None:
                self.error(f"Undefined function '{expr.func.name}'", expr)
                return ERROR_TYPE

            if not isinstance(symbol.type, FunctionType):
                self.error(f"'{expr.func.name}' is not a function", expr)
                return ERROR_TYPE

            func_type = symbol.type

            # Check argument count
            if len(expr.args) != len(func_type.param_types):
                expected = len(func_type.param_types)
                actual = len(expr.args)
                self.error(
                    f"Function '{expr.func.name}' expects {expected} arguments, got {actual}",
                    expr,
                )

            # Check argument types
            for i, (arg, param_type) in enumerate(
                zip(expr.args, func_type.param_types, strict=False)
            ):
                arg_type = self.infer_expr_type(arg)
                if not self.types_compatible(arg_type, param_type):
                    self.error(
                        f"Argument {i+1} type mismatch: expected {param_type}, got {arg_type}",
                        expr,
                    )

            return func_type.return_type
        else:
            # TODO: Handle more complex function expressions
            return UNKNOWN_TYPE

    # Type utilities

    def resolve_type_expr(self, type_expr: ast.TypeExpr) -> Type:
        """Resolve a type expression to a Type."""
        if isinstance(type_expr, ast.SimpleType):
            name = str(type_expr.name)
            type_map = {
                "Int": INT_TYPE,
                "String": STRING_TYPE,
                "Bool": BOOL_TYPE,
                "Nil": NIL_TYPE,
            }
            return type_map.get(name, UNKNOWN_TYPE)  # TODO: Look up type aliases
        elif isinstance(type_expr, ast.FunctionType):
            param_types = tuple(self.resolve_type_expr(pt) for pt in type_expr.param_types)
            return_type = self.resolve_type_expr(type_expr.return_type)
            return FunctionType(param_types, return_type)
        return UNKNOWN_TYPE

    def types_compatible(self, actual: Type, expected: Type) -> bool:
        """Check if actual type is compatible with expected type."""
        # Handle error and unknown types
        if actual.kind == TypeKind.ERROR or expected.kind == TypeKind.ERROR:
            return True  # Error recovery
        if actual.kind == TypeKind.UNKNOWN or expected.kind == TypeKind.UNKNOWN:
            return True  # Allow unknown types during inference

        # Exact match
        return actual == expected


def analyze_module(module: ast.Module) -> tuple[SemanticAnalyzer, list[SemanticError]]:
    """Analyze a module and return the analyzer and any errors."""
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    return analyzer, analyzer.errors
