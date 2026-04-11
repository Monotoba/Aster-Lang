"""Tests for the lexer."""

from aster_lang.lexer import TokenKind, tokenize


def test_keywords() -> None:
    """Test keyword tokenization."""
    source = "fn use as typealias mut if else while for in match return break continue pub"
    tokens = tokenize(source)

    expected_kinds = [
        TokenKind.FN,
        TokenKind.USE,
        TokenKind.AS,
        TokenKind.TYPEALIAS,
        TokenKind.MUT,
        TokenKind.IF,
        TokenKind.ELSE,
        TokenKind.WHILE,
        TokenKind.FOR,
        TokenKind.IN,
        TokenKind.MATCH,
        TokenKind.RETURN,
        TokenKind.BREAK,
        TokenKind.CONTINUE,
        TokenKind.PUB,
        TokenKind.EOF,
    ]

    token_kinds = [t.kind for t in tokens]
    assert token_kinds == expected_kinds


def test_literals() -> None:
    """Test literal tokenization."""
    source = "42 true false nil"
    tokens = tokenize(source)

    assert tokens[0].kind == TokenKind.INTEGER
    assert tokens[0].text == "42"
    assert tokens[1].kind == TokenKind.TRUE
    assert tokens[2].kind == TokenKind.FALSE
    assert tokens[3].kind == TokenKind.NIL


def test_string_literals() -> None:
    """Test string literal tokenization."""
    source = '"hello" "world\\n" "tab\\there"'
    tokens = tokenize(source)

    assert tokens[0].kind == TokenKind.STRING
    assert tokens[0].text == "hello"
    assert tokens[1].kind == TokenKind.STRING
    assert tokens[1].text == "world\n"
    assert tokens[2].kind == TokenKind.STRING
    assert tokens[2].text == "tab\there"


def test_identifiers() -> None:
    """Test identifier tokenization."""
    source = "foo bar_baz _private myVar123"
    tokens = tokenize(source)

    assert all(t.kind == TokenKind.IDENTIFIER or t.kind == TokenKind.EOF for t in tokens)
    assert tokens[0].text == "foo"
    assert tokens[1].text == "bar_baz"
    assert tokens[2].text == "_private"
    assert tokens[3].text == "myVar123"


def test_operators() -> None:
    """Test operator tokenization."""
    source = ":= <- -> == != < <= > >= + - * / % & . |"
    tokens = tokenize(source)

    expected_kinds = [
        TokenKind.BIND,
        TokenKind.ASSIGN,
        TokenKind.ARROW,
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
        TokenKind.AMP,
        TokenKind.DOT,
        TokenKind.PIPE,
        TokenKind.EOF,
    ]

    token_kinds = [t.kind for t in tokens]
    assert token_kinds == expected_kinds


def test_delimiters() -> None:
    """Test delimiter tokenization."""
    source = "( ) [ ] { } : ,"
    tokens = tokenize(source)

    expected_kinds = [
        TokenKind.LPAREN,
        TokenKind.RPAREN,
        TokenKind.LBRACKET,
        TokenKind.RBRACKET,
        TokenKind.LBRACE,
        TokenKind.RBRACE,
        TokenKind.COLON,
        TokenKind.COMMA,
        TokenKind.EOF,
    ]

    token_kinds = [t.kind for t in tokens]
    assert token_kinds == expected_kinds


def test_indentation_simple() -> None:
    """Test simple indentation."""
    source = """fn main():
    x := 1
    y := 2
"""
    tokens = tokenize(source)
    kinds = [t.kind for t in tokens]

    # Should have: FN IDENTIFIER LPAREN RPAREN COLON NEWLINE INDENT ...
    assert kinds[0] == TokenKind.FN
    assert kinds[1] == TokenKind.IDENTIFIER
    assert kinds[5] == TokenKind.NEWLINE
    assert kinds[6] == TokenKind.INDENT
    # Should end with DEDENT EOF
    assert TokenKind.DEDENT in kinds
    assert kinds[-1] == TokenKind.EOF


def test_indentation_nested() -> None:
    """Test nested indentation."""
    source = """if x:
    if y:
        z := 1
"""
    tokens = tokenize(source)
    kinds = [t.kind for t in tokens]

    # Count indents and dedents
    indent_count = kinds.count(TokenKind.INDENT)
    dedent_count = kinds.count(TokenKind.DEDENT)

    assert indent_count == 2  # Two levels of indentation
    assert dedent_count == 2  # Two dedents at the end


