Below is a first draft specification for the language.

I will keep it exploratory rather than design-locking unless you tell me to lock it.

# Aster Language Draft Specification

## Human-first general-purpose programming language

## 1. Purpose

Aster is a general-purpose programming language designed for human comprehension first, while still being suitable for serious software engineering.

Its core goals are:

* make program meaning visually obvious
* make mutation, effects, and failure explicit
* keep syntax regular and easy to parse by humans
* support strong tooling and refactoring
* support both scripting-scale and systems-scale programs
* favor expressions and structured data over incidental ceremony

Aster is not trying to be the shortest language, the most mathematically pure language, or the most machine-like language. It is trying to be a language in which a skilled human can read unfamiliar code and quickly understand what it does, what it may change, what may fail, and what external effects it performs.

---

## 2. Design philosophy

### 2.1 Primary principle

**Make meaning visible.**

The syntax should help the reader see:

* structure
* data flow
* control flow
* state change
* failure paths
* effect boundaries
* abstraction boundaries

### 2.2 Secondary principles

#### A. Structural honesty

Source text should reflect program structure clearly.

#### B. Explicit mutation

Mutation must look different from definition and from equality.

#### C. Explicit effects

Code that performs I/O, mutation of external state, suspension, or other effects should say so.

#### D. Expression-first

Most constructs should yield values and compose naturally.

#### E. Regularity over cleverness

The language should prefer a few consistent rules over many specialized forms.

#### F. Readability over terseness

The language should optimize for reading and maintenance.

#### G. Toolability

The syntax should be easy to parse incrementally, format canonically, analyze statically, and transform structurally.

---

## 3. Language overview

Aster uses:

* indentation-sensitive blocks
* explicit block introducers using `:`
* expression-oriented control constructs
* infix notation for arithmetic and comparisons
* explicit mutation operator `<-`
* type annotations using `name: Type`
* inferred bindings using `:=`
* algebraic data types
* pattern matching
* explicit result/optional handling
* explicit effect markers on functions
* structured macros over syntax trees, not text

---

## 4. Lexical conventions

## 4.1 Character set

Source files are Unicode text encoded as UTF-8.

Identifiers may use Unicode letters, though the standard style guide recommends ASCII identifiers for public APIs unless domain-specific notation benefits from Unicode.

## 4.2 Whitespace

Whitespace is significant for block structure.

Indentation defines nested blocks. Tabs are forbidden in source files. Indentation must use spaces only.

A newline terminates an expression or declaration unless:

* the expression is syntactically incomplete
* the expression is inside parentheses, brackets, or braces
* the next line is indented as part of a block introduced by `:`

## 4.3 Comments

Single-line comments:

```txt
# this is a comment
```

Documentation comments:

```txt
/// Return the area of a circle.
```

Block comments are not included in the initial version. Nested documentation and comment structure should be handled by repeated line comments to preserve lexical simplicity.

## 4.4 Identifiers

Identifiers begin with a letter or `_`, followed by letters, digits, or `_`.

Examples:

```txt
value
parse_user
_user_id
π
```

Style recommendations:

* types use `PascalCase`
* functions and bindings use `snake_case`
* constants use `SCREAMING_SNAKE_CASE` only where appropriate
* traits use `PascalCase`

---

## 5. Core syntax model

## 5.1 Blocks

Blocks begin with `:` and continue with increased indentation.

Example:

```txt
fn sign(n: Int) -> Int:
    if n < 0:
        -1
    else if n > 0:
        1
    else:
        0
```

This rule is universal for all block-bearing constructs.

## 5.2 Grouping delimiters

* `(` `)` for grouped expressions and tuples
* `[` `]` for lists and indexed access
* `{` `}` for maps, sets, record literals, and structured bodies where needed

---

## 6. Values and bindings

## 6.1 Immutable bindings

Type-inferred immutable binding:

```txt
x := 10
name := "Randy"
```

Explicitly typed immutable binding:

```txt
x: Int = 10
name: Text = "Randy"
```

Semantics:

