"""Semantic analysis for the Aster language.

This module provides symbol tables, type checking, and semantic validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path

from aster_lang import ast
from aster_lang.module_resolution import (
    ModuleResolutionError,
    ModuleSearchConfig,
    resolve_module_path,
)
from aster_lang.parser import parse_module

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
    BORROW = auto()
    POINTER = auto()
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
class BorrowType(Type):
    """Borrowed reference type: &T or &mut T"""

    inner: Type
    is_mutable: bool = False

    def __init__(self, inner: Type, *, is_mutable: bool = False) -> None:
        object.__setattr__(self, "kind", TypeKind.BORROW)
        object.__setattr__(self, "inner", inner)
        object.__setattr__(self, "is_mutable", is_mutable)

    def __str__(self) -> str:
        return f"&mut {self.inner}" if self.is_mutable else f"&{self.inner}"


@dataclass(frozen=True)
class PointerType(Type):
    """Smart/raw pointer types: *own T, *shared T, *weak T, *raw T"""

    pointer_kind: str
    inner: Type

    def __init__(self, pointer_kind: str, inner: Type) -> None:
        object.__setattr__(self, "kind", TypeKind.POINTER)
        object.__setattr__(self, "pointer_kind", pointer_kind)
        object.__setattr__(self, "inner", inner)

    def __str__(self) -> str:
        return f"*{self.pointer_kind} {self.inner}"


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
        # NOTE: Builtins are modeled loosely (Unknown types and relaxed arity checks)
        # so semantic analysis can proceed without a full stdlib type model.
        self.global_scope.define(
            Symbol(
                name="print",
                kind=SymbolKind.FUNCTION,
                # `print` is intentionally permissive; it accepts any printable value.
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=NIL_TYPE),
            )
        )
        self.global_scope.define(
            Symbol(
                name="len",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=INT_TYPE),
            )
        )
        self.global_scope.define(
            Symbol(
                name="str",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=STRING_TYPE),
            )
        )
        self.global_scope.define(
            Symbol(
                name="int",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=INT_TYPE),
            )
        )
        self.global_scope.define(
            Symbol(
                name="abs",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=UNKNOWN_TYPE),
            )
        )
        self.global_scope.define(
            Symbol(
                name="max",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=UNKNOWN_TYPE),
            )
        )
        self.global_scope.define(
            Symbol(
                name="min",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=UNKNOWN_TYPE),
            )
        )
        self.global_scope.define(
            Symbol(
                name="range",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=ListType(INT_TYPE)),
            )
        )

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


@dataclass
class SemanticWarning:
    """A semantic warning with location information."""

    message: str
    node: ast.Node | None = None

    def __str__(self) -> str:
        return f"Semantic warning: {self.message}"


class SemanticAnalyzer:
    """Semantic analyzer for the Aster language.

    Performs:
    - Symbol table construction
    - Name resolution
    - Type checking
    - Basic ownership checking
    """

    def __init__(
        self,
        *,
        base_dir: Path | None = None,
        dep_overrides: dict[str, Path] | None = None,
        extra_roots: tuple[Path, ...] = (),
        resolver_config: ModuleSearchConfig | None = None,
        allow_external_imports: bool = False,
        module_exports_cache: dict[Path, dict[str, Symbol]] | None = None,
        loading_modules: set[Path] | None = None,
    ) -> None:
        self.base_dir = base_dir
        self.dep_overrides: dict[str, Path] = dep_overrides or {}
        self.extra_roots: tuple[Path, ...] = extra_roots
        self.resolver_config = resolver_config
        self.allow_external_imports = allow_external_imports
        self.module_exports_cache = {} if module_exports_cache is None else module_exports_cache
        self.loading_modules = set() if loading_modules is None else loading_modules
        self.symbol_table = SymbolTable()
        self.errors: list[SemanticError] = []
        self.warnings: list[SemanticWarning] = []
        self.expr_types: dict[int, Type] = {}  # Map AST node id to inferred type
        # namespace name → exports for `use mod` (namespace) imports
        self._namespace_exports: dict[str, dict[str, Symbol]] = {}
        # Avoid spamming warnings for every type annotation.
        self._warned_borrow_surface = False
        self._warned_pointer_surface = False
        self._warned_raw_pointer = False

    def error(self, message: str, node: ast.Node | None = None) -> None:
        """Record a semantic error."""
        self.errors.append(SemanticError(message, node))

    def warn(self, message: str, node: ast.Node | None = None) -> None:
        """Record a semantic warning."""
        self.warnings.append(SemanticWarning(message, node))

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
        """Analyze a top-level binding declaration."""
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
        exports = self._load_module_exports(decl)
        if exports is None:
            if self.allow_external_imports:
                # Treat unresolved imports as external Python modules during `check/build`.
                if decl.imports:
                    # We can't validate exports for external modules.
                    module_label = ".".join(decl.module.parts)
                    self.error(
                        f"Cannot import names from external module '{module_label}'",
                        decl,
                    )
                    return
                binding_name = decl.alias if decl.alias is not None else decl.module.parts[-1]
                self.symbol_table.define(
                    Symbol(
                        name=binding_name,
                        kind=SymbolKind.MODULE,
                        type=UNKNOWN_TYPE,
                        declaration_node=decl,
                    )
                )
                return
            return

        if decl.imports:
            for name in decl.imports:
                if name not in exports:
                    module_label = ".".join(decl.module.parts)
                    self.error(
                        f"Module '{module_label}' has no public export '{name}'",
                        decl,
                    )
                    continue
                self.symbol_table.define(exports[name])
            return

        binding_name = decl.alias if decl.alias is not None else decl.module.parts[-1]
        self.symbol_table.define(
            Symbol(
                name=binding_name,
                kind=SymbolKind.VARIABLE,
                type=UNKNOWN_TYPE,
                declaration_node=decl,
            )
        )
        self._namespace_exports[binding_name] = exports

    def _load_module_exports(self, decl: ast.ImportDecl) -> dict[str, Symbol] | None:
        """Load exported top-level symbols from a sibling .aster module."""
        module_name = ".".join(decl.module.parts)
        module_path = self._resolve_module_path(decl.module)
        if module_path is None:
            return None
        if module_path in self.module_exports_cache:
            return self.module_exports_cache[module_path]
        if module_path in self.loading_modules:
            self.error(f"Cyclic import detected for module '{module_name}'", decl)
            return None

        self.loading_modules.add(module_path)
        try:
            module = parse_module(module_path.read_text(encoding="utf-8"))
            for inner_decl in module.declarations:
                if isinstance(inner_decl, ast.ImportDecl):
                    self._load_module_exports(inner_decl)
            exports = self._collect_module_exports(module)
            self.module_exports_cache[module_path] = exports
            return exports
        finally:
            self.loading_modules.remove(module_path)

    def _resolve_module_path(self, module_name: ast.QualifiedName) -> Path | None:
        """Resolve a dotted module name from the current base directory."""
        try:
            return resolve_module_path(
                self.base_dir,
                module_name.parts,
                dep_overrides=self.dep_overrides or None,
                extra_roots=self.extra_roots,
                config=self.resolver_config,
            )
        except ModuleResolutionError as exc:
            if not self.allow_external_imports:
                self.error(str(exc), module_name)
            return None

    def _collect_module_exports(self, module: ast.Module) -> dict[str, Symbol]:
        """Collect exported top-level symbols from a module."""
        exports: dict[str, Symbol] = {}
        for decl in module.declarations:
            if isinstance(decl, ast.FunctionDecl):
                if not decl.is_public:
                    continue
                param_types = tuple(
                    self.resolve_type_expr(param.type_annotation)
                    if param.type_annotation is not None
                    else UNKNOWN_TYPE
                    for param in decl.params
                )
                return_type = (
                    self.resolve_type_expr(decl.return_type)
                    if decl.return_type is not None
                    else NIL_TYPE
                )
                exports[decl.name] = Symbol(
                    name=decl.name,
                    kind=SymbolKind.FUNCTION,
                    type=FunctionType(param_types, return_type),
                    declaration_node=decl,
                )
            elif isinstance(decl, ast.LetDecl):
                if not decl.is_public:
                    continue
                exported_type = (
                    self.resolve_type_expr(decl.type_annotation)
                    if decl.type_annotation is not None
                    else self._infer_exported_let_type(decl.initializer)
                )
                exports[decl.name] = Symbol(
                    name=decl.name,
                    kind=SymbolKind.VARIABLE,
                    type=exported_type,
                    is_mutable=decl.is_mutable,
                    declaration_node=decl,
                )
            elif isinstance(decl, ast.TypeAliasDecl):
                if not decl.is_public:
                    continue
                exports[decl.name] = Symbol(
                    name=decl.name,
                    kind=SymbolKind.TYPE_ALIAS,
                    type=self.resolve_type_expr(decl.type_expr),
                    declaration_node=decl,
                )
        return exports

    def _infer_exported_let_type(self, expr: ast.Expr) -> Type:
        """Infer an imported top-level binding type without full module analysis."""
        if isinstance(expr, ast.IntegerLiteral):
            return INT_TYPE
        if isinstance(expr, ast.StringLiteral):
            return STRING_TYPE
        if isinstance(expr, ast.BoolLiteral):
            return BOOL_TYPE
        if isinstance(expr, ast.NilLiteral):
            return NIL_TYPE
        return UNKNOWN_TYPE

    def analyze_type_alias_decl(self, decl: ast.TypeAliasDecl) -> None:
        """Analyze a type alias declaration."""
        resolved_type = self.resolve_type_expr(decl.type_expr)
        if self.symbol_table.lookup(decl.name) is not None:
            self.error(f"Type '{decl.name}' is already defined", decl)
            return
        self.symbol_table.define(
            Symbol(
                name=decl.name,
                kind=SymbolKind.TYPE_ALIAS,
                type=resolved_type,
                declaration_node=decl,
            )
        )

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
        """Analyze a binding statement."""
        # Infer type from initializer
        init_type = self.infer_expr_type(stmt.initializer)

        if isinstance(stmt.pattern, ast.BindingPattern):
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

            symbol = Symbol(
                name=stmt.name,
                kind=SymbolKind.VARIABLE,
                type=final_type,
                is_mutable=stmt.is_mutable,
                declaration_node=stmt,
            )

            if not self.symbol_table.define(symbol):
                self.error(f"Variable '{stmt.name}' is already defined", stmt)
            return

        self._analyze_binding_pattern(
            stmt.pattern,
            init_type,
            stmt.initializer,
            stmt,
            is_mutable=stmt.is_mutable,
        )

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
            return

        # Member/index lvalues: only supported when the receiver is an identifier.
        if isinstance(stmt.target, ast.MemberExpr) and isinstance(stmt.target.obj, ast.Identifier):
            base = self.symbol_table.lookup(stmt.target.obj.name)
            if base is None:
                self.error(f"Undefined variable '{stmt.target.obj.name}'", stmt)
                return
            if not base.is_mutable:
                self.error(
                    f"Cannot assign through immutable variable '{stmt.target.obj.name}'",
                    stmt,
                )
            self.infer_expr_type(stmt.value)
            return

        if isinstance(stmt.target, ast.IndexExpr) and isinstance(stmt.target.obj, ast.Identifier):
            base = self.symbol_table.lookup(stmt.target.obj.name)
            if base is None:
                self.error(f"Undefined variable '{stmt.target.obj.name}'", stmt)
                return
            if not base.is_mutable:
                self.error(
                    f"Cannot assign through immutable variable '{stmt.target.obj.name}'",
                    stmt,
                )
            self.infer_expr_type(stmt.target.index)
            self.infer_expr_type(stmt.value)
            return

        self.error("Invalid assignment target", stmt)

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
        subject_type = self.infer_expr_type(stmt.subject)
        for arm in stmt.arms:
            self.symbol_table.enter_scope("<match-arm>")
            self._analyze_pattern(arm.pattern, subject_type, stmt.subject, stmt)
            for s in arm.body:
                self.analyze_statement(s)
            self.symbol_table.exit_scope()

    def _analyze_pattern(
        self,
        pattern: ast.Pattern,
        subject_type: Type,
        source_expr: ast.Expr | None,
        node: ast.Node,
    ) -> None:
        """Analyze a pattern and define any bindings in the current scope."""
        if isinstance(pattern, ast.BindingPattern):
            bound = Symbol(
                name=pattern.name,
                kind=SymbolKind.VARIABLE,
                type=subject_type,
                declaration_node=node,
            )
            self.symbol_table.define(bound)
            return
        if isinstance(pattern, ast.RestPattern):
            bound = Symbol(
                name=pattern.name,
                kind=SymbolKind.VARIABLE,
                type=subject_type,
                declaration_node=node,
            )
            self.symbol_table.define(bound)
            return
        if isinstance(pattern, ast.OrPattern):
            name_sets = [self._collect_pattern_names(option) for option in pattern.alternatives]
            first_set = name_sets[0]
            for other_set in name_sets[1:]:
                if other_set != first_set:
                    self.error("Or-pattern alternatives must bind exactly the same names", node)
                    return
            # Analyze only the first alternative so bindings are defined once in scope
            self._analyze_pattern(pattern.alternatives[0], subject_type, source_expr, node)
            return
        if isinstance(pattern, ast.TuplePattern):
            if not self._validate_rest_position(pattern.elements, node):
                return
            if isinstance(subject_type, TupleType):
                rest_index = self._rest_index(pattern.elements)
                if rest_index is None and len(pattern.elements) != len(subject_type.element_types):
                    self.error("Tuple pattern arity mismatch", node)
                    return
                if (
                    rest_index is not None
                    and len(subject_type.element_types) < len(pattern.elements) - 1
                ):
                    self.error("Tuple pattern arity mismatch", node)
                    return
                self._analyze_sequence_pattern(
                    pattern.elements,
                    subject_type.element_types,
                    node=node,
                    source_expr=source_expr,
                    sequence_kind="tuple",
                )
                return
            for subpattern in pattern.elements:
                self._analyze_pattern(subpattern, UNKNOWN_TYPE, None, node)
            return
        if isinstance(pattern, ast.ListPattern):
            if not self._validate_rest_position(pattern.elements, node):
                return
            known_length = (
                self._infer_list_length_expr(source_expr) if source_expr is not None else None
            )
            rest_index = self._rest_index(pattern.elements)
            if known_length is not None:
                if rest_index is None and len(pattern.elements) != known_length:
                    self.error("List pattern arity mismatch", node)
                    return
                if rest_index is not None and known_length < len(pattern.elements) - 1:
                    self.error("List pattern arity mismatch", node)
                    return

            element_type: Type = UNKNOWN_TYPE
            if isinstance(subject_type, ListType):
                element_type = subject_type.element_type
            if rest_index is not None and isinstance(subject_type, ListType):
                self._analyze_sequence_pattern(
                    pattern.elements,
                    tuple(
                        element_type for _ in range(max(known_length or len(pattern.elements), 0))
                    ),
                    node=node,
                    source_expr=source_expr,
                    sequence_kind="list",
                    fallback_element_type=element_type,
                )
                return
            for subpattern in pattern.elements:
                subpattern_type = (
                    ListType(element_type)
                    if isinstance(subpattern, ast.RestPattern)
                    else element_type
                )
                self._analyze_pattern(subpattern, subpattern_type, None, node)
            return
        if isinstance(pattern, ast.RecordPattern):
            known_fields = (
                self._infer_record_fields_expr(source_expr) if source_expr is not None else None
            )
            for field in pattern.fields:
                if known_fields is not None and field.name not in known_fields:
                    self.error(f"Record pattern field '{field.name}' not found", node)
                    continue
                self._analyze_pattern(field.pattern, UNKNOWN_TYPE, None, node)

    def _analyze_binding_pattern(
        self,
        pattern: ast.Pattern,
        subject_type: Type,
        source_expr: ast.Expr,
        node: ast.Node,
        *,
        is_mutable: bool,
    ) -> None:
        """Analyze a local binding pattern against an initializer."""
        if isinstance(pattern, ast.BindingPattern):
            symbol = Symbol(
                name=pattern.name,
                kind=SymbolKind.VARIABLE,
                type=subject_type,
                is_mutable=is_mutable,
                declaration_node=node,
            )
            if not self.symbol_table.define(symbol):
                self.error(f"Variable '{pattern.name}' is already defined", node)
            return
        if isinstance(pattern, ast.WildcardPattern):
            return
        if isinstance(pattern, ast.RestPattern):
            symbol = Symbol(
                name=pattern.name,
                kind=SymbolKind.VARIABLE,
                type=subject_type,
                is_mutable=is_mutable,
                declaration_node=node,
            )
            if not self.symbol_table.define(symbol):
                self.error(f"Variable '{pattern.name}' is already defined", node)
            return
        if isinstance(pattern, ast.TuplePattern):
            if not self._validate_rest_position(pattern.elements, node):
                return
            if isinstance(subject_type, TupleType):
                rest_index = self._rest_index(pattern.elements)
                if rest_index is None and len(pattern.elements) != len(subject_type.element_types):
                    self.error("Tuple binding arity mismatch", node)
                    return
                if (
                    rest_index is not None
                    and len(subject_type.element_types) < len(pattern.elements) - 1
                ):
                    self.error("Tuple binding arity mismatch", node)
                    return
                self._analyze_sequence_binding_pattern(
                    pattern.elements,
                    subject_type.element_types,
                    node=node,
                    source_expr=source_expr,
                    sequence_kind="tuple",
                    is_mutable=is_mutable,
                )
                return
            for subpattern in pattern.elements:
                self._analyze_binding_pattern(
                    subpattern,
                    UNKNOWN_TYPE,
                    source_expr,
                    node,
                    is_mutable=is_mutable,
                )
            return
        if isinstance(pattern, ast.ListPattern):
            if not self._validate_rest_position(pattern.elements, node):
                return
            known_length = self._infer_list_length_expr(source_expr)
            rest_index = self._rest_index(pattern.elements)
            if known_length is not None:
                if rest_index is None and len(pattern.elements) != known_length:
                    self.error("List binding arity mismatch", node)
                    return
                if rest_index is not None and known_length < len(pattern.elements) - 1:
                    self.error("List binding arity mismatch", node)
                    return

            element_type: Type = (
                subject_type.element_type if isinstance(subject_type, ListType) else UNKNOWN_TYPE
            )
            known_element_types: tuple[Type, ...] | None = None
            if known_length is not None:
                known_element_types = tuple(element_type for _ in range(known_length))
            if known_element_types is not None:
                self._analyze_sequence_binding_pattern(
                    pattern.elements,
                    known_element_types,
                    node=node,
                    source_expr=source_expr,
                    sequence_kind="list",
                    fallback_element_type=element_type,
                    is_mutable=is_mutable,
                )
            else:
                for subpattern in pattern.elements:
                    subpattern_type = (
                        ListType(element_type)
                        if isinstance(subpattern, ast.RestPattern)
                        else element_type
                    )
                    self._analyze_binding_pattern(
                        subpattern,
                        subpattern_type,
                        source_expr,
                        node,
                        is_mutable=is_mutable,
                    )
            return
        if isinstance(pattern, ast.RecordPattern):
            known_fields = self._infer_record_fields_expr(source_expr)
            for field in pattern.fields:
                if known_fields is not None and field.name not in known_fields:
                    self.error(f"Record binding field '{field.name}' not found", node)
                    continue
                self._analyze_binding_pattern(
                    field.pattern,
                    UNKNOWN_TYPE,
                    source_expr,
                    node,
                    is_mutable=is_mutable,
                )

    def _analyze_sequence_pattern(
        self,
        patterns: list[ast.Pattern],
        element_types: tuple[Type, ...],
        *,
        node: ast.Node,
        source_expr: ast.Expr | None,
        sequence_kind: str,
        fallback_element_type: Type | None = None,
    ) -> None:
        """Analyze tuple/list match patterns with rest support."""
        rest_index = self._rest_index(patterns)
        if rest_index is None:
            for subpattern, element_type in zip(patterns, element_types, strict=False):
                self._analyze_pattern(subpattern, element_type, None, node)
            return

        prefix = patterns[:rest_index]
        suffix = patterns[rest_index + 1 :]
        for subpattern, element_type in zip(prefix, element_types[:rest_index], strict=False):
            self._analyze_pattern(subpattern, element_type, None, node)

        fallback = fallback_element_type if fallback_element_type is not None else UNKNOWN_TYPE
        middle_types = element_types[rest_index : len(element_types) - len(suffix)]
        if sequence_kind == "tuple":
            rest_type: Type = TupleType(middle_types)
        else:
            rest_type = ListType(middle_types[0] if middle_types else fallback)
        self._analyze_pattern(patterns[rest_index], rest_type, None, node)

        suffix_types = element_types[len(element_types) - len(suffix) :]
        for subpattern, element_type in zip(suffix, suffix_types, strict=False):
            self._analyze_pattern(subpattern, element_type, None, node)

    def _analyze_sequence_binding_pattern(
        self,
        patterns: list[ast.Pattern],
        element_types: tuple[Type, ...],
        *,
        node: ast.Node,
        source_expr: ast.Expr,
        sequence_kind: str,
        is_mutable: bool,
        fallback_element_type: Type | None = None,
    ) -> None:
        """Analyze tuple/list binding patterns with rest support."""
        rest_index = self._rest_index(patterns)
        if rest_index is None:
            for subpattern, element_type in zip(patterns, element_types, strict=False):
                self._analyze_binding_pattern(
                    subpattern,
                    element_type,
                    source_expr,
                    node,
                    is_mutable=is_mutable,
                )
            return

        prefix = patterns[:rest_index]
        suffix = patterns[rest_index + 1 :]
        for subpattern, element_type in zip(prefix, element_types[:rest_index], strict=False):
            self._analyze_binding_pattern(
                subpattern,
                element_type,
                source_expr,
                node,
                is_mutable=is_mutable,
            )

        fallback = fallback_element_type if fallback_element_type is not None else UNKNOWN_TYPE
        middle_types = element_types[rest_index : len(element_types) - len(suffix)]
        if sequence_kind == "tuple":
            rest_type: Type = TupleType(middle_types)
        else:
            rest_type = ListType(middle_types[0] if middle_types else fallback)
        self._analyze_binding_pattern(
            patterns[rest_index],
            rest_type,
            source_expr,
            node,
            is_mutable=is_mutable,
        )

        suffix_types = element_types[len(element_types) - len(suffix) :]
        for subpattern, element_type in zip(suffix, suffix_types, strict=False):
            self._analyze_binding_pattern(
                subpattern,
                element_type,
                source_expr,
                node,
                is_mutable=is_mutable,
            )

    def _known_list_length(self, node: ast.Node) -> int | None:
        """Infer list length for simple literal-backed match subjects."""
        if not isinstance(node, ast.MatchStmt):
            return None
        return self._infer_list_length_expr(node.subject)

    def _infer_list_length_expr(self, expr: ast.Expr) -> int | None:
        """Infer a known literal list length from an expression when available."""
        if isinstance(expr, ast.ListExpr):
            return len(expr.elements)
        if isinstance(expr, ast.Identifier):
            symbol = self.symbol_table.lookup(expr.name)
            if symbol is None or symbol.declaration_node is None:
                return None
            decl = symbol.declaration_node
            if isinstance(
                decl,
                ast.LetStmt | ast.LetDecl,
            ) and isinstance(decl.initializer, ast.ListExpr):
                return len(decl.initializer.elements)
        return None

    def _known_record_fields(self, node: ast.Node) -> set[str] | None:
        """Infer known record fields for simple literal-backed match subjects."""
        if not isinstance(node, ast.MatchStmt):
            return None
        return self._infer_record_fields_expr(node.subject)

    def _infer_record_fields_expr(self, expr: ast.Expr) -> set[str] | None:
        """Infer record field names from an expression when available."""
        if isinstance(expr, ast.RecordExpr):
            return {field.name for field in expr.fields}
        if isinstance(expr, ast.Identifier):
            symbol = self.symbol_table.lookup(expr.name)
            if symbol is None or symbol.declaration_node is None:
                return None
            decl = symbol.declaration_node
            if isinstance(
                decl,
                ast.LetStmt | ast.LetDecl,
            ) and isinstance(decl.initializer, ast.RecordExpr):
                return {field.name for field in decl.initializer.fields}
        return None

    def _pattern_binds_names(self, pattern: ast.Pattern) -> bool:
        """Return whether a pattern introduces any bindings."""
        return bool(self._collect_pattern_names(pattern))

    def _collect_pattern_names(self, pattern: ast.Pattern) -> set[str]:
        """Return the set of names bound by a pattern."""
        if isinstance(pattern, ast.BindingPattern):
            return {pattern.name}
        if isinstance(pattern, ast.RestPattern):
            return {pattern.name}
        if isinstance(pattern, ast.OrPattern):
            # Union across alternatives (used when checking if any alternative binds)
            result: set[str] = set()
            for option in pattern.alternatives:
                result |= self._collect_pattern_names(option)
            return result
        if isinstance(pattern, ast.TuplePattern | ast.ListPattern):
            result = set()
            for element in pattern.elements:
                result |= self._collect_pattern_names(element)
            return result
        if isinstance(pattern, ast.RecordPattern):
            result = set()
            for field in pattern.fields:
                result |= self._collect_pattern_names(field.pattern)
            return result
        return set()

    def _rest_index(self, elements: list[ast.Pattern]) -> int | None:
        """Return the index of a rest pattern if one is present."""
        for index, element in enumerate(elements):
            if isinstance(element, ast.RestPattern):
                return index
        return None

    def _validate_rest_position(self, elements: list[ast.Pattern], node: ast.Node) -> bool:
        """Ensure tuple/list rest patterns are trailing and unique."""
        rest_indices = [
            index for index, element in enumerate(elements) if isinstance(element, ast.RestPattern)
        ]
        if not rest_indices:
            return True
        if len(rest_indices) > 1 or rest_indices[0] != len(elements) - 1:
            self.error("Rest pattern must be trailing", node)
            return False
        return True

    # Type inference

    def infer_expr_type(self, expr: ast.Expr) -> Type:
        """Infer the type of an expression."""

        def remember(t: Type) -> Type:
            self.expr_types[id(expr)] = t
            return t

        if isinstance(expr, ast.IntegerLiteral):
            return remember(INT_TYPE)
        elif isinstance(expr, ast.StringLiteral):
            return remember(STRING_TYPE)
        elif isinstance(expr, ast.BoolLiteral):
            return remember(BOOL_TYPE)
        elif isinstance(expr, ast.NilLiteral):
            return remember(NIL_TYPE)
        elif isinstance(expr, ast.Identifier):
            symbol = self.symbol_table.lookup(expr.name)
            if symbol is None:
                self.error(f"Undefined variable '{expr.name}'", expr)
                return remember(ERROR_TYPE)
            return remember(symbol.type)
        elif isinstance(expr, ast.BinaryExpr):
            return remember(self.infer_binary_expr_type(expr))
        elif isinstance(expr, ast.UnaryExpr):
            return remember(self.infer_unary_expr_type(expr))
        elif isinstance(expr, ast.CallExpr):
            return remember(self.infer_call_expr_type(expr))
        elif isinstance(expr, ast.LambdaExpr):
            param_types: list[Type] = []
            self.symbol_table.enter_scope("<lambda>")
            try:
                for p in expr.params:
                    pt = (
                        self.resolve_type_expr(p.type_annotation)
                        if p.type_annotation
                        else UNKNOWN_TYPE
                    )
                    param_types.append(pt)
                    self.symbol_table.define(
                        Symbol(
                            name=p.name,
                            kind=SymbolKind.PARAMETER,
                            type=pt,
                            declaration_node=p,
                        )
                    )

                ret_t: Type
                if isinstance(expr.body, list):
                    for stmt in expr.body:
                        self.analyze_statement(stmt)
                    ret_t = UNKNOWN_TYPE
                else:
                    ret_t = self.infer_expr_type(expr.body)
            finally:
                self.symbol_table.exit_scope()
            return remember(FunctionType(tuple(param_types), ret_t))
        elif isinstance(expr, ast.MemberExpr):
            # TODO: Implement member type inference
            self.infer_expr_type(expr.obj)
            return remember(UNKNOWN_TYPE)
        elif isinstance(expr, ast.IndexExpr):
            # TODO: Implement index type inference
            self.infer_expr_type(expr.obj)
            self.infer_expr_type(expr.index)
            return remember(UNKNOWN_TYPE)
        elif isinstance(expr, ast.ListExpr):
            # TODO: Infer element type
            for elem in expr.elements:
                self.infer_expr_type(elem)
            return remember(ListType(UNKNOWN_TYPE))
        elif isinstance(expr, ast.TupleExpr):
            elem_types = tuple(self.infer_expr_type(e) for e in expr.elements)
            return remember(TupleType(elem_types))
        elif isinstance(expr, ast.ParenExpr):
            return remember(self.infer_expr_type(expr.expr))
        else:
            return remember(UNKNOWN_TYPE)

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

            # Builtins: arity/type rules are intentionally loose for now.
            # This keeps semantic analysis usable while the stdlib type model evolves.
            variadic = {"print", "max", "min"}
            poly_arity = {"range"}  # 1 or 2 args
            if expr.func.name in variadic:
                for arg in expr.args:
                    self.infer_expr_type(arg)
                return func_type.return_type
            if expr.func.name in poly_arity:
                for arg in expr.args:
                    self.infer_expr_type(arg)
                return func_type.return_type

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
            callee_t = self.infer_expr_type(expr.func)
            for arg in expr.args:
                self.infer_expr_type(arg)
            if not isinstance(callee_t, FunctionType):
                return UNKNOWN_TYPE

            if len(expr.args) != len(callee_t.param_types):
                expected = len(callee_t.param_types)
                actual = len(expr.args)
                self.error(
                    f"Function call expects {expected} arguments, got {actual}",
                    expr,
                )

            for i, (arg, param_type) in enumerate(
                zip(expr.args, callee_t.param_types, strict=False)
            ):
                arg_type = self.infer_expr_type(arg)
                if not self.types_compatible(arg_type, param_type):
                    self.error(
                        f"Argument {i+1} type mismatch: expected {param_type}, got {arg_type}",
                        expr,
                    )

            return callee_t.return_type

    # Type utilities

    def resolve_type_expr(self, type_expr: ast.TypeExpr) -> Type:
        """Resolve a type expression to a Type."""
        if isinstance(type_expr, ast.SimpleType):
            parts = type_expr.name.parts
            if len(parts) == 1:
                name = parts[0]
                type_map = {
                    "Int": INT_TYPE,
                    "String": STRING_TYPE,
                    "Bool": BOOL_TYPE,
                    "Nil": NIL_TYPE,
                }
                if name in type_map:
                    return type_map[name]
                symbol = self.symbol_table.lookup(name)
                if symbol is not None and symbol.kind == SymbolKind.TYPE_ALIAS:
                    return symbol.type
                return UNKNOWN_TYPE
            if len(parts) == 2:
                namespace, member = parts
                ns_exports = self._namespace_exports.get(namespace)
                if ns_exports is not None:
                    sym = ns_exports.get(member)
                    if sym is not None and sym.kind == SymbolKind.TYPE_ALIAS:
                        return sym.type
            return UNKNOWN_TYPE
        elif isinstance(type_expr, ast.FunctionType):
            param_types = tuple(self.resolve_type_expr(pt) for pt in type_expr.param_types)
            return_type = self.resolve_type_expr(type_expr.return_type)
            return FunctionType(param_types, return_type)
        elif isinstance(type_expr, ast.BorrowTypeExpr):
            if not self._warned_borrow_surface:
                self.warn(
                    "Borrow types (&T, &mut T) are parsed and type-checked structurally, "
                    "but borrow/aliasing rules are not enforced yet.",
                    type_expr,
                )
                self._warned_borrow_surface = True
            inner = self.resolve_type_expr(type_expr.inner)
            return BorrowType(inner, is_mutable=type_expr.is_mutable)
        elif isinstance(type_expr, ast.PointerTypeExpr):
            if not self._warned_pointer_surface:
                self.warn(
                    (
                        "Pointer types (*own/*shared/*weak/*raw) are parsed and type-checked "
                        "structurally, but ownership/move rules are not enforced yet."
                    ),
                    type_expr,
                )
                self._warned_pointer_surface = True
            inner = self.resolve_type_expr(type_expr.inner)
            if type_expr.pointer_kind not in {"own", "shared", "weak", "raw"}:
                self.error(
                    (
                        f"Unknown pointer kind '*{type_expr.pointer_kind}'. "
                        "Expected one of: own, shared, weak, raw."
                    ),
                    type_expr,
                )
            elif type_expr.pointer_kind == "raw" and not self._warned_raw_pointer:
                self.warn(
                    "Raw pointers (*raw T) are unsafe; no safety checks are implemented yet.",
                    type_expr,
                )
                self._warned_raw_pointer = True
            return PointerType(type_expr.pointer_kind, inner)
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