def test_indentation_mixed_levels() -> None:
    """Test mixed indentation levels."""
    source = """fn main():
    x := 1
    if x:
        y := 2
    z := 3
"""
    tokens = tokenize(source)
    kinds = [t.kind for t in tokens]

    # Should have indents and dedents properly balanced
    indent_count = kinds.count(TokenKind.INDENT)
    dedent_count = kinds.count(TokenKind.DEDENT)

    assert indent_count == 2  # One for function body, one for if body
    assert dedent_count == 2  # Matching dedents


def test_comments() -> None:
    """Test comment handling."""
    source = """# This is a comment
x := 1  # inline comment
# Another comment
"""
    tokens = tokenize(source)
    kinds = [t.kind for t in tokens]

    # Comments should be skipped
    assert TokenKind.COMMENT not in kinds
    # But identifiers and operators should be present
    assert TokenKind.IDENTIFIER in kinds
    assert TokenKind.BIND in kinds


def test_empty_lines() -> None:
    """Test that empty lines are handled correctly."""
    source = """x := 1

y := 2
"""
    tokens = tokenize(source)
    kinds = [t.kind for t in tokens]

    # Should not have spurious indents/dedents
    assert kinds.count(TokenKind.INDENT) == 0
    assert kinds.count(TokenKind.DEDENT) == 0


def test_source_locations() -> None:
    """Test that source locations are tracked correctly."""
    source = "fn main():\n    x := 1"
    tokens = tokenize(source)

    # First token should be at line 1, column 0
    assert tokens[0].kind == TokenKind.FN
    assert tokens[0].start.line == 1
    assert tokens[0].start.column == 0

    # Token after newline should be on line 2
    for token in tokens:
        if token.kind == TokenKind.IDENTIFIER and token.text == "x":
            assert token.start.line == 2
            break


def test_function_declaration() -> None:
    """Test tokenizing a simple function declaration."""
    source = """fn add(a: Int, b: Int) -> Int:
    return a + b
"""
    tokens = tokenize(source)
    kinds = [t.kind for t in tokens]

    # Verify key tokens are present
    assert TokenKind.FN in kinds
    assert TokenKind.IDENTIFIER in kinds
    assert TokenKind.LPAREN in kinds
    assert TokenKind.COLON in kinds
    assert TokenKind.ARROW in kinds
    assert TokenKind.RETURN in kinds
    assert TokenKind.INDENT in kinds
    assert TokenKind.DEDENT in kinds


def test_mutation_operator() -> None:
    """Test the mutation operator."""
    source = "x <- 42"
    tokens = tokenize(source)

    assert tokens[0].kind == TokenKind.IDENTIFIER
    assert tokens[0].text == "x"
    assert tokens[1].kind == TokenKind.ASSIGN
    assert tokens[1].text == "<-"
    assert tokens[2].kind == TokenKind.INTEGER
    assert tokens[2].text == "42"


def test_comparison_operators() -> None:
    """Test all comparison operators."""
    source = "a == b != c < d <= e > f >= g"
    tokens = tokenize(source)
    kinds = [t.kind for t in tokens]

    assert TokenKind.EQ in kinds
    assert TokenKind.NE in kinds
    assert TokenKind.LT in kinds
    assert TokenKind.LE in kinds
    assert TokenKind.GT in kinds
    assert TokenKind.GE in kinds


def test_logical_operators() -> None:
    """Test logical operators."""
    source = "x and y or not z"
    tokens = tokenize(source)
    kinds = [t.kind for t in tokens]

    assert TokenKind.AND in kinds
    assert TokenKind.OR in kinds
    assert TokenKind.NOT in kinds


def test_real_example_hello() -> None:
    """Test tokenizing the hello.aster example."""
    source = """fn main():
    print("hello, world")
"""
    tokens = tokenize(source)

    # Should successfully tokenize without errors
    assert tokens[-1].kind == TokenKind.EOF
    assert any(t.kind == TokenKind.STRING and t.text == "hello, world" for t in tokens)


def test_real_example_sum_to() -> None:
    """Test tokenizing the sum_to.aster example."""
    source = """fn sum_to(n: Int) -> Int:
    mut total := 0
    mut i := 1
    while i <= n:
        total <- total + i
        i <- i + 1
    return total
"""
    tokens = tokenize(source)

    # Should successfully tokenize
    assert tokens[-1].kind == TokenKind.EOF
    kinds = [t.kind for t in tokens]

    # Verify key constructs are present
    assert TokenKind.FN in kinds
    assert TokenKind.MUT in kinds
    assert TokenKind.WHILE in kinds
    assert TokenKind.RETURN in kinds
    assert TokenKind.ASSIGN in kinds  # <-
    assert TokenKind.BIND in kinds  # :=