* `:=` introduces a new local binding with inferred type
* `name: Type = expr` introduces a new binding with explicit type

Bindings are immutable unless declared mutable.

## 6.2 Mutable bindings

Mutable variable:

```txt
mut count := 0
mut total: Float = 0.0
```

Mutation uses `<-`:

```txt
count <- count + 1
total <- total + price
```

Rationale:

* definition is distinct from mutation
* equality is distinct from both

## 6.3 Constants

Module-level constants:

```txt
const PI: Float = 3.141592653589793
const DEFAULT_PORT := 8080
```

---

## 7. Primitive types

Initial primitive types:

* `Bool`
* `Int`
* `UInt`
* `Float`
* `Text`
* `Char`
* `Byte`
* `Unit`

Literals:

```txt
true
false
123
0xff
3.14
"hello"
'a'
()
```

`Unit` has one value: `()`.

---

## 8. Composite data

## 8.1 Lists

```txt
nums := [1, 2, 3]
empty: List[Int] = []
```

## 8.2 Tuples

```txt
point := (10, 20)
```

Single-element tuples require a trailing comma:

```txt
single := (42,)
```

## 8.3 Maps

```txt
config := {
    "host": "localhost",
    "port": 8080,
}
```

## 8.4 Records

Anonymous record literal:

```txt
user := {
    id: 1,
    name: "Ada",
    active: true,
}
```

Field access:

```txt
user.name
user.active
```

Named record types are preferred for durable APIs.

---

## 9. Type declarations

## 9.1 Record types

```txt
type User = {
    id: Int,
    name: Text,
    email: Text?,
    active: Bool,
}
```

## 9.2 Sum types / algebraic data types

```txt
type Result[T, E] =
    Ok(T)
    | Err(E)
```

```txt
type Color =
    Red
    | Green
    | Blue
```

## 9.3 Recursive types

```txt
type ListNode[T] =
    Empty
    | Node(value: T, next: ListNode[T])
```

## 9.4 Type aliases

```txt
alias UserId = Int
alias Headers = Map[Text, Text]
```

---

## 10. Optionality and result types

## 10.1 Optional values

Optional type syntax:

```txt
Text?
User?
```

Constructors:

```txt
some("hello")
none
```

## 10.2 Results

Standard result type:

```txt
type Result[T, E] =
    Ok(T)
    | Err(E)
```

## 10.3 Propagation

Optional/result propagation operator:

```txt
user := find_user(id)?
text := read_text(path)?
```

Semantics:

* if the value is success/present, unwrap it
* otherwise propagate failure to the enclosing function if compatible

This is permitted only in functions whose return type supports propagation.

## 10.4 Recovery

```txt
user := find_user(id) else guest_user()
```

```txt
text := read_text(path) else:
    log("using default config")
    DEFAULT_CONFIG
```

---

## 11. Functions

## 11.1 Function declarations

Expression-bodied function:

```txt
fn square(x: Int) -> Int = x * x
```

Block-bodied function:

```txt
fn classify(n: Int) -> Text:
    if n < 0:
        "negative"
    else if n == 0:
        "zero"
    else:
        "positive"
```

## 11.2 Parameters

```txt
fn add(a: Int, b: Int) -> Int = a + b
```

## 11.3 Return type inference

Allowed for local/private functions where obvious:

```txt
fn add(a: Int, b: Int) = a + b
```

For public APIs, explicit return types are recommended and may be required by style or compiler policy.

## 11.4 Named arguments

```txt
draw_text("Hello", at: point, color: blue)
```

## 11.5 Default parameters

```txt
fn connect(host: Text, port: Int = 8080) -> Connection !net:
    ...
```

---

## 12. Effects

## 12.1 Motivation

One of Aster’s central ideas is that the syntax should show whether code merely computes a value or interacts with the world.

## 12.2 Function effect annotation

Effectful functions declare effects after the return type:

```txt
fn read_text(path: Path) -> Result[Text, IoError] !io:
    ...
```

```txt
fn fetch(url: Url) -> Result[Response, NetError] !net async:
    ...
```

Possible initial built-in effect markers:

