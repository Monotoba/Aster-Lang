from __future__ import annotations

from dataclasses import dataclass, field

# Base classes


@dataclass(slots=True)
class Node:
    """Base class for all AST nodes."""

    # Source line span: (start_line, end_line), 1-based.  Set by the parser.
    span: tuple[int, int] | None = field(default=None, kw_only=True)
    # Comments attached during the comment-attachment pass.
    leading_comments: list[str] = field(default_factory=list, kw_only=True)
    trailing_comment: str | None = field(default=None, kw_only=True)


@dataclass(slots=True)
class Decl(Node):
    """Base class for top-level declarations."""

    pass


@dataclass(slots=True)
class Stmt(Node):
    """Base class for statements."""

    pass


@dataclass(slots=True)
class Expr(Node):
    """Base class for expressions."""

    pass


@dataclass(slots=True)
class TypeExpr(Node):
    """Base class for type expressions."""

    pass


# Module


@dataclass(slots=True)
class Module(Node):
    """A module containing top-level declarations."""

    declarations: list[Decl] = field(default_factory=list)


# Declarations


@dataclass(slots=True)
class FunctionDecl(Decl):
    """Function declaration: fn name(params) -> Type: body"""

    name: str
    type_params: list[TypeParam]
    params: list[ParamDecl]
    return_type: TypeExpr | None
    body: list[Stmt]
    is_public: bool = False


@dataclass(slots=True)
class ParamDecl(Node):
    """Parameter declaration: name: Type"""

    name: str
    type_annotation: TypeExpr | None = None


@dataclass(slots=True)
class TypeAliasDecl(Decl):
    """Type alias declaration: typealias Name = Type"""

    name: str
    type_params: list[TypeParam]
    type_expr: TypeExpr
    is_public: bool = False


@dataclass(slots=True)
class TypeParam(Node):
    """Type parameter: T or T: Bound + Bound2"""

    name: str
    bounds: list[TypeExpr] = field(default_factory=list)


@dataclass(slots=True)
class ImportDecl(Decl):
    """Import declaration: use module or use module: name1, name2"""

    module: QualifiedName
    imports: list[str] | None = None  # None means import all
    alias: str | None = None


@dataclass(slots=True)
class LetDecl(Decl):
    """Top-level binding declaration: pub? mut? name: Type := expr"""

    name: str
    type_annotation: TypeExpr | None
    initializer: Expr
    is_mutable: bool = False
    is_public: bool = False


@dataclass(slots=True)
class FunctionSig(Node):
    """Function signature (no body): fn name(params) -> Type?"""

    name: str
    params: list[ParamDecl]
    return_type: TypeExpr | None


@dataclass(slots=True)
class TraitDecl(Decl):
    """Trait declaration: trait Name[T]? : members"""

    name: str
    type_params: list[TypeParam]
    members: list[FunctionSig]
    is_public: bool = False


@dataclass(slots=True)
class ImplDecl(Decl):
    """Impl declaration.

    - Inherent impl: impl Type: members
    - Trait impl: impl Trait for Type: members
    """

    target: TypeExpr
    trait: TypeExpr | None
    members: list[FunctionDecl]


# Patterns (used in match arms)


@dataclass(slots=True)
class Pattern(Node):
    """Base class for match patterns."""

    pass


@dataclass(slots=True)
class WildcardPattern(Pattern):
    """Wildcard pattern: _"""

    pass


@dataclass(slots=True)
class LiteralPattern(Pattern):
    """Literal pattern: 0, "hello", true, nil"""

    literal: IntegerLiteral | StringLiteral | BoolLiteral | NilLiteral


@dataclass(slots=True)
class BindingPattern(Pattern):
    """Binding pattern: name — captures matched value into a variable."""

    name: str


@dataclass(slots=True)
class OrPattern(Pattern):
    """Or-pattern: p1 | p2 | ..."""

    alternatives: list[Pattern]


@dataclass(slots=True)
class RestPattern(Pattern):
    """Rest pattern: *name"""

    name: str


@dataclass(slots=True)
class TuplePattern(Pattern):
    """Tuple pattern: (p1, p2, ...)"""

    elements: list[Pattern]


@dataclass(slots=True)
class ListPattern(Pattern):
    """List pattern: [p1, p2, ...]"""

    elements: list[Pattern]


@dataclass(slots=True)
class RecordPatternField(Node):
    """Record pattern field: name or name: pattern"""

    name: str
    pattern: Pattern


@dataclass(slots=True)
class RecordPattern(Pattern):
    """Record pattern: {field1: p1, field2}"""

    fields: list[RecordPatternField]


# Match


@dataclass(slots=True)
class MatchArm(Node):
    """A single arm in a match statement: pattern: body"""

    pattern: Pattern
    body: list[Stmt]


@dataclass(slots=True)
class MatchStmt(Stmt):
    """Match statement: match expr: arms"""

    subject: Expr
    arms: list[MatchArm]


# Statements


