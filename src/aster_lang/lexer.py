from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    """Token kinds for the Aster language."""

    # Keywords
    FN = auto()
    USE = auto()
    AS = auto()
    TYPEALIAS = auto()
    MUT = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    FOR = auto()
    IN = auto()
    MATCH = auto()
    RETURN = auto()
    BREAK = auto()
    CONTINUE = auto()
    PUB = auto()
    TRUE = auto()
    FALSE = auto()
    NIL = auto()
    NOT = auto()
    AND = auto()
    OR = auto()

    # Operators
    ASSIGN = auto()  # <-
    BIND = auto()  # :=
    ARROW = auto()  # ->
    EQ = auto()  # ==
    NE = auto()  # !=
    LT = auto()  # <
    LE = auto()  # <=
    GT = auto()  # >
    GE = auto()  # >=
    PLUS = auto()  # +
    MINUS = auto()  # -
    STAR = auto()  # *
    SLASH = auto()  # /
    PERCENT = auto()  # %
    DOT = auto()  # .

    # Delimiters
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    LBRACE = auto()  # {
    RBRACE = auto()  # }
    COLON = auto()  # :
    COMMA = auto()  # ,

    # Literals
    INTEGER = auto()
    STRING = auto()
    IDENTIFIER = auto()

    # Indentation
    INDENT = auto()
    DEDENT = auto()
    NEWLINE = auto()

    # Special
    EOF = auto()
    COMMENT = auto()


# Keyword map for quick lookup
KEYWORDS = {
    "fn": TokenKind.FN,
    "use": TokenKind.USE,
    "as": TokenKind.AS,
    "typealias": TokenKind.TYPEALIAS,
    "mut": TokenKind.MUT,
    "if": TokenKind.IF,
    "else": TokenKind.ELSE,
    "while": TokenKind.WHILE,
    "for": TokenKind.FOR,
    "in": TokenKind.IN,
    "match": TokenKind.MATCH,
    "return": TokenKind.RETURN,
    "break": TokenKind.BREAK,
    "continue": TokenKind.CONTINUE,
    "pub": TokenKind.PUB,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
    "nil": TokenKind.NIL,
    "not": TokenKind.NOT,
    "and": TokenKind.AND,
    "or": TokenKind.OR,
}


@dataclass(slots=True, frozen=True)
class SourceLocation:
    """Source location information for a token."""

    line: int  # 1-based line number
    column: int  # 0-based column number
    offset: int  # 0-based byte offset in source


@dataclass(slots=True)
class Token:
    """A lexical token with source location information."""

    kind: TokenKind
    text: str
    start: SourceLocation
    end: SourceLocation

    def __repr__(self) -> str:
        return f"Token({self.kind.name}, {self.text!r}, {self.start.line}:{self.start.column})"