* `!io`
* `!net`
* `!state`
* `!time`
* `!random`

`async` is separate from effect tags and indicates suspension capability.

Pure functions omit effect markers:

```txt
fn area(r: Float) -> Float = PI * r * r
```

## 12.3 Effect inference

The compiler may infer effects internally, but public signatures must expose them.

## 12.4 Effect polymorphism

Deferred in the first edition of the spec. The initial design should support it later, but not require it immediately.

---

## 13. Control flow

## 13.1 If expressions

```txt
result :=
    if score >= 60:
        "pass"
    else:
        "fail"
```

## 13.2 While loops

```txt
while not done:
    tick()
```

## 13.3 For loops

```txt
for item in items:
    print(item)
```

Range iteration:

```txt
for i in 0 ..< 10:
    print(i)
```

Inclusive range:

```txt
for i in 1 .. 5:
    print(i)
```

## 13.4 Break and continue

```txt
for item in items:
    if item.invalid:
        continue
    if item.done:
        break
    process(item)
```

---

## 14. Pattern matching

Pattern matching is a first-class construct.

## 14.1 Match expression

```txt
match token:
    Number(value):
        emit_number(value)
    Plus:
        emit_plus()
    Minus:
        emit_minus()
    _:
        fail "unexpected token"
```

## 14.2 Destructuring records

```txt
match user:
    {name: n, active: true}:
        greet(n)
    _:
        ignore()
```

## 14.3 Tuple destructuring

```txt
match point:
    (0, 0):
        "origin"
    (x, 0):
        "x-axis at {x}"
    (0, y):
        "y-axis at {y}"
    (x, y):
        "point {x}, {y}"
```

## 14.4 Binding in patterns

```txt
match result:
    Ok(value):
        use(value)
    Err(err):
        log(err)
```

## 14.5 Guard patterns

```txt
match n:
    x if x < 0:
        "negative"
    0:
        "zero"
    x:
        "positive {x}"
```

---

## 15. Expressions

## 15.1 Arithmetic

```txt
a + b
a - b
a * b
a / b
a % b
```

## 15.2 Comparison

```txt
a == b
a != b
a < b
a <= b
a > b
a >= b
```

## 15.3 Boolean operators

```txt
not ready
a and b
a or b
```

Keyword boolean operators are chosen over `&&` and `||` to reduce symbolic noise.

## 15.4 Operator precedence

Aster intentionally keeps a small precedence ladder.

Proposed order from high to low:

1. field access, indexing, calls
2. unary `not`, unary `-`
3. `* / %`
4. `+ -`
5. ranges `.. ..<`
6. comparisons
7. `and`
8. `or`
9. `else` recovery
10. pipeline `|>`

The full precedence table should remain small and stable.

---

## 16. Function literals

## 16.1 Lambda syntax

```txt
x -> x * x
(a, b) -> a + b
```

Multi-line lambda:

```txt
user ->:
    if user.active:
        user.email
    else:
        none
```

## 16.2 Usage

```txt
nums |> map(x -> x * 2)
```

---

## 17. Pipelines

Pipelines are included for readability in transformation-heavy code.

```txt
emails :=
    users
    |> filter(.active)
    |> flat_map(user -> user.email.to_list())
    |> sort()
```

Semantics:

* `a |> f()` becomes `f(a)`
* `a |> f(x, y)` becomes `f(a, x, y)`

Placeholder shorthand:

* `.name` means `x -> x.name`
* `.active` means `x -> x.active`

This shorthand is limited to field/member extraction and zero-argument member access for clarity.

---

## 18. Assignment and mutation

## 18.1 Mutation syntax

```txt
value <- expr
```

Examples:

```txt
mut sum := 0
sum <- sum + 1
```

## 18.2 Indexed mutation

```txt
buffer[i] <- normalize(buffer[i])
```

## 18.3 Field mutation

```txt
user.name <- "New Name"
```

Whether field mutation is allowed depends on mutability rules of the containing object.

---

## 19. Declarations at module scope

## 19.1 Module declaration

```txt
module app.users
```