@dataclass(slots=True)
class LetStmt(Stmt):
    """Binding statement: mut? name: Type := expr"""

    pattern: Pattern
    type_annotation: TypeExpr | None
    initializer: Expr
    is_mutable: bool = False

    @property
    def name(self) -> str:
        """Return the bound name for simple identifier bindings."""
        if isinstance(self.pattern, BindingPattern):
            return self.pattern.name
        raise AttributeError("Destructuring binding statement has no single name")


@dataclass(slots=True)
class AssignStmt(Stmt):
    """Assignment statement: target <- value"""

    target: Expr
    value: Expr


@dataclass(slots=True)
class ReturnStmt(Stmt):
    """Return statement: return expr?"""

    value: Expr | None = None


@dataclass(slots=True)
class IfStmt(Stmt):
    """If statement: if condition: then_block else: else_block"""

    condition: Expr
    then_block: list[Stmt]
    else_block: list[Stmt] | None = None


@dataclass(slots=True)
class WhileStmt(Stmt):
    """While statement: while condition: body"""

    condition: Expr
    body: list[Stmt]


@dataclass(slots=True)
class ForStmt(Stmt):
    """For statement: for var in iterable: body"""

    variable: str
    iterable: Expr
    body: list[Stmt]


@dataclass(slots=True)
class BreakStmt(Stmt):
    """Break statement: break"""

    pass


@dataclass(slots=True)
class ContinueStmt(Stmt):
    """Continue statement: continue"""

    pass


@dataclass(slots=True)
class ExprStmt(Stmt):
    """Expression statement: expr"""

    expr: Expr


# Expressions


@dataclass(slots=True)
class BinaryExpr(Expr):
    """Binary expression: left op right"""

    left: Expr
    operator: str
    right: Expr


@dataclass(slots=True)
class UnaryExpr(Expr):
    """Unary expression: op operand"""

    operator: str
    operand: Expr


@dataclass(slots=True)
class BorrowExpr(Expr):
    """Borrow expression: &x or &mut x (expression-level borrowing)."""

    target: Expr
    is_mutable: bool = False


@dataclass(slots=True)
class CallExpr(Expr):
    """Function call: func(args)"""

    func: Expr
    args: list[Expr]


@dataclass(slots=True)
class IndexExpr(Expr):
    """Index expression: obj[index]"""

    obj: Expr
    index: Expr


@dataclass(slots=True)
class MemberExpr(Expr):
    """Member access: obj.member"""

    obj: Expr
    member: str


@dataclass(slots=True)
class TupleExpr(Expr):
    """Tuple expression: (a, b, c)"""

    elements: list[Expr]


@dataclass(slots=True)
class ListExpr(Expr):
    """List expression: [a, b, c]"""

    elements: list[Expr]


@dataclass(slots=True)
class RecordExpr(Expr):
    """Record expression: {field1: value1, field2: value2}"""

    fields: list[RecordField]


@dataclass(slots=True)
class RecordField(Node):
    """Record field: name: value"""

    name: str
    value: Expr


@dataclass(slots=True)
class LambdaExpr(Expr):
    """Lambda expression: (params) -> expr or (params) -> : body"""

    params: list[LambdaParam]
    body: Expr | list[Stmt]  # Single expr or block of statements


@dataclass(slots=True)
class LambdaParam(Node):
    """Lambda parameter: name: Type?"""

    name: str
    type_annotation: TypeExpr | None = None


@dataclass(slots=True)
class ParenExpr(Expr):
    """Parenthesized expression: (expr)"""

    expr: Expr


# Literals


@dataclass(slots=True)
class IntegerLiteral(Expr):
    """Integer literal: 123"""

    value: int


@dataclass(slots=True)
class StringLiteral(Expr):
    """String literal: "hello" """

    value: str


@dataclass(slots=True)
class BoolLiteral(Expr):
    """Boolean literal: true or false"""

    value: bool


@dataclass(slots=True)
class NilLiteral(Expr):
    """Nil literal: nil"""

    pass


@dataclass(slots=True)
class Identifier(Expr):
    """Identifier: name"""

    name: str


@dataclass(slots=True)
class QualifiedName(Expr):
    """Qualified name: module.submodule.name"""

    parts: list[str]

    @property
    def name(self) -> str:
        """Get the simple name (last part)."""
        return self.parts[-1] if self.parts else ""

    def __str__(self) -> str:
        return ".".join(self.parts)


# Type Expressions


@dataclass(slots=True)
class SimpleType(TypeExpr):
    """Simple type: Name or Name[T1, T2]"""

    name: QualifiedName
    type_args: list[TypeExpr] = field(default_factory=list)


@dataclass(slots=True)
class FunctionType(TypeExpr):
    """Function type: Fn(T1, T2) -> T3"""

    param_types: list[TypeExpr]
    return_type: TypeExpr


@dataclass(slots=True)
class BorrowTypeExpr(TypeExpr):
    """Borrowed reference type: &T or &mut T"""

    inner: TypeExpr
    is_mutable: bool = False


@dataclass(slots=True)
class PointerTypeExpr(TypeExpr):
    """Smart/raw pointer type: *own T, *shared T, *weak T, *raw T"""

    pointer_kind: str
    inner: TypeExpr


@dataclass(slots=True)
class SelfType(TypeExpr):
    """Self type: Self (inside traits/impls)"""

    pass