class Lexer:
    """Indentation-aware lexer for the Aster language."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 0
        self.indent_stack: list[int] = [0]  # Stack of indentation levels
        self.pending_tokens: list[Token] = []  # Tokens to emit before next token
        self.at_line_start = True  # Track if we're at the start of a line

    def current_location(self) -> SourceLocation:
        """Get the current source location."""
        return SourceLocation(line=self.line, column=self.column, offset=self.pos)

    def peek(self, offset: int = 0) -> str:
        """Peek at a character without consuming it."""
        pos = self.pos + offset
        return self.source[pos] if pos < len(self.source) else ""

    def advance(self) -> str:
        """Consume and return the current character."""
        if self.pos >= len(self.source):
            return ""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 0
            self.at_line_start = True
        else:
            self.column += 1
        return ch

    def skip_whitespace(self) -> None:
        """Skip whitespace except newlines."""
        while self.peek() and self.peek() in " \t\r":
            self.advance()

    def skip_comment(self) -> None:
        """Skip a comment to end of line."""
        if self.peek() == "#":
            while self.peek() and self.peek() != "\n":
                self.advance()

    def read_string(self) -> str:
        """Read a string literal with escape sequences."""
        result = []
        self.advance()  # Skip opening quote
        while self.peek() and self.peek() != '"':
            if self.peek() == "\\":
                self.advance()
                next_ch = self.advance()
                if next_ch == "n":
                    result.append("\n")
                elif next_ch == "r":
                    result.append("\r")
                elif next_ch == "t":
                    result.append("\t")
                elif next_ch == "\\":
                    result.append("\\")
                elif next_ch == '"':
                    result.append('"')
                else:
                    result.append(next_ch)
            else:
                result.append(self.advance())
        if self.peek() == '"':
            self.advance()  # Skip closing quote
        return "".join(result)

    def read_number(self) -> str:
        """Read an integer literal."""
        result = []
        while self.peek().isdigit():
            result.append(self.advance())
        return "".join(result)

    def read_identifier(self) -> str:
        """Read an identifier or keyword."""
        result = []
        # First character: letter or underscore
        if self.peek().isalpha() or self.peek() == "_":
            result.append(self.advance())
        # Remaining characters: letters, digits, underscores
        while self.peek().isalnum() or self.peek() == "_":
            result.append(self.advance())
        return "".join(result)

    def handle_indentation(self) -> None:
        """Handle indentation at the start of a line."""
        if not self.at_line_start:
            return

        # At EOF or start of file, just mark not at line start
        if self.pos >= len(self.source):
            self.at_line_start = False
            return

        # Skip blank lines and comment-only lines without processing indentation
        while self.pos < len(self.source):
            # Count leading spaces
            indent = 0
            while self.peek() == " ":
                self.advance()
                indent += 1

            # Check if this is a blank line or comment-only line
            if self.peek() == "\n":
                # Blank line - consume newline and continue
                self.advance()
                continue
            elif self.peek() == "#":
                # Comment line - skip to end
                self.skip_comment()
                if self.peek() == "\n":
                    self.advance()
                continue
            elif self.peek() == "":
                # EOF reached
                self.at_line_start = False
                return
            else:
                # Real content found - process indentation
                self.at_line_start = False
                current_indent = self.indent_stack[-1]

                if indent > current_indent:
                    # Increased indentation
                    self.indent_stack.append(indent)
                    start = self.current_location()
                    self.pending_tokens.append(Token(TokenKind.INDENT, "", start, start))
                elif indent < current_indent:
                    # Decreased indentation
                    while self.indent_stack and self.indent_stack[-1] > indent:
                        self.indent_stack.pop()
                        start = self.current_location()
                        self.pending_tokens.append(Token(TokenKind.DEDENT, "", start, start))
                return

        # Reached EOF in loop
        self.at_line_start = False

    def next_token(self) -> Token:
        """Get the next token from the source."""
        # Return pending tokens first
        if self.pending_tokens:
            return self.pending_tokens.pop(0)

        # Handle indentation at line start
        self.handle_indentation()
        if self.pending_tokens:
            return self.pending_tokens.pop(0)

        # Skip whitespace (but not newlines)
        self.skip_whitespace()

        start = self.current_location()

        # End of file
        if self.pos >= len(self.source):
            # Emit any remaining DEDENTs
            if len(self.indent_stack) > 1:
                self.indent_stack.pop()
                return Token(TokenKind.DEDENT, "", start, start)
            return Token(TokenKind.EOF, "", start, start)

        ch = self.peek()

        # Newline
        if ch == "\n":
            self.advance()
            return Token(TokenKind.NEWLINE, "\n", start, self.current_location())

        # String literal
        if ch == '"':
            text = self.read_string()
            return Token(TokenKind.STRING, text, start, self.current_location())

        # Number
        if ch.isdigit():
            text = self.read_number()
            return Token(TokenKind.INTEGER, text, start, self.current_location())

        # Identifier or keyword
        if ch.isalpha() or ch == "_":
            text = self.read_identifier()
            kind = KEYWORDS.get(text, TokenKind.IDENTIFIER)
            return Token(kind, text, start, self.current_location())

        # Two-character operators
        if ch == ":" and self.peek(1) == "=":
            self.advance()
            self.advance()
            return Token(TokenKind.BIND, ":=", start, self.current_location())

        if ch == "<" and self.peek(1) == "-":
            self.advance()
            self.advance()
            return Token(TokenKind.ASSIGN, "<-", start, self.current_location())

        if ch == "-" and self.peek(1) == ">":
            self.advance()
            self.advance()
            return Token(TokenKind.ARROW, "->", start, self.current_location())

        if ch == "=" and self.peek(1) == "=":
            self.advance()
            self.advance()
            return Token(TokenKind.EQ, "==", start, self.current_location())

        if ch == "!" and self.peek(1) == "=":
            self.advance()
            self.advance()
            return Token(TokenKind.NE, "!=", start, self.current_location())

        if ch == "<" and self.peek(1) == "=":
            self.advance()
            self.advance()
            return Token(TokenKind.LE, "<=", start, self.current_location())

        if ch == ">" and self.peek(1) == "=":
            self.advance()
            self.advance()
            return Token(TokenKind.GE, ">=", start, self.current_location())

        # Single-character tokens
        single_char_tokens = {
            "(": TokenKind.LPAREN,
            ")": TokenKind.RPAREN,
            "[": TokenKind.LBRACKET,
            "]": TokenKind.RBRACKET,
            "{": TokenKind.LBRACE,
            "}": TokenKind.RBRACE,
            ":": TokenKind.COLON,
            ",": TokenKind.COMMA,
            "+": TokenKind.PLUS,
            "-": TokenKind.MINUS,
            "*": TokenKind.STAR,
            "/": TokenKind.SLASH,
            "%": TokenKind.PERCENT,
            ".": TokenKind.DOT,
            "<": TokenKind.LT,
            ">": TokenKind.GT,
        }

        if ch in single_char_tokens:
            kind = single_char_tokens[ch]
            self.advance()
            return Token(kind, ch, start, self.current_location())

        # Unknown character - skip it
        self.advance()
        return self.next_token()

    def tokenize_all(self) -> list[Token]:
        """Tokenize the entire source and return all tokens."""
        tokens = []
        while True:
            token = self.next_token()
            tokens.append(token)
            if token.kind == TokenKind.EOF:
                break
        return tokens


def tokenize(source: str) -> list[Token]:
    """Tokenize source code into a list of tokens."""
    lexer = Lexer(source)
    return lexer.tokenize_all()