## 19.2 Imports

```txt
use math.geometry: Point, Rect
use io.files: read_text
use ui.colors as colors
```

## 19.3 Public visibility

```txt
pub fn parse_user(...)
pub type User = ...
pub const DEFAULT_PORT := 8080
```

Default visibility is module-private.

---

## 20. Traits and implementations

## 20.1 Trait declarations

```txt
trait Renderable:
    fn render(self, canvas: Canvas) -> Unit !io
```

## 20.2 Implementation

```txt
impl Renderable for Button:
    fn render(self, canvas: Canvas) -> Unit !io:
        canvas.draw_rect(self.bounds)
        canvas.draw_text(self.label, at: self.bounds.center)
```

## 20.3 Philosophy

Aster supports behavior abstraction, but does not center the entire language around class syntax. Data and behavior may be coupled when useful, but plain functions remain first-class.

---

## 21. Methods

Methods are ordinary functions declared in `impl` blocks.

Method call syntax:

```txt
button.render(canvas)
```

Static/associated functions:

```txt
impl Path:
    fn join(a: Path, b: Path) -> Path:
        ...
```

Called as:

```txt
Path.join(a, b)
```

---

## 22. Error signaling

## 22.1 Result-first model

Aster prefers explicit result values over hidden exception control flow.

```txt
fn load(path: Path) -> Result[Config, LoadError] !io:
    ...
```

## 22.2 Panic/fail

For unrecoverable programmer errors:

```txt
fail "internal invariant violated"
```

This aborts the current task or process depending on runtime policy.

`fail` is not intended as ordinary control flow.

---

## 23. Async and concurrency

## 23.1 Async functions

```txt
fn fetch_user(id: UserId) -> Result[User, NetError] !net async:
    ...
```

## 23.2 Await

```txt
user := await fetch_user(id)?
```

## 23.3 Spawn

```txt
task := spawn sync_index(db)
```

## 23.4 Channels

Initial library-level abstraction rather than syntax-level primitive:

```txt
sender.send(msg)?
msg := receiver.recv()?
```

---

## 24. Generics

## 24.1 Generic functions

```txt
fn first[T](items: List[T]) -> T?:
    if items.is_empty():
        none
    else:
        some(items[0])
```

## 24.2 Generic types

```txt
type Box[T] = {
    value: T,
}
```

Type parameters use square brackets.

---

## 25. Type inference

Aster uses local type inference aggressively for bindings and expressions, but not in ways that obscure public APIs.

Example:

```txt
x := 10
name := "Ada"
items := [1, 2, 3]
```

Public functions and exported values should generally retain explicit types.

---

## 26. Destructuring binds

```txt
(x, y) := point
{name, active} := user
Ok(value) := compute()
```

The last form requires the pattern to match; otherwise it is a runtime failure or compile error depending on static provability. For ordinary uncertain flows, `match` is preferred.

---

## 27. Strings and interpolation

## 27.1 String literals

```txt
"hello"
```

## 27.2 Multiline strings

```txt
"""
line one
line two
"""
```

## 27.3 Interpolation

```txt
"Hello, {name}"
"Area = {area(radius)}"
```

---

## 28. Standard library conventions

The standard library should reflect the language philosophy:

* result-based error handling
* immutable data by default
* explicit I/O boundaries
* strong collection APIs
* parser/formatter-friendly data structures
* good text and Unicode support
* first-class time, path, file, process, and network libraries

---

## 29. Formatting rules

Aster should have a canonical formatter.

Formatting is part of the language ecosystem, not an afterthought.

Rules include:

* spaces, never tabs
* fixed indentation width
* trailing commas encouraged where multiline stability matters
* line breaks around pipelines and long argument lists
* standardized import ordering
* stable formatting of record and match forms

The formatter should preserve comments and doc comments predictably.

---

## 30. Macros and metaprogramming

## 30.1 Philosophy

Aster does not allow textual macros.

Macros operate on structured syntax trees with source locations preserved.

## 30.2 Syntax sketch

```txt
macro unless(condition, body):
    syntax:
        if not $condition:
            $body
```

