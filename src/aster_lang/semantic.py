"""Semantic analysis for the Aster language.

This module provides symbol tables, type checking, and semantic validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    BITS = auto()
    TYPEVAR = auto()
    FLOAT = auto()
    UNKNOWN = auto()  # For type inference
    ERROR = auto()  # For error recovery


class OwnershipMode(Enum):
    """How aggressively to apply ownership/borrow surface diagnostics."""

    OFF = "off"
    WARN = "warn"
    DENY = "deny"


@dataclass
class _OwnVarState:
    move_only: bool
    moved: bool = False


@dataclass
class _BorrowState:
    mutably_borrowed_by: str | None = None
    immutably_borrowed_by: set[str] = field(default_factory=set)


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
class FloatType(Type):
    """Floating-point type."""

    def __init__(self) -> None:
        object.__setattr__(self, "kind", TypeKind.FLOAT)

    def __str__(self) -> str:
        return "Float"


@dataclass(frozen=True)
class BitsType(Type):
    """Fixed-width unsigned integer type (Nibble/Byte/Word/DWord/QWord)."""

    name: str
    bits: int

    def __init__(self, name: str, bits: int) -> None:
        object.__setattr__(self, "kind", TypeKind.BITS)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "bits", bits)

    def __str__(self) -> str:
        return self.name


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
    """Function type: (T1, T2, ...) -> R !effect"""

    param_types: tuple[Type, ...]
    return_type: Type
    # Generic type parameters and their trait bounds: name -> (Bound1, Bound2, ...)
    type_params: dict[str, tuple[str, ...]]
    # Declared effects for this function.
    effects: tuple[str, ...]

    def __init__(
        self,
        param_types: tuple[Type, ...],
        return_type: Type,
        type_params: dict[str, tuple[str, ...]] | None = None,
        effects: tuple[str, ...] = (),
    ) -> None:
        object.__setattr__(self, "kind", TypeKind.FUNCTION)
        object.__setattr__(self, "param_types", param_types)
        object.__setattr__(self, "return_type", return_type)
        object.__setattr__(self, "type_params", type_params or {})
        object.__setattr__(self, "effects", effects)

    def __str__(self) -> str:
        params = ", ".join(str(t) for t in self.param_types)
        base = f"Fn({params}) -> {self.return_type}"
        if self.effects:
            base += " " + " ".join(f"!{e}" for e in self.effects)
        return base


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
class TypeVarType(Type):
    """Type variable (type parameter) such as T."""

    name: str

    def __init__(self, name: str) -> None:
        object.__setattr__(self, "kind", TypeKind.TYPEVAR)
        object.__setattr__(self, "name", name)

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class SelfType(Type):
    """Placeholder for 'Self' type inside traits."""

    def __init__(self) -> None:
        object.__setattr__(self, "kind", TypeKind.TYPEVAR)

    def __str__(self) -> str:
        return "Self"


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
NIBBLE_TYPE = BitsType("Nibble", 4)
BYTE_TYPE = BitsType("Byte", 8)
WORD_TYPE = BitsType("Word", 16)
DWORD_TYPE = BitsType("DWord", 32)
QWORD_TYPE = BitsType("QWord", 64)
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
    TYPE_PARAM = auto()
    TRAIT = auto()
    MODULE = auto()
    EFFECT = auto()


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
        self.global_scope.define(
            Symbol(
                name="ord",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(STRING_TYPE,), return_type=INT_TYPE),
            )
        )
        self.global_scope.define(
            Symbol(
                name="ascii_bytes",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(STRING_TYPE,), return_type=ListType(BYTE_TYPE)),
            )
        )
        self.global_scope.define(
            Symbol(
                name="unicode_bytes",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(STRING_TYPE,), return_type=ListType(BYTE_TYPE)),
            )
        )
        # Fixed-width integer casts.
        self.global_scope.define(
            Symbol(
                name="nibble",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=NIBBLE_TYPE),
            )
        )
        self.global_scope.define(
            Symbol(
                name="byte",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=BYTE_TYPE),
            )
        )
        self.global_scope.define(
            Symbol(
                name="word",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=WORD_TYPE),
            )
        )
        self.global_scope.define(
            Symbol(
                name="dword",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=DWORD_TYPE),
            )
        )
        self.global_scope.define(
            Symbol(
                name="qword",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=QWORD_TYPE),
            )
        )
        # assert(condition) / assert(condition, message) — used in test files.
        self.global_scope.define(
            Symbol(
                name="assert",
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types=(UNKNOWN_TYPE,), return_type=NIL_TYPE),
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
        strict_types: bool = False,
        ownership_mode: OwnershipMode = OwnershipMode.OFF,
        module_exports_cache: dict[Path, dict[str, Symbol]] | None = None,
        loading_modules: set[Path] | None = None,
    ) -> None:
        self.base_dir = base_dir
        self.dep_overrides: dict[str, Path] = dep_overrides or {}
        self.extra_roots: tuple[Path, ...] = extra_roots
        self.resolver_config = resolver_config
        self.allow_external_imports = allow_external_imports
        self.strict_types = strict_types
        self.ownership_mode = ownership_mode
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
        # Trait prototype: name -> required method signatures.
        self._traits: dict[str, dict[str, FunctionType]] = {}
        # Namespace imports: ns -> trait name -> methods
        self._namespace_traits: dict[str, dict[str, dict[str, FunctionType]]] = {}
        # Cache trait method sets for imported modules by path.
        self._module_trait_cache: dict[Path, dict[str, dict[str, FunctionType]]] = {}
        # Persisted generic params (for later passes like ownership).
        # node_id -> { type_param_name: (trait_bound1, trait_bound2, ...) }
        self.decl_type_params: dict[int, dict[str, tuple[str, ...]]] = {}
        # Live type-param bounds for the current function scope (trait call-site resolution).
        # type_var_name -> tuple of trait name refs (simple "TraitName" or "ns.TraitName")
        self._current_typevar_bounds: dict[str, tuple[str, ...]] = {}
        # Trait implementations: (Type, TraitName) -> methods.
        # TraitName is a simple "TraitName" or "ns.TraitName" string.
        self._impls: dict[tuple[Type, str], dict[str, FunctionType]] = {}
        # The 'Self' type for the current trait/impl scope.
        self._current_self_type: Type | None = None
        # Effect tracking prototype.
        # Set of declared effect names in the module.
        self._declared_effects: set[str] = set()
        # Effects declared by the current function being analyzed (empty = no constraint).
        self._current_fn_effects: tuple[str, ...] = ()
        # Whether we are currently inside a function body (vs. top-level).
        self._inside_function: bool = False
        # Ownership/borrow prototype enforcement (opt-in).
        # Stack of scopes: name -> moved-state.
        self._own_scopes: list[dict[str, _OwnVarState]] = [{}]
        # Stack of scopes: borrowed variable name -> borrow state.
        self._borrow_scopes: list[dict[str, _BorrowState]] = [{}]
        # Stack of scopes: reference variable name -> borrowed target name.
        self._ref_scopes: list[dict[str, str]] = [{}]

    def _own_diag(self, message: str, node: ast.Node | None = None) -> None:
        if self.ownership_mode == OwnershipMode.WARN:
            self.warn(message, node)
        elif self.ownership_mode == OwnershipMode.DENY:
            self.error(message, node)

    def _enter_scope(self, name: str = "<block>") -> None:
        self.symbol_table.enter_scope(name)
        self._own_scopes.append({})
        self._borrow_scopes.append({})
        self._ref_scopes.append({})

    def _exit_scope(self) -> None:
        self.symbol_table.exit_scope()
        self._own_scopes.pop()
        self._borrow_scopes.pop()
        self._ref_scopes.pop()

    def _ref_origin(self, name: str) -> str | None:
        for scope in reversed(self._ref_scopes):
            target = scope.get(name)
            if target is not None:
                return target
        return None

    def _is_global_symbol(self, sym: Symbol) -> bool:
        return self.symbol_table.global_scope.lookup_local(sym.name) is sym

    def _is_global_name(self, name: str) -> bool:
        sym = self.symbol_table.lookup(name)
        if sym is None:
            return False
        return self._is_global_symbol(sym)

    def _expr_is_reference_value(self, expr: ast.Expr) -> bool:
        if isinstance(expr, ast.BorrowExpr):
            return True
        if isinstance(expr, ast.Identifier):
            sym = self.symbol_table.lookup(expr.name)
            return sym is not None and isinstance(sym.type, BorrowType)
        return False

    def _borrow_base_name(self, target: ast.Expr) -> str | None:
        if isinstance(target, ast.Identifier):
            return target.name
        if isinstance(target, ast.MemberExpr):
            return self._borrow_base_name(target.obj)
        if isinstance(target, ast.IndexExpr):
            return self._borrow_base_name(target.obj)
        return None

    def _analyze_lvalue_chain(self, target: ast.Expr) -> None:
        if isinstance(target, ast.Identifier):
            self.infer_expr_type(target)
            return
        if isinstance(target, ast.MemberExpr):
            self._analyze_lvalue_chain(target.obj)
            return
        if isinstance(target, ast.IndexExpr):
            self._analyze_lvalue_chain(target.obj)
            self.infer_expr_type(target.index)
            return
        self.infer_expr_type(target)

    def _expr_contains_reference_value(self, expr: ast.Expr) -> bool:
        if self._expr_is_reference_value(expr):
            return True
        if isinstance(expr, ast.ParenExpr):
            return self._expr_contains_reference_value(expr.expr)
        if isinstance(expr, ast.UnaryExpr):
            return self._expr_contains_reference_value(expr.operand)
        if isinstance(expr, ast.BinaryExpr):
            return self._expr_contains_reference_value(
                expr.left
            ) or self._expr_contains_reference_value(expr.right)
        if isinstance(expr, ast.CallExpr):
            return self._expr_contains_reference_value(expr.func) or any(
                self._expr_contains_reference_value(a) for a in expr.args
            )
        if isinstance(expr, ast.ListExpr):
            return any(self._expr_contains_reference_value(e) for e in expr.elements)
        if isinstance(expr, ast.TupleExpr):
            return any(self._expr_contains_reference_value(e) for e in expr.elements)
        if isinstance(expr, ast.RecordExpr):
            return any(self._expr_contains_reference_value(f.value) for f in expr.fields)
        if isinstance(expr, ast.MemberExpr):
            return self._expr_contains_reference_value(expr.obj)
        if isinstance(expr, ast.IndexExpr):
            return self._expr_contains_reference_value(
                expr.obj
            ) or self._expr_contains_reference_value(expr.index)
        return False

    def _borrow_effective(self, name: str) -> _BorrowState:
        eff = _BorrowState()
        for scope in self._borrow_scopes:
            st = scope.get(name)
            if st is None:
                continue
            if st.mutably_borrowed_by is not None:
                eff.mutably_borrowed_by = st.mutably_borrowed_by
            eff.immutably_borrowed_by |= st.immutably_borrowed_by
        return eff

    def _borrow_acquire(
        self,
        *,
        target: str,
        by: str,
        is_mutable: bool,
        node: ast.Node,
    ) -> None:
        eff = self._borrow_effective(target)
        if is_mutable:
            if eff.mutably_borrowed_by is not None or eff.immutably_borrowed_by:
                self._own_diag(f"Cannot mutably borrow '{target}': already borrowed", node)
                return
            self._borrow_scopes[-1].setdefault(target, _BorrowState()).mutably_borrowed_by = by
            return

        # Shared borrow.
        if eff.mutably_borrowed_by is not None:
            self._own_diag(
                f"Cannot immutably borrow '{target}': it is mutably borrowed",
                node,
            )
            return
        self._borrow_scopes[-1].setdefault(target, _BorrowState()).immutably_borrowed_by.add(by)

    def _own_define(self, name: str, t: Type) -> None:
        move_only = isinstance(t, PointerType) and t.pointer_kind == "own"
        self._own_scopes[-1][name] = _OwnVarState(move_only=move_only)

    def _own_lookup(self, name: str) -> _OwnVarState | None:
        for scope in reversed(self._own_scopes):
            st = scope.get(name)
            if st is not None:
                return st
        return None

    def _own_mark_moved(self, name: str, node: ast.Node | None) -> None:
        st = self._own_lookup(name)
        if st is None:
            return
        if st.move_only and st.moved:
            self._own_diag(f"Use of moved value '{name}'", node)
            return
        if st.move_only:
            st.moved = True

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

    def _validate_trait_bound(self, bound: ast.TypeExpr, *, context: str) -> None:
        """Validate a trait bound type expression (prototype: simple names only)."""
        if not isinstance(bound, ast.SimpleType) or bound.type_args:
            self.error(f"{context} bound must be a trait name", bound)
            return

        parts = bound.name.parts
        if len(parts) == 1:
            name = parts[0]
            sym = self.symbol_table.lookup(name)
            if sym is None or sym.kind != SymbolKind.TRAIT:
                self.error(f"Unknown trait '{name}'", bound)
            return

        if len(parts) == 2:
            namespace, member = parts
            ns_exports = self._namespace_exports.get(namespace)
            if ns_exports is None:
                self.error(f"Unknown trait '{namespace}.{member}'", bound)
                return
            sym = ns_exports.get(member)
            if sym is None or sym.kind != SymbolKind.TRAIT:
                self.error(f"Unknown trait '{namespace}.{member}'", bound)
            return

        self.error(f"{context} bound must be a simple trait name", bound)

    def _trait_bound_ref(self, bound: ast.TypeExpr) -> str | None:
        if not isinstance(bound, ast.SimpleType) or bound.type_args:
            return None
        parts = bound.name.parts
        if len(parts) == 1:
            return parts[0]
        if len(parts) == 2:
            return f"{parts[0]}.{parts[1]}"
        return None

    def _record_decl_type_params(self, node: ast.Node, params: list[ast.TypeParam]) -> None:
        out: dict[str, tuple[str, ...]] = {}
        for tp in params:
            refs: list[str] = []
            for b in tp.bounds:
                r = self._trait_bound_ref(b)
                if r is not None:
                    refs.append(r)
            out[tp.name] = tuple(refs)
        self.decl_type_params[id(node)] = out

    def _substitute_typevars(self, t: Type, subs: dict[str, Type]) -> Type:
        if isinstance(t, TypeVarType):
            return subs.get(t.name, t)
        if isinstance(t, SelfType):
            return subs.get("Self", t)
        if isinstance(t, FunctionType):
            return FunctionType(
                tuple(self._substitute_typevars(p, subs) for p in t.param_types),
                self._substitute_typevars(t.return_type, subs),
            )
        if isinstance(t, ListType):
            return ListType(self._substitute_typevars(t.element_type, subs))
        if isinstance(t, TupleType):
            return TupleType(tuple(self._substitute_typevars(e, subs) for e in t.element_types))
        if isinstance(t, BorrowType):
            return BorrowType(
                self._substitute_typevars(t.inner, subs),
                is_mutable=t.is_mutable,
            )
        if isinstance(t, PointerType):
            return PointerType(t.pointer_kind, self._substitute_typevars(t.inner, subs))
        return t

    def _collect_typevar_bindings(
        self,
        expected: Type,
        actual: Type,
        subs: dict[str, Type],
    ) -> None:
        if isinstance(expected, TypeVarType):
            existing = subs.get(expected.name)
            if existing is None:
                subs[expected.name] = actual
                return
            # Prefer more specific bindings when we first saw `?`.
            if existing.kind == TypeKind.UNKNOWN and actual.kind != TypeKind.UNKNOWN:
                subs[expected.name] = actual
            return
        if isinstance(expected, FunctionType) and isinstance(actual, FunctionType):
            for e, a in zip(expected.param_types, actual.param_types, strict=False):
                self._collect_typevar_bindings(e, a, subs)
            self._collect_typevar_bindings(expected.return_type, actual.return_type, subs)
            return
        if isinstance(expected, ListType) and isinstance(actual, ListType):
            self._collect_typevar_bindings(expected.element_type, actual.element_type, subs)
            return
        if isinstance(expected, TupleType) and isinstance(actual, TupleType):
            for e, a in zip(expected.element_types, actual.element_types, strict=False):
                self._collect_typevar_bindings(e, a, subs)
            return
        if isinstance(expected, BorrowType) and isinstance(actual, BorrowType):
            self._collect_typevar_bindings(expected.inner, actual.inner, subs)
            return
        if isinstance(expected, PointerType) and isinstance(actual, PointerType):
            self._collect_typevar_bindings(expected.inner, actual.inner, subs)
            return

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
        elif isinstance(decl, ast.TraitDecl):
            self.analyze_trait_decl(decl)
        elif isinstance(decl, ast.ImplDecl):
            self.analyze_impl_decl(decl)
        elif isinstance(decl, ast.EffectDecl):
            self.analyze_effect_decl(decl)
        elif isinstance(decl, ast.ExternDecl):
            self.analyze_extern_decl(decl)

    def analyze_extern_decl(self, decl: ast.ExternDecl) -> None:
        """Analyze an extern block: register each function signature."""
        for sig in decl.functions:
            param_types = tuple(
                self.resolve_type_expr(p.type_annotation) if p.type_annotation else UNKNOWN_TYPE
                for p in sig.params
            )
            return_type = self.resolve_type_expr(sig.return_type) if sig.return_type else NIL_TYPE
            symbol = Symbol(
                name=sig.name,
                kind=SymbolKind.FUNCTION,
                type=FunctionType(param_types, return_type),
                declaration_node=sig,
            )
            if not self.symbol_table.define(symbol):
                self.error(f"Function '{sig.name}' is already defined", decl)

    def analyze_effect_decl(self, decl: ast.EffectDecl) -> None:
        """Analyze an effect declaration: registers the effect name."""
        if decl.name in self._declared_effects:
            self.error(f"Effect '{decl.name}' is already declared", decl)
            return
        self._declared_effects.add(decl.name)
        self.symbol_table.define(
            Symbol(
                name=decl.name,
                kind=SymbolKind.EFFECT,
                type=UNKNOWN_TYPE,
                declaration_node=decl,
            )
        )

    def analyze_trait_decl(self, decl: ast.TraitDecl) -> None:
        """Analyze a trait declaration (prototype: signatures only)."""
        if self.symbol_table.lookup(decl.name) is not None:
            self.error(f"Trait '{decl.name}' is already defined", decl)
            return

        self.symbol_table.define(
            Symbol(
                name=decl.name,
                kind=SymbolKind.TRAIT,
                type=UNKNOWN_TYPE,
                declaration_node=decl,
            )
        )

        methods: dict[str, FunctionType] = {}
        self._record_decl_type_params(decl, decl.type_params)
        self._enter_scope(f"trait {decl.name}")
        old_self = self._current_self_type
        self._current_self_type = SelfType()
        try:
            for tp in decl.type_params:
                self.symbol_table.define(
                    Symbol(
                        name=tp.name,
                        kind=SymbolKind.TYPE_PARAM,
                        type=TypeVarType(tp.name),
                        declaration_node=decl,
                    )
                )
                for b in tp.bounds:
                    self._validate_trait_bound(b, context="Type parameter")

            for m in decl.members:
                if m.name in methods:
                    self.error(f"Duplicate trait method '{m.name}'", m)
                    continue
                # Strip implicit 'self' param so call-site arity matches explicit args.
                explicit_params = (
                    m.params[1:] if m.params and m.params[0].name == "self" else m.params
                )
                param_types = tuple(
                    self.resolve_type_expr(p.type_annotation)
                    if p.type_annotation is not None
                    else UNKNOWN_TYPE
                    for p in explicit_params
                )
                ret_t = (
                    self.resolve_type_expr(m.return_type) if m.return_type is not None else NIL_TYPE
                )
                methods[m.name] = FunctionType(param_types=param_types, return_type=ret_t)
        finally:
            self._current_self_type = old_self
            self._exit_scope()

        self._traits[decl.name] = methods

    def analyze_impl_decl(self, decl: ast.ImplDecl) -> None:
        """Analyze an impl declaration (prototype)."""
        if decl.trait is None:
            # Inherent impls are syntax-only for now.
            return

        if not isinstance(decl.trait, ast.SimpleType) or decl.trait.type_args:
            self.error("impl trait must be a trait name", decl.trait)
            return

        trait_name: str | None = None
        trait_full_name: str | None = None
        required: dict[str, FunctionType] | None = None
        parts = decl.trait.name.parts
        if len(parts) == 1:
            trait_name = parts[0]
            trait_full_name = trait_name
            required = self._traits.get(trait_name)
        elif len(parts) == 2:
            ns, member = parts
            trait_name = member
            trait_full_name = f"{ns}.{member}"
            required = self._namespace_traits.get(ns, {}).get(member)
        else:
            self.error("impl trait must be a simple trait name", decl.trait)
            return

        if required is None:
            self.error(f"Unknown trait '{trait_name}'", decl.trait)
            return

        target_type = self.resolve_type_expr(decl.target)

        provided: dict[str, FunctionType] = {}
        old_self = self._current_self_type
        self._current_self_type = target_type
        try:
            for fn in decl.members:
                # Strip implicit 'self' to match the same convention as trait recording.
                explicit_params = (
                    fn.params[1:] if fn.params and fn.params[0].name == "self" else fn.params
                )
                param_types = tuple(
                    self.resolve_type_expr(p.type_annotation)
                    if p.type_annotation is not None
                    else UNKNOWN_TYPE
                    for p in explicit_params
                )
                ret_t = (
                    self.resolve_type_expr(fn.return_type)
                    if fn.return_type is not None
                    else NIL_TYPE
                )
                provided[fn.name] = FunctionType(param_types=param_types, return_type=ret_t)
        finally:
            self._current_self_type = old_self

        # Record the impl for call-site resolution
        if trait_full_name:
            self._impls[(target_type, trait_full_name)] = provided

        for name, req_sig in required.items():
            got = provided.get(name)
            if got is None:
                self.error(
                    f"impl is missing required method '{name}' for trait '{trait_name}'",
                    decl,
                )
                continue
            if len(got.param_types) != len(req_sig.param_types):
                self.error(
                    (
                        f"Method '{name}' has wrong arity: expected {len(req_sig.param_types)}, "
                        f"got {len(got.param_types)}"
                    ),
                    decl,
                )
                continue
            if not self.types_compatible(got.return_type, req_sig.return_type):
                self.error(
                    (
                        f"Method '{name}' has wrong return type: expected {req_sig.return_type}, "
                        f"got {got.return_type}"
                    ),
                    decl,
                )

    def analyze_function_decl(self, decl: ast.FunctionDecl) -> None:
        """Analyze a function declaration."""
        self._record_decl_type_params(decl, decl.type_params)
        # Resolve parameter/return types in a scope that includes type parameters.
        self._enter_scope(f"fn-sig {decl.name}")
        try:
            for tp in decl.type_params:
                self.symbol_table.define(
                    Symbol(
                        name=tp.name,
                        kind=SymbolKind.TYPE_PARAM,
                        type=TypeVarType(tp.name),
                        declaration_node=decl,
                    )
                )
                for b in tp.bounds:
                    self._validate_trait_bound(b, context="Type parameter")

            param_types: list[Type] = []
            for param in decl.params:
                if param.type_annotation:
                    param_type = self.resolve_type_expr(param.type_annotation)
                else:
                    param_type = UNKNOWN_TYPE
                param_types.append(param_type)

            return_type = self.resolve_type_expr(decl.return_type) if decl.return_type else NIL_TYPE
        finally:
            self._exit_scope()

        # Validate declared effects
        for eff_name in decl.effects:
            if eff_name not in self._declared_effects:
                self.error(
                    f"Unknown effect '{eff_name}' — declare it with 'effect {eff_name}'",
                    decl,
                )

        # Create function symbol (with effects)
        type_params = self.decl_type_params.get(id(decl))
        func_type = FunctionType(
            tuple(param_types),
            return_type,
            type_params=type_params,
            effects=tuple(decl.effects),
        )
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
        self._enter_scope(f"fn {decl.name}")
        saved_typevar_bounds = self._current_typevar_bounds
        self._current_typevar_bounds = dict(self.decl_type_params.get(id(decl), {}))
        saved_fn_effects = self._current_fn_effects
        saved_inside_function = self._inside_function
        self._current_fn_effects = tuple(decl.effects)
        self._inside_function = True

        for tp in decl.type_params:
            self.symbol_table.define(
                Symbol(
                    name=tp.name,
                    kind=SymbolKind.TYPE_PARAM,
                    type=TypeVarType(tp.name),
                    declaration_node=decl,
                )
            )
            for b in tp.bounds:
                self._validate_trait_bound(b, context="Type parameter")

        # Define parameters
        for param, param_type in zip(decl.params, param_types, strict=False):
            param_symbol = Symbol(
                name=param.name,
                kind=SymbolKind.PARAMETER,
                type=param_type,
                declaration_node=param,
            )
            self.symbol_table.define(param_symbol)
            if self.ownership_mode != OwnershipMode.OFF:
                self._own_define(param.name, param_type)

        # Analyze function body
        for stmt in decl.body:
            self.analyze_statement(stmt)

        # Exit function scope
        self._exit_scope()
        self._current_typevar_bounds = saved_typevar_bounds
        self._current_fn_effects = saved_fn_effects
        self._inside_function = saved_inside_function

    def analyze_let_decl(self, decl: ast.LetDecl) -> None:
        """Analyze a top-level binding declaration."""
        # Infer type from initializer
        init_type = self.infer_expr_type(decl.initializer)
        if self.ownership_mode != OwnershipMode.OFF and isinstance(
            decl.initializer, ast.Identifier
        ):
            self._own_mark_moved(decl.initializer.name, decl.initializer)

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
        elif self.ownership_mode != OwnershipMode.OFF:
            self._own_define(decl.name, final_type)
            # Escape rule: disallow storing references in module-level bindings for now.
            if isinstance(final_type, BorrowType) or self._expr_contains_reference_value(
                decl.initializer
            ):
                self._own_diag(
                    (
                        "Storing references in module-level bindings is not supported yet "
                        "(reference escape)"
                    ),
                    decl,
                )
            if isinstance(decl.initializer, ast.BorrowExpr):
                base = self._borrow_base_name(decl.initializer.target)
                if base is not None:
                    self._ref_scopes[-1][decl.name] = base
                self._borrow_acquire(
                    target=base or "<unknown>",
                    by=decl.name,
                    is_mutable=decl.initializer.is_mutable,
                    node=decl.initializer,
                )

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
            module_path = self._resolve_module_path(decl.module)
            trait_methods = (
                {} if module_path is None else self._module_trait_cache.get(module_path, {})
            )
            for name in decl.imports:
                if name not in exports:
                    module_label = ".".join(decl.module.parts)
                    self.error(
                        f"Module '{module_label}' has no public export '{name}'",
                        decl,
                    )
                    continue
                self.symbol_table.define(exports[name])
                if exports[name].kind == SymbolKind.TRAIT:
                    # Make imported traits available for bounds/impl validation.
                    self._traits[name] = trait_methods.get(name, {})
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
        module_path = self._resolve_module_path(decl.module)
        if module_path is not None:
            self._namespace_traits[binding_name] = self._module_trait_cache.get(module_path, {})

    def _load_module_exports(self, decl: ast.ImportDecl) -> dict[str, Symbol] | None:
        """Load exported top-level symbols from a sibling .aster module."""
        module_name = ".".join(decl.module.parts)

        # Check native module registry first.
        from aster_lang.native_modules import NATIVE_MODULE_SYMBOLS  # noqa: PLC0415

        if module_name in NATIVE_MODULE_SYMBOLS:
            return NATIVE_MODULE_SYMBOLS[module_name]  # type: ignore[return-value]

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
            self._module_trait_cache[module_path] = self._collect_module_traits(module)
            return exports
        finally:
            self.loading_modules.remove(module_path)

    def _collect_module_traits(self, module: ast.Module) -> dict[str, dict[str, FunctionType]]:
        """Collect method requirements for public traits in a module."""
        out: dict[str, dict[str, FunctionType]] = {}
        for decl in module.declarations:
            if not isinstance(decl, ast.TraitDecl) or not decl.is_public:
                continue
            methods: dict[str, FunctionType] = {}
            self._enter_scope(f"imported-trait {decl.name}")
            try:
                for tp in decl.type_params:
                    self.symbol_table.define(
                        Symbol(
                            name=tp.name,
                            kind=SymbolKind.TYPE_PARAM,
                            type=TypeVarType(tp.name),
                            declaration_node=decl,
                        )
                    )
                for m in decl.members:
                    explicit_params = (
                        m.params[1:] if m.params and m.params[0].name == "self" else m.params
                    )
                    param_types = tuple(
                        self.resolve_type_expr(p.type_annotation)
                        if p.type_annotation is not None
                        else UNKNOWN_TYPE
                        for p in explicit_params
                    )
                    ret_t = (
                        self.resolve_type_expr(m.return_type)
                        if m.return_type is not None
                        else NIL_TYPE
                    )
                    methods[m.name] = FunctionType(param_types=param_types, return_type=ret_t)
            finally:
                self._exit_scope()
            out[decl.name] = methods
        return out

    def _resolve_trait_method(
        self, receiver_t: Type, method_name: str, node: ast.Node | None = None
    ) -> FunctionType | None:
        """Look up a method by name on a receiver type using trait bounds or concrete impls.

        For TypeVarType receivers, searches bounds recorded in _current_typevar_bounds.
        For concrete types, searches recorded impls in _impls.
        If multiple matching traits are found, reports an error (ambiguity) and returns None.
        Returns the FunctionType of the matched method, or None if not found or ambiguous.
        """
        matches: list[tuple[str, FunctionType]] = []

        if isinstance(receiver_t, TypeVarType):
            bounds = self._current_typevar_bounds.get(receiver_t.name, ())
            for bound_ref in bounds:
                parts = bound_ref.split(".", 1)
                if len(parts) == 1:
                    methods = self._traits.get(parts[0], {})
                else:
                    methods = self._namespace_traits.get(parts[0], {}).get(parts[1], {})
                if method_name in methods:
                    matches.append((bound_ref, methods[method_name]))
        else:
            # Check concrete impls
            for (target_t, trait_ref), methods in self._impls.items():
                if self.types_compatible(receiver_t, target_t) and method_name in methods:
                    matches.append((trait_ref, methods[method_name]))

        if not matches:
            return None

        if len(matches) > 1:
            if node is not None:
                trait_names = [m[0] for m in matches]
                self.error(
                    f"Ambiguous method '{method_name}': "
                    f"found in multiple trait bounds {trait_names}",
                    node,
                )
            return None

        # Substitute 'Self' in the matched method signature with the actual receiver type.
        sig = matches[0][1]
        substituted = self._substitute_typevars(sig, {"Self": receiver_t})
        if isinstance(substituted, FunctionType):
            return substituted
        return sig

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
            elif isinstance(decl, ast.TraitDecl):
                if not decl.is_public:
                    continue
                exports[decl.name] = Symbol(
                    name=decl.name,
                    kind=SymbolKind.TRAIT,
                    type=UNKNOWN_TYPE,
                    declaration_node=decl,
                )
            elif isinstance(decl, ast.ExternDecl):
                if not decl.is_public:
                    continue
                for sig in decl.functions:
                    param_types = tuple(
                        self.resolve_type_expr(p.type_annotation)
                        if p.type_annotation is not None
                        else UNKNOWN_TYPE
                        for p in sig.params
                    )
                    return_type = (
                        self.resolve_type_expr(sig.return_type)
                        if sig.return_type is not None
                        else NIL_TYPE
                    )
                    exports[sig.name] = Symbol(
                        name=sig.name,
                        kind=SymbolKind.FUNCTION,
                        type=FunctionType(param_types, return_type),
                        declaration_node=sig,
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
        self._record_decl_type_params(decl, decl.type_params)
        self._enter_scope(f"typealias {decl.name}")
        try:
            for tp in decl.type_params:
                self.symbol_table.define(
                    Symbol(
                        name=tp.name,
                        kind=SymbolKind.TYPE_PARAM,
                        type=TypeVarType(tp.name),
                        declaration_node=decl,
                    )
                )
                for b in tp.bounds:
                    self._validate_trait_bound(b, context="Type parameter")
            resolved_type = self.resolve_type_expr(decl.type_expr)
        finally:
            self._exit_scope()
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
        _init_id = stmt.initializer if isinstance(stmt.initializer, ast.Identifier) else None
        _pre_moved = (
            self.ownership_mode != OwnershipMode.OFF
            and _init_id is not None
            and (lambda st: st is not None and st.move_only and st.moved)(
                self._own_lookup(_init_id.name)
            )
        )
        init_type = self.infer_expr_type(stmt.initializer)
        if self.ownership_mode != OwnershipMode.OFF and _init_id is not None and not _pre_moved:
            self._own_mark_moved(_init_id.name, _init_id)

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
            elif self.ownership_mode != OwnershipMode.OFF:
                self._own_define(stmt.name, final_type)
                if isinstance(stmt.initializer, ast.BorrowExpr):
                    base = self._borrow_base_name(stmt.initializer.target)
                    if base is not None:
                        self._ref_scopes[-1][stmt.name] = base
                    self._borrow_acquire(
                        target=base or "<unknown>",
                        by=stmt.name,
                        is_mutable=stmt.initializer.is_mutable,
                        node=stmt.initializer,
                    )
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

            # Type check
            _val_id = stmt.value if isinstance(stmt.value, ast.Identifier) else None
            _pre_moved_val = (
                self.ownership_mode != OwnershipMode.OFF
                and _val_id is not None
                and (lambda st: st is not None and st.move_only and st.moved)(
                    self._own_lookup(_val_id.name)
                )
            )
            value_type = self.infer_expr_type(stmt.value)
            if (
                self.ownership_mode != OwnershipMode.OFF
                and _val_id is not None
                and not _pre_moved_val
            ):
                self._own_mark_moved(_val_id.name, _val_id)
            if isinstance(symbol.type, BorrowType):
                if not symbol.type.is_mutable:
                    self.error(
                        f"Cannot assign through immutable reference '{stmt.target.name}'",
                        stmt,
                    )
                if not self.types_compatible(value_type, symbol.type.inner):
                    self.error(
                        f"Type mismatch: cannot assign {value_type} to {symbol.type.inner}",
                        stmt,
                    )
                return

            if self.ownership_mode != OwnershipMode.OFF:
                b = self._borrow_effective(stmt.target.name)
                if b.mutably_borrowed_by is not None:
                    self._own_diag(
                        f"Cannot assign to '{stmt.target.name}' while it is mutably borrowed",
                        stmt,
                    )
                if b.immutably_borrowed_by:
                    self._own_diag(
                        f"Cannot assign to '{stmt.target.name}' while it is immutably borrowed",
                        stmt,
                    )

            # Check mutability for value bindings.
            if not symbol.is_mutable:
                self.error(
                    f"Cannot assign to immutable variable '{stmt.target.name}'",
                    stmt,
                )
            if not self.types_compatible(value_type, symbol.type):
                self.error(
                    f"Type mismatch: cannot assign {value_type} to {symbol.type}",
                    stmt,
                )
            return

        # Deref lvalue: *p <- v
        if isinstance(stmt.target, ast.UnaryExpr) and stmt.target.operator == "*":
            if isinstance(stmt.target.operand, ast.Identifier):
                sym = self.symbol_table.lookup(stmt.target.operand.name)
                target_t = UNKNOWN_TYPE if sym is None else sym.type
            else:
                target_t = self.infer_expr_type(stmt.target.operand)
            value_t = self.infer_expr_type(stmt.value)
            if isinstance(target_t, BorrowType):
                if not target_t.is_mutable:
                    self.error("Cannot assign through immutable reference", stmt)
                if not self.types_compatible(value_t, target_t.inner):
                    self.error(
                        f"Type mismatch: cannot assign {value_t} to {target_t.inner}",
                        stmt,
                    )
                return
            if isinstance(target_t, PointerType):
                # Pointers are not fully implemented yet; allow type-checking for now.
                if not self.types_compatible(value_t, target_t.inner):
                    self.error(
                        f"Type mismatch: cannot assign {value_t} to {target_t.inner}",
                        stmt,
                    )
                return
            self.error("Invalid assignment target", stmt)
            return

        # Member/index lvalues: supported for identifier-rooted chains.
        if isinstance(stmt.target, ast.MemberExpr):
            base_name = self._borrow_base_name(stmt.target)
            if base_name is not None:
                base = self.symbol_table.lookup(base_name)
                if base is None:
                    self.error(f"Undefined variable '{base_name}'", stmt)
                    return
                if not base.is_mutable:
                    self.error(
                        f"Cannot assign through immutable variable '{base_name}'",
                        stmt,
                    )
            self._analyze_lvalue_chain(stmt.target)
            self.infer_expr_type(stmt.value)
            return

        if isinstance(stmt.target, ast.IndexExpr):
            base_name = self._borrow_base_name(stmt.target)
            if base_name is not None:
                base = self.symbol_table.lookup(base_name)
                if base is None:
                    self.error(f"Undefined variable '{base_name}'", stmt)
                    return
                if not base.is_mutable:
                    self.error(
                        f"Cannot assign through immutable variable '{base_name}'",
                        stmt,
                    )
            self._analyze_lvalue_chain(stmt.target)
            self.infer_expr_type(stmt.value)
            return

        self.error("Invalid assignment target", stmt)

    def analyze_return_stmt(self, stmt: ast.ReturnStmt) -> None:
        """Analyze a return statement."""
        if stmt.value:
            _ret_id = stmt.value if isinstance(stmt.value, ast.Identifier) else None
            _pre_moved_ret = (
                self.ownership_mode != OwnershipMode.OFF
                and _ret_id is not None
                and (lambda st: st is not None and st.move_only and st.moved)(
                    self._own_lookup(_ret_id.name)
                )
            )
            self.infer_expr_type(stmt.value)
            if (
                self.ownership_mode != OwnershipMode.OFF
                and _ret_id is not None
                and not _pre_moved_ret
            ):
                self._own_mark_moved(_ret_id.name, _ret_id)

            if self.ownership_mode != OwnershipMode.OFF:
                # Escape rules (prototype):
                # - returning a borrow of a local variable is disallowed
                # - returning aggregates containing references is disallowed
                if self._expr_contains_reference_value(stmt.value) and isinstance(
                    stmt.value, ast.ListExpr | ast.TupleExpr | ast.RecordExpr
                ):
                    self._own_diag(
                        "Cannot return aggregates containing references (reference escape)",
                        stmt.value,
                    )
                elif isinstance(stmt.value, ast.BorrowExpr):
                    base = self._borrow_base_name(stmt.value.target)
                    if base is None:
                        self._own_diag(
                            "Cannot return a reference to a non-lvalue in this prototype",
                            stmt.value,
                        )
                        return
                    target_sym = self.symbol_table.lookup(base)
                    if (
                        target_sym is not None
                        and target_sym.kind != SymbolKind.PARAMETER
                        and not self._is_global_symbol(target_sym)
                    ):
                        self._own_diag(
                            f"Cannot return a reference to local '{base}'",
                            stmt.value,
                        )
                elif isinstance(stmt.value, ast.Identifier):
                    sym = self.symbol_table.lookup(stmt.value.name)
                    if sym is not None and isinstance(sym.type, BorrowType):
                        # Returning a borrow parameter is allowed.
                        if sym.kind == SymbolKind.PARAMETER:
                            return
                        origin = self._ref_origin(stmt.value.name)
                        if origin is None:
                            self._own_diag(
                                "Cannot return a reference value of unknown origin",
                                stmt.value,
                            )
                            return
                        origin_sym = self.symbol_table.lookup(origin)
                        if origin_sym is None:
                            return
                        if origin_sym.kind == SymbolKind.PARAMETER or self._is_global_symbol(
                            origin_sym
                        ):
                            return
                        self._own_diag(
                            f"Cannot return a reference to local '{origin}'",
                            stmt.value,
                        )
        # TODO: Check return type against function signature

    def analyze_if_stmt(self, stmt: ast.IfStmt) -> None:
        """Analyze an if statement."""
        # Check condition type
        cond_type = self.infer_expr_type(stmt.condition)
        if self.strict_types and cond_type.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR):
            self.error("If condition must be Bool (unknown in strict mode)", stmt)
        if not self.types_compatible(cond_type, BOOL_TYPE):
            self.error(f"If condition must be Bool, got {cond_type}", stmt)

        # Analyze blocks
        self._enter_scope("<then>")
        for s in stmt.then_block:
            self.analyze_statement(s)
        self._exit_scope()

        if stmt.else_block:
            self._enter_scope("<else>")
            for s in stmt.else_block:
                self.analyze_statement(s)
            self._exit_scope()

    def analyze_while_stmt(self, stmt: ast.WhileStmt) -> None:
        """Analyze a while statement."""
        # Check condition type
        cond_type = self.infer_expr_type(stmt.condition)
        if self.strict_types and cond_type.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR):
            self.error("While condition must be Bool (unknown in strict mode)", stmt)
        if not self.types_compatible(cond_type, BOOL_TYPE):
            self.error(f"While condition must be Bool, got {cond_type}", stmt)

        # Analyze body
        self._enter_scope("<while>")
        for s in stmt.body:
            self.analyze_statement(s)
        self._exit_scope()

    def analyze_for_stmt(self, stmt: ast.ForStmt) -> None:
        """Analyze a for statement."""
        # TODO: Infer element type from iterable
        self.infer_expr_type(stmt.iterable)

        # Enter loop scope and define loop variable
        self._enter_scope("<for>")
        loop_var = Symbol(
            name=stmt.variable,
            kind=SymbolKind.VARIABLE,
            type=UNKNOWN_TYPE,  # TODO: Infer from iterable
            declaration_node=stmt,
        )
        self.symbol_table.define(loop_var)
        if self.ownership_mode != OwnershipMode.OFF:
            self._own_define(stmt.variable, UNKNOWN_TYPE)

        # Analyze body
        for s in stmt.body:
            self.analyze_statement(s)

        self._exit_scope()

    def analyze_match_stmt(self, stmt: ast.MatchStmt) -> None:
        """Analyze a match statement."""
        subject_type = self.infer_expr_type(stmt.subject)
        for arm in stmt.arms:
            self._enter_scope("<match-arm>")
            self._analyze_pattern(arm.pattern, subject_type, stmt.subject, stmt)
            for s in arm.body:
                self.analyze_statement(s)
            self._exit_scope()

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
            if self.ownership_mode != OwnershipMode.OFF:
                self._own_define(pattern.name, subject_type)
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
            if self.ownership_mode != OwnershipMode.OFF:
                st = self._own_lookup(expr.name)
                if st is not None and st.move_only and st.moved:
                    self._own_diag(f"Use of moved value '{expr.name}'", expr)
                # Borrow enforcement (prototype): if a value binding is mutably borrowed, it
                # cannot be used directly until the borrow ends. If it is immutably borrowed,
                # it cannot be assigned to (enforced in analyze_assign_stmt).
                if not isinstance(symbol.type, BorrowType):
                    b = self._borrow_effective(expr.name)
                    if b.mutably_borrowed_by is not None:
                        self._own_diag(
                            f"Cannot use '{expr.name}' while it is mutably borrowed",
                            expr,
                        )
            # Implicit deref model: a binding typed as `&T` behaves like `T` in expression typing.
            if isinstance(symbol.type, BorrowType):
                return remember(symbol.type.inner)
            return remember(symbol.type)
        elif isinstance(expr, ast.BorrowExpr):
            base = self._borrow_base_name(expr.target)
            if base is None:
                if self.ownership_mode != OwnershipMode.OFF and not isinstance(
                    expr.target, ast.MemberExpr | ast.IndexExpr
                ):
                    self._own_diag(
                        (
                            "Borrow targets must be identifiers, member accesses, or index "
                            "lvalues in this prototype"
                        ),
                        expr,
                    )
                self.infer_expr_type(expr.target)
                inner: Type
                if isinstance(expr.target, ast.MemberExpr | ast.IndexExpr):
                    inner = INT_TYPE
                else:
                    inner = UNKNOWN_TYPE
                return remember(BorrowType(inner, is_mutable=expr.is_mutable))

            sym = self.symbol_table.lookup(base)
            if sym is None:
                self.error(f"Undefined variable '{base}'", expr)
                return remember(ERROR_TYPE)
            if self.ownership_mode != OwnershipMode.OFF and expr.is_mutable and not sym.is_mutable:
                self._own_diag(
                    f"Cannot take &mut of immutable variable '{base}'",
                    expr,
                )
            # Member/index types are not inferred yet; assume Int so common borrow patterns stay
            # usable, including computed roots like `&mut {x: 1}.x`.
            inner = sym.type if isinstance(expr.target, ast.Identifier) else INT_TYPE
            return remember(BorrowType(inner, is_mutable=expr.is_mutable))
        elif isinstance(expr, ast.BinaryExpr):
            return remember(self.infer_binary_expr_type(expr))
        elif isinstance(expr, ast.UnaryExpr):
            return remember(self.infer_unary_expr_type(expr))
        elif isinstance(expr, ast.CallExpr):
            return remember(self.infer_call_expr_type(expr))
        elif isinstance(expr, ast.LambdaExpr):
            param_types: list[Type] = []
            self._enter_scope("<lambda>")
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
                    if self.ownership_mode != OwnershipMode.OFF:
                        self._own_define(p.name, pt)

                ret_t: Type
                if isinstance(expr.body, list):
                    for stmt in expr.body:
                        self.analyze_statement(stmt)
                    # Block lambdas default to Nil when they don't explicitly return.
                    # If they do return, infer a best-effort return type from the body.
                    ret_t = self._infer_return_type_from_stmts(expr.body)
                else:
                    ret_t = self.infer_expr_type(expr.body)
            finally:
                self._exit_scope()
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
            if self.ownership_mode != OwnershipMode.OFF:
                for e in expr.elements:
                    if self._expr_is_reference_value(e):
                        self._own_diag(
                            (
                                "References in collection literals are not supported yet "
                                "(reference escape)"
                            ),
                            e,
                        )
            for elem in expr.elements:
                self.infer_expr_type(elem)
            return remember(ListType(UNKNOWN_TYPE))
        elif isinstance(expr, ast.TupleExpr):
            if self.ownership_mode != OwnershipMode.OFF:
                for e in expr.elements:
                    if self._expr_is_reference_value(e):
                        self._own_diag(
                            (
                                "References in collection literals are not supported yet "
                                "(reference escape)"
                            ),
                            e,
                        )
            elem_types = tuple(self.infer_expr_type(e) for e in expr.elements)
            return remember(TupleType(elem_types))
        elif isinstance(expr, ast.RecordExpr):
            if self.ownership_mode != OwnershipMode.OFF:
                for f in expr.fields:
                    if self._expr_is_reference_value(f.value):
                        self._own_diag(
                            (
                                "References in collection literals are not supported yet "
                                "(reference escape)"
                            ),
                            f.value,
                        )
            for f in expr.fields:
                self.infer_expr_type(f.value)
            return remember(UNKNOWN_TYPE)
        elif isinstance(expr, ast.ParenExpr):
            return remember(self.infer_expr_type(expr.expr))
        else:
            return remember(UNKNOWN_TYPE)

    def _infer_return_type_from_stmts(self, stmts: list[ast.Stmt]) -> Type:
        """Best-effort return type inference for block lambdas.

        We collect the types of any `return` statements we can see structurally, without attempting
        to prove control-flow coverage. This keeps higher-order code usable without requiring full
        function-level return type checking infrastructure.
        """

        collected: list[Type] = []

        def walk(block: list[ast.Stmt]) -> None:
            for s in block:
                if isinstance(s, ast.ReturnStmt):
                    if s.value is None:
                        collected.append(NIL_TYPE)
                    else:
                        collected.append(self.infer_expr_type(s.value))
                elif isinstance(s, ast.IfStmt):
                    walk(s.then_block)
                    if s.else_block:
                        walk(s.else_block)
                elif isinstance(s, ast.MatchStmt):
                    for arm in s.arms:
                        walk(arm.body)
                elif isinstance(s, ast.WhileStmt | ast.ForStmt):
                    walk(s.body)

        walk(stmts)

        if not collected:
            return NIL_TYPE

        # Unify: prefer a concrete type over Unknown when possible.
        unified = collected[0]
        for t in collected[1:]:
            if unified == UNKNOWN_TYPE and t != UNKNOWN_TYPE:
                unified = t
                continue
            if t == UNKNOWN_TYPE:
                continue
            if not self.types_compatible(unified, t) and not self.types_compatible(t, unified):
                self.error(f"Inconsistent return types in lambda: {unified} vs {t}", stmts[0])
                return UNKNOWN_TYPE

        return unified

    def infer_binary_expr_type(self, expr: ast.BinaryExpr) -> Type:
        """Infer type of binary expression."""
        left_type = self.infer_expr_type(expr.left)
        right_type = self.infer_expr_type(expr.right)

        def is_integral(t: Type) -> bool:
            # Keep semantics permissive during prototyping: Unknown/typevars should not block
            # arithmetic in higher-order/lambda-heavy code.
            return t.kind in (TypeKind.INT, TypeKind.BITS, TypeKind.UNKNOWN, TypeKind.TYPEVAR)

        def int_width(t: Type) -> int | None:
            if isinstance(t, BitsType):
                return t.bits
            return None

        def widen_integral(a: Type, b: Type) -> Type:
            if a.kind == TypeKind.INT or b.kind == TypeKind.INT:
                return INT_TYPE
            assert isinstance(a, BitsType) and isinstance(b, BitsType)
            width = max(a.bits, b.bits)
            if width == 4:
                return NIBBLE_TYPE
            if width == 8:
                return BYTE_TYPE
            if width == 16:
                return WORD_TYPE
            if width == 32:
                return DWORD_TYPE
            return QWORD_TYPE

        # Arithmetic operators
        if expr.operator in ("+", "-", "*", "/", "%"):
            # String concatenation: String + String -> String
            #
            # The interpreter and VM both support string concatenation, so semantic analysis
            # should accept it as well (and report mixed String/Int uses as errors).
            if expr.operator == "+" and (left_type == STRING_TYPE or right_type == STRING_TYPE):
                if not self.types_compatible(left_type, STRING_TYPE):
                    self.error(f"String + requires String, got {left_type}", expr)
                if not self.types_compatible(right_type, STRING_TYPE):
                    self.error(f"String + requires String, got {right_type}", expr)
                return STRING_TYPE

            if left_type.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR):
                if self.strict_types:
                    self.error(
                        f"Cannot use unknown type on left side of '{expr.operator}' in strict mode",
                        expr,
                    )
                return INT_TYPE
            if right_type.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR):
                if self.strict_types:
                    self.error(
                        f"Cannot use unknown type on right side of '{expr.operator}' "
                        "in strict mode",
                        expr,
                    )
                return INT_TYPE
            if not is_integral(left_type):
                self.error(f"Arithmetic requires an integer, got {left_type}", expr)
                return INT_TYPE
            if not is_integral(right_type):
                self.error(f"Arithmetic requires an integer, got {right_type}", expr)
                return INT_TYPE
            return widen_integral(left_type, right_type)

        # Bitwise operators
        if expr.operator in ("&", "|", "^", "<<", ">>"):
            if left_type.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR):
                if self.strict_types:
                    self.error(
                        f"Cannot use unknown type on left side of '{expr.operator}' in strict mode",
                        expr,
                    )
                return INT_TYPE
            if right_type.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR):
                if self.strict_types:
                    self.error(
                        f"Cannot use unknown type on right side of '{expr.operator}' "
                        "in strict mode",
                        expr,
                    )
                return INT_TYPE
            if not is_integral(left_type):
                self.error(f"Bitwise operator requires an integer, got {left_type}", expr)
                return INT_TYPE
            if not is_integral(right_type):
                self.error(f"Bitwise operator requires an integer, got {right_type}", expr)
                return INT_TYPE

            # Shifts preserve the left type when it is fixed-width; otherwise Int.
            if expr.operator in ("<<", ">>"):
                return left_type if left_type.kind == TypeKind.BITS else INT_TYPE

            return widen_integral(left_type, right_type)

        # Comparison operators
        elif expr.operator in ("==", "!=", "<", "<=", ">", ">="):
            if self.strict_types and (
                left_type.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR)
                or right_type.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR)
            ):
                self.error(
                    f"Cannot compare unknown types in strict mode ({left_type} vs {right_type})",
                    expr,
                )
            if not self.types_compatible(left_type, right_type):
                self.error(
                    f"Cannot compare {left_type} with {right_type}",
                    expr,
                )
            return BOOL_TYPE

        # Logical operators
        elif expr.operator in ("and", "or"):
            if self.strict_types and (
                left_type.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR)
                or right_type.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR)
            ):
                self.error("Logical operators require Bool (unknown in strict mode)", expr)
            if not self.types_compatible(left_type, BOOL_TYPE):
                self.error(f"Logical operator requires Bool, got {left_type}", expr)
            if not self.types_compatible(right_type, BOOL_TYPE):
                self.error(f"Logical operator requires Bool, got {right_type}", expr)
            return BOOL_TYPE

        return UNKNOWN_TYPE

    def infer_unary_expr_type(self, expr: ast.UnaryExpr) -> Type:
        """Infer type of unary expression."""
        if expr.operator == "*":
            operand_t: Type
            if isinstance(expr.operand, ast.Identifier):
                sym = self.symbol_table.lookup(expr.operand.name)
                operand_t = UNKNOWN_TYPE if sym is None else sym.type
            else:
                operand_t = self.infer_expr_type(expr.operand)

            if operand_t.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR):
                return UNKNOWN_TYPE
            if isinstance(operand_t, BorrowType):
                return operand_t.inner
            if isinstance(operand_t, PointerType):
                return operand_t.inner
            self.error(f"Deref requires a reference/pointer, got {operand_t}", expr)
            return UNKNOWN_TYPE

        operand_type = self.infer_expr_type(expr.operand)

        if expr.operator == "-":
            if operand_type.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR):
                if self.strict_types:
                    self.error("Cannot negate unknown type in strict mode", expr)
                return INT_TYPE
            if operand_type.kind != TypeKind.INT:
                self.error(f"Negation requires Int, got {operand_type}", expr)
            return INT_TYPE
        elif expr.operator == "not":
            if not self.types_compatible(operand_type, BOOL_TYPE):
                self.error(f"Logical not requires Bool, got {operand_type}", expr)
            return BOOL_TYPE
        elif expr.operator == "~":
            if operand_type.kind in (TypeKind.UNKNOWN, TypeKind.TYPEVAR):
                if self.strict_types:
                    self.error("Cannot apply '~' to unknown type in strict mode", expr)
                return INT_TYPE
            if operand_type.kind not in (TypeKind.INT, TypeKind.BITS):
                self.error(f"Bitwise not requires an integer, got {operand_type}", expr)
                return INT_TYPE
            return operand_type

        return UNKNOWN_TYPE

    def _check_effect_propagation(
        self, callee_effects: tuple[str, ...], node: ast.Node | None
    ) -> None:
        """Ensure all effects of a callee are declared by the current function."""
        if not self._inside_function or not callee_effects:
            return
        for eff in callee_effects:
            if eff not in self._current_fn_effects:
                self.error(
                    f"Effect '{eff}' is not declared on this function — "
                    f"add '!{eff}' to the function signature",
                    node,
                )

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
            poly_arity = {"range", "assert"}  # 1 or 2 args
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
            subs: dict[str, Type] = {}
            arg_types: list[Type] = []
            for arg in expr.args:
                arg_types.append(self.infer_expr_type(arg))

            for param_t, arg_t in zip(func_type.param_types, arg_types, strict=False):
                self._collect_typevar_bindings(param_t, arg_t, subs)

            for i, (arg_t, param_t) in enumerate(
                zip(arg_types, func_type.param_types, strict=False)
            ):
                inst_param = self._substitute_typevars(param_t, subs)
                if not self.types_compatible(arg_t, inst_param):
                    if expr.func.name in {"ord", "ascii_bytes", "unicode_bytes"}:
                        self.error(f"{expr.func.name}() expects String", expr)
                    else:
                        self.error(
                            f"Argument {i+1} type mismatch: expected {inst_param}, got {arg_t}",
                            expr,
                        )

            # Validate trait bounds on inferred type parameters
            for tp_name, bounds in func_type.type_params.items():
                if tp_name in subs:
                    inferred_t = subs[tp_name]
                    for bound_ref in bounds:
                        # Check if inferred_t implements bound_ref
                        found = False
                        for (target_t, impl_trait_ref), _methods in self._impls.items():
                            if impl_trait_ref == bound_ref and self.types_compatible(
                                inferred_t, target_t
                            ):
                                found = True
                                break
                        if not found:
                            self.error(
                                f"Type '{inferred_t}' does not implement trait '{bound_ref}' "
                                f"required by type parameter '{tp_name}'",
                                expr,
                            )

            if self.ownership_mode != OwnershipMode.OFF:
                mut_borrows: set[str] = set()
                shared_borrows: set[str] = set()
                moved_args: set[str] = set()
                for inst_param, arg_expr in zip(
                    (self._substitute_typevars(p, subs) for p in func_type.param_types),
                    expr.args,
                    strict=False,
                ):
                    if isinstance(inst_param, BorrowType):
                        arg_name: str | None = None
                        if isinstance(arg_expr, ast.Identifier):
                            arg_name = arg_expr.name
                        elif isinstance(arg_expr, ast.BorrowExpr):
                            arg_name = self._borrow_base_name(arg_expr.target)
                        if arg_name is None:
                            self._own_diag(
                                "Borrow arguments must be identifiers in this prototype",
                                arg_expr,
                            )
                            continue
                        sym = self.symbol_table.lookup(arg_name)
                        if inst_param.is_mutable and (sym is None or not sym.is_mutable):
                            self._own_diag(
                                f"Cannot take &mut of immutable variable '{arg_name}'",
                                arg_expr,
                            )
                        if inst_param.is_mutable:
                            if arg_name in mut_borrows or arg_name in shared_borrows:
                                self._own_diag(
                                    f"Conflicting borrows of '{arg_name}' in the same call",
                                    arg_expr,
                                )
                            mut_borrows.add(arg_name)
                        else:
                            if arg_name in mut_borrows:
                                self._own_diag(
                                    f"Conflicting borrows of '{arg_name}' in the same call",
                                    arg_expr,
                                )
                            shared_borrows.add(arg_name)
                        continue

                    if isinstance(inst_param, PointerType) and inst_param.pointer_kind == "own":
                        if not isinstance(arg_expr, ast.Identifier):
                            self._own_diag(
                                (
                                    "Passing *own values requires an identifier argument in this "
                                    "prototype"
                                ),
                                arg_expr,
                            )
                            continue
                        arg_name = arg_expr.name
                        if arg_name in moved_args:
                            self._own_diag(
                                f"Value '{arg_name}' moved more than once in the same call",
                                arg_expr,
                            )
                            continue
                        moved_args.add(arg_name)
                        # infer_expr_type already flagged use-after-move; just update state.
                        st2 = self._own_lookup(arg_name)
                        if st2 is not None and st2.move_only and not st2.moved:
                            st2.moved = True

            self._check_effect_propagation(func_type.effects, expr)
            return self._substitute_typevars(func_type.return_type, subs)
        elif isinstance(expr.func, ast.MemberExpr):
            # Trait call-site resolution prototype: x.method(args) where x has a bounded type var.
            receiver_t = self.infer_expr_type(expr.func.obj)
            method_name = expr.func.member
            method_sig = self._resolve_trait_method(receiver_t, method_name, node=expr)
            for arg in expr.args:
                self.infer_expr_type(arg)
            if method_sig is None:
                # Unknown method — fall through silently (UNKNOWN_TYPE) unless receiver is a
                # known type-var with explicit bounds, in which case it is an error.
                if (
                    isinstance(receiver_t, TypeVarType)
                    and receiver_t.name in self._current_typevar_bounds
                ):
                    bounds = self._current_typevar_bounds[receiver_t.name]
                    if bounds:
                        self.error(
                            f"No method '{method_name}' found in trait bounds "
                            f"{list(bounds)} of type parameter '{receiver_t.name}'",
                            expr,
                        )
                return UNKNOWN_TYPE
            # Validate argument count (self is implicit — not in args)
            # Trait method signatures include 'self' as first param when declared with `self`.
            # The call site provides only the explicit args (receiver is the object).
            expected_arity = len(method_sig.param_types)
            actual_arity = len(expr.args)
            if expected_arity != actual_arity:
                self.error(
                    f"Method '{method_name}' expects {expected_arity} argument(s), "
                    f"got {actual_arity}",
                    expr,
                )
            self._check_effect_propagation(method_sig.effects, expr)
            return method_sig.return_type
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

            subs2: dict[str, Type] = {}
            arg_types2: list[Type] = [self.infer_expr_type(a) for a in expr.args]
            for param_t, arg_t in zip(callee_t.param_types, arg_types2, strict=False):
                self._collect_typevar_bindings(param_t, arg_t, subs2)

            for i, (arg_t, param_t) in enumerate(
                zip(arg_types2, callee_t.param_types, strict=False)
            ):
                inst_param = self._substitute_typevars(param_t, subs2)
                if not self.types_compatible(arg_t, inst_param):
                    self.error(
                        f"Argument {i+1} type mismatch: expected {inst_param}, got {arg_t}",
                        expr,
                    )

            self._check_effect_propagation(callee_t.effects, expr)
            return self._substitute_typevars(callee_t.return_type, subs2)

    # Type utilities

    def resolve_type_expr(self, type_expr: ast.TypeExpr) -> Type:
        """Resolve a type expression to a Type."""
        if isinstance(type_expr, ast.SimpleType):
            parts = type_expr.name.parts
            if len(parts) == 1:
                name = parts[0]
                type_map = {
                    "Int": INT_TYPE,
                    "Nibble": NIBBLE_TYPE,
                    "Byte": BYTE_TYPE,
                    "Word": WORD_TYPE,
                    "DWord": DWORD_TYPE,
                    "QWord": QWORD_TYPE,
                    "String": STRING_TYPE,
                    "Bool": BOOL_TYPE,
                    "Nil": NIL_TYPE,
                    "Float": FloatType(),
                }
                if name in type_map:
                    return type_map[name]
                symbol = self.symbol_table.lookup(name)
                if symbol is not None and symbol.kind == SymbolKind.TYPE_PARAM:
                    return symbol.type
                if symbol is not None and symbol.kind == SymbolKind.TYPE_ALIAS:
                    if not type_expr.type_args:
                        return symbol.type
                    decl = symbol.declaration_node
                    if not isinstance(decl, ast.TypeAliasDecl):
                        return symbol.type
                    if not decl.type_params:
                        return symbol.type
                    if len(type_expr.type_args) != len(decl.type_params):
                        self.error(
                            (
                                f"Type alias '{name}' expects {len(decl.type_params)} type "
                                f"argument(s), got {len(type_expr.type_args)}"
                            ),
                            type_expr,
                        )
                        return symbol.type
                    subs = {
                        tp.name: self.resolve_type_expr(arg)
                        for tp, arg in zip(decl.type_params, type_expr.type_args, strict=False)
                    }
                    return self._substitute_typevars(symbol.type, subs)
                return UNKNOWN_TYPE
            if len(parts) == 2:
                namespace, member = parts
                ns_exports = self._namespace_exports.get(namespace)
                if ns_exports is not None:
                    sym = ns_exports.get(member)
                    if sym is not None and sym.kind == SymbolKind.TYPE_ALIAS:
                        if not type_expr.type_args:
                            return sym.type
                        decl = sym.declaration_node
                        if not isinstance(decl, ast.TypeAliasDecl):
                            return sym.type
                        if not decl.type_params:
                            return sym.type
                        if len(type_expr.type_args) != len(decl.type_params):
                            self.error(
                                (
                                    f"Type alias '{namespace}.{member}' expects "
                                    f"{len(decl.type_params)} type argument(s), got "
                                    f"{len(type_expr.type_args)}"
                                ),
                                type_expr,
                            )
                            return sym.type
                        subs = {
                            tp.name: self.resolve_type_expr(arg)
                            for tp, arg in zip(decl.type_params, type_expr.type_args, strict=False)
                        }
                        return self._substitute_typevars(sym.type, subs)
            return UNKNOWN_TYPE
        elif isinstance(type_expr, ast.FunctionType):
            param_types = tuple(self.resolve_type_expr(pt) for pt in type_expr.param_types)
            return_type = self.resolve_type_expr(type_expr.return_type)
            return FunctionType(param_types, return_type)
        elif isinstance(type_expr, ast.BorrowTypeExpr):
            if self.ownership_mode == OwnershipMode.WARN and not self._warned_borrow_surface:
                self.warn(
                    (
                        "Ownership checking is enabled (experimental). Borrow types "
                        "(&T, &mut T) are allowed."
                    ),
                    type_expr,
                )
                self._warned_borrow_surface = True
            inner = self.resolve_type_expr(type_expr.inner)
            return BorrowType(inner, is_mutable=type_expr.is_mutable)
        elif isinstance(type_expr, ast.PointerTypeExpr):
            if self.ownership_mode == OwnershipMode.WARN and not self._warned_pointer_surface:
                self.warn(
                    (
                        "Ownership checking is enabled (experimental). Pointer types "
                        "(*own/*shared/*weak/*raw) are allowed."
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
            elif (
                self.ownership_mode == OwnershipMode.WARN
                and type_expr.pointer_kind == "raw"
                and not self._warned_raw_pointer
            ):
                self.warn(
                    "Raw pointers (*raw T) are unsafe; no safety checks are implemented yet.",
                    type_expr,
                )
                self._warned_raw_pointer = True
            return PointerType(type_expr.pointer_kind, inner)
        elif isinstance(type_expr, ast.SelfType):
            if self._current_self_type is not None:
                return self._current_self_type
            self.error("'Self' type used outside of trait or implementation", type_expr)
            return ERROR_TYPE
        return UNKNOWN_TYPE

    def types_compatible(self, actual: Type, expected: Type) -> bool:
        """Check if actual type is compatible with expected type."""
        # Handle error and unknown types
        if actual.kind == TypeKind.ERROR or expected.kind == TypeKind.ERROR:
            return True  # Error recovery
        if actual.kind == TypeKind.UNKNOWN or expected.kind == TypeKind.UNKNOWN:
            return True  # Allow unknown types during inference

        # Self placeholder is compatible with anything during trait/impl validation.
        if isinstance(actual, SelfType) or isinstance(expected, SelfType):
            return True

        # Type variables are only compatible with themselves in this prototype.
        if isinstance(actual, TypeVarType) or isinstance(expected, TypeVarType):
            return actual == expected

        # Borrow compatibility:
        # - allow passing `&T` to `&T` (mutability must not be weakened)
        # - allow passing `T` to `&T` (implicit borrow)
        # - allow passing `&T` to `T` (implicit deref)
        if isinstance(actual, BorrowType) and isinstance(expected, BorrowType):
            if expected.is_mutable and not actual.is_mutable:
                return False
            return self.types_compatible(actual.inner, expected.inner)
        if isinstance(expected, BorrowType):
            a = actual.inner if isinstance(actual, BorrowType) else actual
            return self.types_compatible(a, expected.inner)
        if isinstance(actual, BorrowType):
            return self.types_compatible(actual.inner, expected)

        # Implicit borrow passing: allow `T` where `&T` is expected (and the checker enforces
        # mutability/aliasing rules separately for `&mut`).
        # NOTE: handled above, kept for historical context.

        # Integral widenings (prototype): allow Int <-> fixed-width integers, and allow narrowing
        # only when the expected width is >= the actual width.
        if isinstance(actual, BitsType) and expected.kind == TypeKind.INT:
            return True
        if actual.kind == TypeKind.INT and isinstance(expected, BitsType):
            return True
        if isinstance(actual, BitsType) and isinstance(expected, BitsType):
            return actual.bits <= expected.bits

        # Exact match
        return actual == expected


def analyze_module(module: ast.Module) -> tuple[SemanticAnalyzer, list[SemanticError]]:
    """Analyze a module and return the analyzer and any errors."""
    analyzer = SemanticAnalyzer()
    analyzer.analyze(module)
    return analyzer, analyzer.errors
