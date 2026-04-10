from __future__ import annotations

from aster_lang import ast
from aster_lang.lexer import Lexer, Token, TokenKind


class ParseError(Exception):
    """Parse error with location information."""

    def __init__(self, message: str, token: Token) -> None:
        super().__init__(f"{message} at line {token.start.line}, column {token.start.column}")
        self.token = token


class Parser:
    """Recursive descent parser with Pratt parsing for expressions."""

    def __init__(self, source: str) -> None:
        self.lexer = Lexer(source)
        self.current = self.lexer.next_token()
        self.previous: Token | None = None

    # Token management

    def peek(self) -> TokenKind:
        """Get the kind of the current token."""
        return self.current.kind

    def check(self, *kinds: TokenKind) -> bool:
        """Check if current token matches any of the given kinds."""
        return self.current.kind in kinds

    def advance(self) -> Token:
        """Consume and return the current token."""
        self.previous = self.current
        self.current = self.lexer.next_token()
        return self.previous

    def expect(self, kind: TokenKind, message: str | None = None) -> Token:
        """Consume a token of the expected kind or raise an error."""
        if not self.check(kind):
            if message is None:
                message = f"Expected {kind.name}, got {self.current.kind.name}"
            raise ParseError(message, self.current)
        return self.advance()

    def match(self, *kinds: TokenKind) -> bool:
        """If current token matches any kind, consume it and return True."""
        if self.check(*kinds):
            self.advance()
            return True
        return False

    def skip_newlines(self) -> None:
        """Skip any newline tokens."""
        while self.match(TokenKind.NEWLINE):
            pass

    # Module and declarations

    def parse_module(self) -> ast.Module:
        """Parse a module: declarations*"""
        declarations = []
        self.skip_newlines()

        while not self.check(TokenKind.EOF):
            decl = self.parse_top_level_item()
            declarations.append(decl)
            self.skip_newlines()

        return ast.Module(declarations=declarations)

    def parse_top_level_item(self) -> ast.Decl:
        """Parse a top-level declaration."""
        is_public = self.match(TokenKind.PUB)

        if self.check(TokenKind.FN):
            return self.parse_function_decl(is_public)
        elif self.check(TokenKind.TYPEALIAS):
            return self.parse_type_alias_decl(is_public)
        elif self.check(TokenKind.USE):
            return self.parse_import_decl()
        elif self.check(TokenKind.MUT, TokenKind.IDENTIFIER):
            # Top-level let declaration
            is_mutable = self.match(TokenKind.MUT)
            if not self.check(TokenKind.IDENTIFIER):
                raise ParseError("Expected identifier", self.current)
            name_token = self.advance()
            name = name_token.text

            type_annotation = None
            if self.match(TokenKind.COLON):
                type_annotation = self.parse_type_expr()

            self.expect(TokenKind.BIND, "Expected ':=' in let declaration")
            initializer = self.parse_expression()
            self.skip_newlines()

            return ast.LetDecl(
                name=name,
                type_annotation=type_annotation,
                initializer=initializer,
                is_mutable=is_mutable,
            )
        else:
            raise ParseError(f"Expected declaration, got {self.current.kind.name}", self.current)

    def parse_function_decl(self, is_public: bool = False) -> ast.FunctionDecl:
        """Parse function declaration: fn name(params) -> Type: body"""
        self.expect(TokenKind.FN)
        name_token = self.expect(TokenKind.IDENTIFIER)
        name = name_token.text

        # Parameters
        self.expect(TokenKind.LPAREN)
        params = []
        if not self.check(TokenKind.RPAREN):
            params = self.parse_param_list()
        self.expect(TokenKind.RPAREN)

        # Return type
        return_type = None
        if self.match(TokenKind.ARROW):
            return_type = self.parse_type_expr()

        # Body
        self.expect(TokenKind.COLON)
        body = self.parse_block()

        return ast.FunctionDecl(
            name=name,
            params=params,
            return_type=return_type,
            body=body,
            is_public=is_public,
        )

    def parse_param_list(self) -> list[ast.ParamDecl]:
        """Parse parameter list: param, param, ..."""
        params = []
        while True:
            name_token = self.expect(TokenKind.IDENTIFIER)
            name = name_token.text

            type_annotation = None
            if self.match(TokenKind.COLON):
                type_annotation = self.parse_type_expr()

            params.append(ast.ParamDecl(name=name, type_annotation=type_annotation))

            if not self.match(TokenKind.COMMA):
                break
            # Allow trailing comma
            if self.check(TokenKind.RPAREN):
                break

        return params

    def parse_type_alias_decl(self, is_public: bool = False) -> ast.TypeAliasDecl:
        """Parse type alias: typealias Name[T1, T2] = Type"""
        self.expect(TokenKind.TYPEALIAS)
        name_token = self.expect(TokenKind.IDENTIFIER)
        name = name_token.text

        # Type parameters
        type_params = []
        if self.match(TokenKind.LBRACKET):
            while not self.check(TokenKind.RBRACKET):
                param_token = self.expect(TokenKind.IDENTIFIER)
                type_params.append(param_token.text)
                if not self.match(TokenKind.COMMA):
                    break
            self.expect(TokenKind.RBRACKET)

        self.expect(TokenKind.EQUALS, "Expected '=' in type alias")
        type_expr = self.parse_type_expr()
        self.skip_newlines()

        return ast.TypeAliasDecl(
            name=name,
            type_params=type_params,
            type_expr=type_expr,
            is_public=is_public,
        )

    def parse_import_decl(self) -> ast.ImportDecl:
        """Parse import: use module or use module: name1, name2 or use module as alias"""
        self.expect(TokenKind.USE)
        module = self.parse_qualified_name()

        imports = None
        alias = None

        if self.match(TokenKind.COLON):
            # Import specific names
            imports = []
            while True:
                name_token = self.expect(TokenKind.IDENTIFIER)
                imports.append(name_token.text)
                if not self.match(TokenKind.COMMA):
                    break
        elif self.match(TokenKind.AS):
            # Import with alias
            alias_token = self.expect(TokenKind.IDENTIFIER)
            alias = alias_token.text

        self.skip_newlines()

        return ast.ImportDecl(module=module, imports=imports, alias=alias)

    # Type expressions

    def parse_type_expr(self) -> ast.TypeExpr:
        """Parse a type expression."""
        # Function type: Fn(T1, T2) -> T3
        if self.check(TokenKind.FN):
            self.advance()
            self.expect(TokenKind.LPAREN)

            param_types = []
            if not self.check(TokenKind.RPAREN):
                while True:
                    param_types.append(self.parse_type_expr())
                    if not self.match(TokenKind.COMMA):
                        break

            self.expect(TokenKind.RPAREN)
            self.expect(TokenKind.ARROW)
            return_type = self.parse_type_expr()

            return ast.FunctionType(param_types=param_types, return_type=return_type)

        # Simple type: Name or Name[T1, T2]
        name = self.parse_qualified_name()

        type_args = []
        if self.match(TokenKind.LBRACKET):
            while not self.check(TokenKind.RBRACKET):
                type_args.append(self.parse_type_expr())
                if not self.match(TokenKind.COMMA):
                    break
            self.expect(TokenKind.RBRACKET)

        return ast.SimpleType(name=name, type_args=type_args)

    def parse_qualified_name(self) -> ast.QualifiedName:
        """Parse a qualified name: a.b.c"""
        parts = []
        parts.append(self.expect(TokenKind.IDENTIFIER).text)

        while self.match(TokenKind.DOT):
            parts.append(self.expect(TokenKind.IDENTIFIER).text)

        return ast.QualifiedName(parts=parts)

    # Statements

    def parse_block(self) -> list[ast.Stmt]:
        """Parse a block: NEWLINE INDENT statements DEDENT"""
        self.expect(TokenKind.NEWLINE)
        self.expect(TokenKind.INDENT)

        statements = []
        while not self.check(TokenKind.DEDENT, TokenKind.EOF):
            stmt = self.parse_statement()
            statements.append(stmt)
            self.skip_newlines()

        self.expect(TokenKind.DEDENT)
        return statements

    def parse_statement(self) -> ast.Stmt:
        """Parse a statement."""
        # Let statement: mut? name: Type := expr
        if self.check(TokenKind.MUT, TokenKind.IDENTIFIER):
            # Could be let statement or assignment - need to look ahead
            if self.check(TokenKind.MUT):
                # Definitely a let statement
                is_mutable = True
                self.advance()
                name_token = self.expect(TokenKind.IDENTIFIER)
                name = name_token.text

                type_annotation = None
                if self.match(TokenKind.COLON):
                    type_annotation = self.parse_type_expr()

                self.expect(TokenKind.BIND)
                initializer = self.parse_expression()
                self.skip_newlines()

                return ast.LetStmt(
                    name=name,
                    type_annotation=type_annotation,
                    initializer=initializer,
                    is_mutable=is_mutable,
                )
            else:
                # Could be let or assignment - parse as expression statement first
                # and check for := or <-
                expr = self.parse_expression()

                if self.check(TokenKind.BIND):
                    # It's a let statement
                    if not isinstance(expr, ast.Identifier):
                        raise ParseError("Expected identifier in let statement", self.current)
                    self.advance()  # consume :=
                    initializer = self.parse_expression()
                    self.skip_newlines()

                    return ast.LetStmt(
                        name=expr.name,
                        type_annotation=None,
                        initializer=initializer,
                        is_mutable=False,
                    )
                elif self.check(TokenKind.ASSIGN):
                    # It's an assignment statement
                    self.advance()  # consume <-
                    assign_value = self.parse_expression()
                    self.skip_newlines()

                    return ast.AssignStmt(target=expr, value=assign_value)
                else:
                    # It's an expression statement
                    self.skip_newlines()
                    return ast.ExprStmt(expr=expr)

        # Return statement
        if self.match(TokenKind.RETURN):
            value: ast.Expr | None = None
            if not self.check(TokenKind.NEWLINE, TokenKind.DEDENT, TokenKind.EOF):
                value = self.parse_expression()
            self.skip_newlines()
            return ast.ReturnStmt(value=value)

        # If statement
        if self.match(TokenKind.IF):
            condition = self.parse_expression()
            self.expect(TokenKind.COLON)
            then_block = self.parse_block()

            else_block = None
            if self.match(TokenKind.ELSE):
                self.expect(TokenKind.COLON)
                else_block = self.parse_block()

            return ast.IfStmt(condition=condition, then_block=then_block, else_block=else_block)

        # While statement
        if self.match(TokenKind.WHILE):
            condition = self.parse_expression()
            self.expect(TokenKind.COLON)
            body = self.parse_block()
            return ast.WhileStmt(condition=condition, body=body)

        # For statement
        if self.match(TokenKind.FOR):
            var_token = self.expect(TokenKind.IDENTIFIER)
            variable = var_token.text
            self.expect(TokenKind.IN)
            iterable = self.parse_expression()
            self.expect(TokenKind.COLON)
            body = self.parse_block()
            return ast.ForStmt(variable=variable, iterable=iterable, body=body)

        # Break statement
        if self.match(TokenKind.BREAK):
            self.skip_newlines()
            return ast.BreakStmt()

        # Continue statement
        if self.match(TokenKind.CONTINUE):
            self.skip_newlines()
            return ast.ContinueStmt()

        # Expression statement (includes assignments)
        expr = self.parse_expression()

        # Check for assignment
        if self.check(TokenKind.ASSIGN):
            self.advance()
            value = self.parse_expression()
            self.skip_newlines()
            return ast.AssignStmt(target=expr, value=value)

        self.skip_newlines()
        return ast.ExprStmt(expr=expr)

    # Expressions (Pratt parsing)

    def parse_expression(self, precedence: int = 0) -> ast.Expr:
        """Parse an expression with Pratt parsing."""
        left = self.parse_primary()

        while True:
            token_precedence = self.get_precedence(self.current.kind)
            if token_precedence < precedence:
                break

            if self.check_binary_op():
                operator = self.advance().text
                right = self.parse_expression(token_precedence + 1)
                left = ast.BinaryExpr(left=left, operator=operator, right=right)

            elif self.check(TokenKind.LPAREN):
                # Function call
                self.advance()
                args = []
                if not self.check(TokenKind.RPAREN):
                    while True:
                        args.append(self.parse_expression())
                        if not self.match(TokenKind.COMMA):
                            break
                        if self.check(TokenKind.RPAREN):  # Trailing comma
                            break
                self.expect(TokenKind.RPAREN)
                left = ast.CallExpr(func=left, args=args)

            elif self.check(TokenKind.LBRACKET):
                # Index
                self.advance()
                index = self.parse_expression()
                self.expect(TokenKind.RBRACKET)
                left = ast.IndexExpr(obj=left, index=index)

            elif self.check(TokenKind.DOT):
                # Member access
                self.advance()
                member_token = self.expect(TokenKind.IDENTIFIER)
                left = ast.MemberExpr(obj=left, member=member_token.text)

            else:
                break

        return left

    def parse_primary(self) -> ast.Expr:
        """Parse a primary expression."""
        # Unary operators
        if self.check(TokenKind.MINUS, TokenKind.NOT):
            operator = self.advance().text
            operand = self.parse_expression(70)  # High precedence for unary
            return ast.UnaryExpr(operator=operator, operand=operand)

        # Literals
        if self.match(TokenKind.INTEGER):
            assert self.previous is not None
            return ast.IntegerLiteral(value=int(self.previous.text))

        if self.match(TokenKind.STRING):
            assert self.previous is not None
            return ast.StringLiteral(value=self.previous.text)

        if self.match(TokenKind.TRUE):
            return ast.BoolLiteral(value=True)

        if self.match(TokenKind.FALSE):
            return ast.BoolLiteral(value=False)

        if self.match(TokenKind.NIL):
            return ast.NilLiteral()

        # Identifier (qualified names only used in type contexts)
        if self.check(TokenKind.IDENTIFIER):
            name_token = self.advance()
            return ast.Identifier(name=name_token.text)

        # Parenthesized expression or tuple
        if self.match(TokenKind.LPAREN):
            # Empty tuple or parenthesized expression
            if self.check(TokenKind.RPAREN):
                self.advance()
                return ast.TupleExpr(elements=[])

            first = self.parse_expression()

            # Check for tuple
            if self.match(TokenKind.COMMA):
                elements = [first]
                if not self.check(TokenKind.RPAREN):
                    while True:
                        elements.append(self.parse_expression())
                        if not self.match(TokenKind.COMMA):
                            break
                        if self.check(TokenKind.RPAREN):  # Trailing comma
                            break
                self.expect(TokenKind.RPAREN)
                return ast.TupleExpr(elements=elements)

            # Just a parenthesized expression
            self.expect(TokenKind.RPAREN)
            return ast.ParenExpr(expr=first)

        # List
        if self.match(TokenKind.LBRACKET):
            elements = []
            if not self.check(TokenKind.RBRACKET):
                while True:
                    elements.append(self.parse_expression())
                    if not self.match(TokenKind.COMMA):
                        break
                    if self.check(TokenKind.RBRACKET):  # Trailing comma
                        break
            self.expect(TokenKind.RBRACKET)
            return ast.ListExpr(elements=elements)

        # Record
        if self.match(TokenKind.LBRACE):
            fields = []
            if not self.check(TokenKind.RBRACE):
                while True:
                    name_token = self.expect(TokenKind.IDENTIFIER)
                    self.expect(TokenKind.COLON)
                    value = self.parse_expression()
                    fields.append(ast.RecordField(name=name_token.text, value=value))
                    if not self.match(TokenKind.COMMA):
                        break
                    if self.check(TokenKind.RBRACE):  # Trailing comma
                        break
            self.expect(TokenKind.RBRACE)
            return ast.RecordExpr(fields=fields)

        raise ParseError(f"Unexpected token in expression: {self.current.kind.name}", self.current)

    def check_binary_op(self) -> bool:
        """Check if current token is a binary operator."""
        return self.check(
            TokenKind.OR,
            TokenKind.AND,
            TokenKind.EQ,
            TokenKind.NE,
            TokenKind.LT,
            TokenKind.LE,
            TokenKind.GT,
            TokenKind.GE,
            TokenKind.PLUS,
            TokenKind.MINUS,
            TokenKind.STAR,
            TokenKind.SLASH,
            TokenKind.PERCENT,
        )

    def get_precedence(self, kind: TokenKind) -> int:
        """Get the precedence of an operator."""
        # Postfix operators (call, index, member)
        if kind in (TokenKind.LPAREN, TokenKind.LBRACKET, TokenKind.DOT):
            return 90

        # Multiplicative
        if kind in (TokenKind.STAR, TokenKind.SLASH, TokenKind.PERCENT):
            return 60

        # Additive
        if kind in (TokenKind.PLUS, TokenKind.MINUS):
            return 50

        # Comparison
        if kind in (TokenKind.LT, TokenKind.LE, TokenKind.GT, TokenKind.GE):
            return 40

        # Equality
        if kind in (TokenKind.EQ, TokenKind.NE):
            return 30

        # Logical AND
        if kind == TokenKind.AND:
            return 20

        # Logical OR
        if kind == TokenKind.OR:
            return 10

        return 0


def parse_module(source: str) -> ast.Module:
    """Parse source code into an AST Module."""
    parser = Parser(source)
    return parser.parse_module()