This is illustrative only. The deeper design intent is:

* macros receive parsed syntax objects
* macro expansion is hygienic by default
* source mapping is preserved
* expanded code remains formatter- and tooling-friendly

A second draft spec should formalize:

* syntax object types
* hygiene model
* pattern matching on syntax
* compile phase separation

---

## 31. Example program

```txt
module app.main

type User = {
    id: Int,
    name: Text,
    email: Text?,
    active: Bool,
}

type LoadError =
    NotFound
    | InvalidData(Text)
    | IoError(Text)

fn parse_bool(text: Text) -> Bool:
    match text.lower():
        "true":
            true
        "yes":
            true
        "1":
            true
        _:
            false

fn parse_user(row: Map[Text, Text]) -> Result[User, LoadError]:
    id_text := row.get("id") else Err(InvalidData("missing id"))
    id := id_text.to_int() else Err(InvalidData("bad id"))

    name := row.get("name") else Err(InvalidData("missing name"))
    email := row.get("email")
    active := row.get("active").map(parse_bool).unwrap_or(false)

    Ok(User {
        id: id,
        name: name,
        email: email,
        active: active,
    })

fn active_emails(users: List[User]) -> List[Text]:
    users
    |> filter(.active)
    |> flat_map(user -> user.email.to_list())

fn send_report(users: List[User]) -> Result[Unit, Text] !io:
    emails := active_emails(users)

    if emails.is_empty():
        Err("no active recipients")
    else:
        for email in emails:
            print("sending to {email}")
        Ok(())

fn main() -> Result[Unit, Text] !io:
    users := [
        User { id: 1, name: "Ada", email: some("ada@example.com"), active: true },
        User { id: 2, name: "Bob", email: none, active: false },
        User { id: 3, name: "Cara", email: some("cara@example.com"), active: true },
    ]

    send_report(users)?
    Ok(())
```

---

## 32. Why this syntax was chosen

## 32.1 Why indentation and `:`

It makes structure obvious while avoiding heavy punctuation.

## 32.2 Why `:=` and `<-`

It cleanly separates:

* definition
* mutation
* equality

This removes one of the major longstanding ambiguities in mainstream syntax.

## 32.3 Why expression orientation

It improves composition and reduces the fragmentation between “statement forms” and “expression forms.”

## 32.4 Why pattern matching

It aligns closely with how humans reason about structured data.

## 32.5 Why effects are annotated

Because hidden effects make code harder to reason about and review.

## 32.6 Why not full Lisp syntax

Because most human readers benefit from stronger visual distinction between ordinary constructs, while we can still preserve structural macro power underneath.

## 32.7 Why not C syntax

Because C-family syntax has too much historical baggage for a new human-first language.

---

## 33. Open design questions

This draft leaves several areas open:

### A. Ownership / borrowing / memory model

This is intentionally unspecified in the first syntax draft.

### B. Error propagation exact typing rules

The `?` propagation rules need formalization.

### C. Effect system depth

Initial effect markers are simple. Whether Aster eventually gains algebraic effects, row polymorphism, or capability types is still open.

### D. Pattern exhaustiveness rules

These need formal definition.

### E. Macro API

Only sketched here.

### F. Module/package system

Needs a full spec for dependency and build semantics.

### G. Visibility and encapsulation granularity

Module-private vs package-private vs public remains to be finalized.

---

## 34. Summary

Aster is intended to be a language where:

* structure is easy to see
* mutation is explicit
* effects are visible
* failure is first-class
* types are readable
* data-oriented reasoning is natural
* tooling is strong
* syntax supports human understanding rather than historical accident

Its syntax is designed around the belief that a modern language should optimize not merely for what the machine can execute, but for what humans can reliably understand, maintain, and evolve.

The best next step is to formalize one of these directions:

* lexical grammar and EBNF
* type system
* effect system
* module/package system
* memory/runtime model
* macro system
* standard library design
* parser and AST design

The most productive next step would be the **EBNF plus AST model**, because that will test whether the syntax is actually as coherent as it currently appears.

