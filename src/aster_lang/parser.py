from __future__ import annotations

from aster_lang import ast
from aster_lang.lexer import Lexer, LexerState, Token, TokenKind


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

    def snapshot(self) -> tuple[Token, Token | None, LexerState]:
        """Capture parser state for backtracking."""
        return (self.current, self.previous, self.lexer.snapshot())

    def restore(self, state: tuple[Token, Token | None, LexerState]) -> None:
        """Restore parser state from a snapshot."""
        self.current = state[0]
        self.previous = state[1]
        self.lexer.restore(state[2])

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
            # Top-level binding declaration
            is_mutable = self.match(TokenKind.MUT)
            if not self.check(TokenKind.IDENTIFIER):
                raise ParseError("Expected identifier", self.current)
            name_token = self.advance()
            name = name_token.text

            type_annotation = None
            if self.match(TokenKind.COLON):
                type_annotation = self.parse_type_expr()

            self.expect(TokenKind.BIND, "Expected ':=' in binding declaration")
            initializer = self.parse_expression()
            self.skip_newlines()

            return ast.LetDecl(
                name=name,
                type_annotation=type_annotation,
                initializer=initializer,
                is_mutable=is_mutable,
                is_public=is_public,
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
        # Borrowed references: &T, &mut T
        if self.match(TokenKind.AMP):
            is_mut = self.match(TokenKind.MUT)
            inner = self.parse_type_expr()
            return ast.BorrowTypeExpr(inner=inner, is_mutable=is_mut)

        # Pointer types: *own T, *shared T, *weak T, *raw T
        if self.match(TokenKind.STAR):
            kind_tok = self.expect(TokenKind.IDENTIFIER)
            inner = self.parse_type_expr()
            return ast.PointerTypeExpr(pointer_kind=kind_tok.text, inner=inner)

        # Function type: Fn(T1, T2) -> T3
        # Parseable as either the identifier "Fn" (preferred) or legacy "fn" keyword.
        if self.check(TokenKind.IDENTIFIER) and self.current.text == "Fn":
            self.advance()
            self.expect(TokenKind.LPAREN)
            param_types: list[ast.TypeExpr] = []
            if not self.check(TokenKind.RPAREN):
                while True:
                    param_types.append(self.parse_type_expr())
                    if not self.match(TokenKind.COMMA):
                        break
            self.expect(TokenKind.RPAREN)
            self.expect(TokenKind.ARROW)
            return_type = self.parse_type_expr()
            return ast.FunctionType(param_types=param_types, return_type=return_type)

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
        # Binding statement: mut? name: Type := expr
        if self.check(
            TokenKind.MUT,
            TokenKind.IDENTIFIER,
            TokenKind.LPAREN,
            TokenKind.LBRACKET,
            TokenKind.LBRACE,
        ):
            # Could be a binding statement or assignment - need to look ahead
            if self.check(TokenKind.MUT):
                # Definitely a binding statement
                is_mutable = True
                self.advance()
                pattern = self.parse_binding_pattern()

                type_annotation = None
                if isinstance(pattern, ast.BindingPattern) and self.match(TokenKind.COLON):
                    type_annotation = self.parse_type_expr()

                self.expect(TokenKind.BIND)
                initializer = self.parse_expression()
                self.skip_newlines()

                return ast.LetStmt(
                    pattern=pattern,
                    type_annotation=type_annotation,
                    initializer=initializer,
                    is_mutable=is_mutable,
                )
            else:
                # Could be a binding or assignment - parse as expression statement first
                # and check for := or <-
                state = self.snapshot()
                try:
                    pattern = self.parse_binding_pattern()
                except ParseError:
                    self.restore(state)
                    pattern = None

                if pattern is not None and self.check(TokenKind.BIND):
                    self.advance()  # consume :=
                    initializer = self.parse_expression()
                    self.skip_newlines()

                    return ast.LetStmt(
                        pattern=pattern,
                        type_annotation=None,
                        initializer=initializer,
                        is_mutable=False,
                    )
                self.restore(state)
                expr = self.parse_expression()

                if self.check(TokenKind.ASSIGN):
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

        # Match statement
        if self.check(TokenKind.MATCH):
            return self.parse_match_stmt()

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

    def parse_match_stmt(self) -> ast.MatchStmt:
        """Parse: match expr: NEWLINE INDENT arm+ DEDENT"""
        self.expect(TokenKind.MATCH)
        subject = self.parse_expression()
        self.expect(TokenKind.COLON)
        self.skip_newlines()
        self.expect(TokenKind.INDENT)

        arms: list[ast.MatchArm] = []
        while not self.check(TokenKind.DEDENT, TokenKind.EOF):
            self.skip_newlines()
            if self.check(TokenKind.DEDENT, TokenKind.EOF):
                break
            arms.append(self.parse_match_arm())

        self.expect(TokenKind.DEDENT)
        return ast.MatchStmt(subject=subject, arms=arms)

    def parse_match_arm(self) -> ast.MatchArm:
        """Parse a single match arm: pattern: (expr | block)"""
        pattern = self.parse_pattern()
        self.expect(TokenKind.COLON)

        # Block arm: pattern: NEWLINE INDENT stmts DEDENT
        if self.check(TokenKind.NEWLINE, TokenKind.INDENT):
            body = self.parse_block()
            return ast.MatchArm(pattern=pattern, body=body)

        # Inline arm: pattern: stmt NEWLINE
        stmt = self.parse_statement()
        return ast.MatchArm(pattern=pattern, body=[stmt])

    def parse_pattern(self) -> ast.Pattern:
        """Parse a match pattern."""
        pattern = self.parse_pattern_atom()
        alternatives = [pattern]
        while self.match(TokenKind.PIPE):
            alternatives.append(self.parse_pattern_atom())
        if len(alternatives) == 1:
            return pattern
        return ast.OrPattern(alternatives=alternatives)

    def parse_pattern_atom(self) -> ast.Pattern:
        """Parse a non-or pattern atom."""
        if self.match(TokenKind.STAR):
            name_token = self.expect(
                TokenKind.IDENTIFIER,
                "Expected identifier after '*' in rest pattern",
            )
            return ast.RestPattern(name=name_token.text)
        if self.match(TokenKind.LPAREN):
            elements = [self.parse_pattern()]
            self.expect(TokenKind.COMMA, "Expected ',' in tuple pattern")
            while not self.check(TokenKind.RPAREN):
                elements.append(self.parse_pattern())
                if not self.match(TokenKind.COMMA):
                    break
            self.expect(TokenKind.RPAREN)
            return ast.TuplePattern(elements=elements)
        if self.match(TokenKind.LBRACKET):
            elements = [self.parse_pattern()]
            self.expect(TokenKind.COMMA, "Expected ',' in list pattern")
            while not self.check(TokenKind.RBRACKET):
                elements.append(self.parse_pattern())
                if not self.match(TokenKind.COMMA):
                    break
            self.expect(TokenKind.RBRACKET)
            return ast.ListPattern(elements=elements)
        if self.match(TokenKind.LBRACE):
            fields = []
            if not self.check(TokenKind.RBRACE):
                while True:
                    name_token = self.expect(TokenKind.IDENTIFIER)
                    pattern: ast.Pattern
                    if self.match(TokenKind.COLON):
                        pattern = self.parse_pattern()
                    else:
                        pattern = ast.BindingPattern(name=name_token.text)
                    fields.append(ast.RecordPatternField(name=name_token.text, pattern=pattern))
                    if not self.match(TokenKind.COMMA):
                        break
            self.expect(TokenKind.RBRACE)
            return ast.RecordPattern(fields=fields)

        # Wildcard
        if self.check(TokenKind.IDENTIFIER) and self.current.text == "_":
            self.advance()
            return ast.WildcardPattern()

        # Negative integer literal: -N
        if self.check(TokenKind.MINUS):
            self.advance()
            tok = self.expect(TokenKind.INTEGER)
            return ast.LiteralPattern(literal=ast.IntegerLiteral(value=-int(tok.text)))

        # Literal patterns
        if self.check(TokenKind.INTEGER):
            tok = self.advance()
            return ast.LiteralPattern(literal=ast.IntegerLiteral(value=int(tok.text)))
        if self.check(TokenKind.STRING):
            tok = self.advance()
            return ast.LiteralPattern(literal=ast.StringLiteral(value=tok.text))
        if self.check(TokenKind.TRUE):
            self.advance()
            return ast.LiteralPattern(literal=ast.BoolLiteral(value=True))
        if self.check(TokenKind.FALSE):
            self.advance()
            return ast.LiteralPattern(literal=ast.BoolLiteral(value=False))
        if self.check(TokenKind.NIL):
            self.advance()
            return ast.LiteralPattern(literal=ast.NilLiteral())

        # Binding pattern: any identifier
        if self.check(TokenKind.IDENTIFIER):
            tok = self.advance()
            return ast.BindingPattern(name=tok.text)

        raise ParseError(f"Expected pattern, got {self.current.kind.name}", self.current)

    def parse_binding_pattern(self) -> ast.Pattern:
        """Parse a binding-only pattern for local bindings."""
        if self.match(TokenKind.STAR):
            name_token = self.expect(
                TokenKind.IDENTIFIER,
                "Expected identifier after '*' in rest binding pattern",
            )
            return ast.RestPattern(name=name_token.text)
        if self.match(TokenKind.LPAREN):
            elements = [self.parse_binding_pattern()]
            self.expect(TokenKind.COMMA, "Expected ',' in tuple binding pattern")
            while not self.check(TokenKind.RPAREN):
                elements.append(self.parse_binding_pattern())
                if not self.match(TokenKind.COMMA):
                    break
            self.expect(TokenKind.RPAREN)
            return ast.TuplePattern(elements=elements)
        if self.match(TokenKind.LBRACKET):
            elements = [self.parse_binding_pattern()]
            self.expect(TokenKind.COMMA, "Expected ',' in list binding pattern")
            while not self.check(TokenKind.RBRACKET):
                elements.append(self.parse_binding_pattern())
                if not self.match(TokenKind.COMMA):
                    break
            self.expect(TokenKind.RBRACKET)
            return ast.ListPattern(elements=elements)
        if self.match(TokenKind.LBRACE):
            fields = []
            if not self.check(TokenKind.RBRACE):
                while True:
                    name_token = self.expect(TokenKind.IDENTIFIER)
                    if self.match(TokenKind.COLON):
                        field_pattern = self.parse_binding_pattern()
                    else:
                        field_pattern = ast.BindingPattern(name=name_token.text)
                    fields.append(
                        ast.RecordPatternField(name=name_token.text, pattern=field_pattern)
                    )
                    if not self.match(TokenKind.COMMA):
                        break
            self.expect(TokenKind.RBRACE)
            return ast.RecordPattern(fields=fields)
        if self.check(TokenKind.IDENTIFIER) and self.current.text == "_":
            self.advance()
            return ast.WildcardPattern()
        if self.check(TokenKind.IDENTIFIER):
            tok = self.advance()
            return ast.BindingPattern(name=tok.text)
        raise ParseError(
            f"Expected binding pattern, got {self.current.kind.name}",
            self.current,
        )

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
        # Lambda: x -> expr
        if self.check(TokenKind.IDENTIFIER):
            snap = self.snapshot()
            try:
                name_tok = self.advance()
                type_ann: ast.TypeExpr | None = None
                if self.match(TokenKind.COLON):
                    type_ann = self.parse_type_expr()
                if self.match(TokenKind.ARROW):
                    # Block lambda: x -> : NEWLINE INDENT ...
                    lambda_body: ast.Expr | list[ast.Stmt]
                    if self.match(TokenKind.COLON):
                        lambda_body = self.parse_block()
                    else:
                        lambda_body = self.parse_expression()
                    return ast.LambdaExpr(
                        params=[ast.LambdaParam(name=name_tok.text, type_annotation=type_ann)],
                        body=lambda_body,
                    )
            except ParseError:
                self.restore(snap)
            else:
                self.restore(snap)

        # Lambda: (a, b: T) -> expr  or  (a, b) -> : block
        if self.check(TokenKind.LPAREN):
            snap = self.snapshot()
            try:
                self.advance()
                params: list[ast.LambdaParam] = []
                if not self.check(TokenKind.RPAREN):
                    while True:
                        if not self.check(TokenKind.IDENTIFIER):
                            raise ParseError("Expected lambda parameter name", self.current)
                        p_name = self.advance().text
                        p_type: ast.TypeExpr | None = None
                        if self.match(TokenKind.COLON):
                            p_type = self.parse_type_expr()
                        params.append(ast.LambdaParam(name=p_name, type_annotation=p_type))
                        if not self.match(TokenKind.COMMA):
                            break
                        if self.check(TokenKind.RPAREN):
                            break
                self.expect(TokenKind.RPAREN)
                if self.match(TokenKind.ARROW):
                    lambda_body2: ast.Expr | list[ast.Stmt]
                    if self.match(TokenKind.COLON):
                        lambda_body2 = self.parse_block()
                    else:
                        lambda_body2 = self.parse_expression()
                    return ast.LambdaExpr(params=params, body=lambda_body2)
            except ParseError:
                self.restore(snap)
            else:
                self.restore(snap)

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


def parse_repl_input(source: str) -> list[ast.Decl | ast.Stmt]:
    """Parse a REPL input that may contain declarations, statements, or expressions.

    Returns a flat list of Decl and Stmt nodes for the REPL to process one by one.
    Declarations (fn, typealias, use, pub) are parsed as Decl; everything else as Stmt.
    """
    parser = Parser(source)
    items: list[ast.Decl | ast.Stmt] = []
    _DECL_STARTS = (TokenKind.FN, TokenKind.TYPEALIAS, TokenKind.USE, TokenKind.PUB)
    while not parser.check(TokenKind.EOF):
        parser.skip_newlines()
        if parser.check(TokenKind.EOF):
            break
        if parser.check(*_DECL_STARTS):
            items.append(parser.parse_top_level_item())
        else:
            # Statements cover: bindings, assign, if, while, for, match, return,
            # break, continue, and bare expressions (including `x := expr`).
            items.append(parser.parse_statement())
    return items
