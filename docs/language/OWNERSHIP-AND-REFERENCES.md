# Ownership, References, and Smart Pointers

This document proposes the Aster ownership surface model.

## Goals

- allow systems-scale resource management
- remain readable
- support static analysis
- avoid hidden lifetime complexity where possible
- support both safe and explicitly unsafe interop

## Surface forms

### Borrowed references
- `&T` immutable/shared borrow
- `&mut T` unique mutable borrow

### Pointer kinds
- `*own T` unique owning smart pointer
- `*shared T` shared owning pointer with reference counting or equivalent runtime strategy
- `*weak T` weak observer pointer
- `*raw T` unsafe raw pointer

## Semantics sketch

### `&T`
Read-only aliasing allowed.

### `&mut T`
Exactly one active mutable borrow in the relevant region.

Current expression-level borrow surface includes identifier, member, and index lvalues such as
`&mut x`, `&mut r.inner.x`, and `&mut make_list()[0]`.

### `*own T`
Single owner, move semantics by default.

### `*shared T`
Reference-counted or managed shared ownership.

### `*weak T`
May be upgraded conditionally if the referent still exists.

### `*raw T`
Unsafe; no lifetime or aliasing guarantees.

## Why this model

This gives Aster:
- an explicit and parseable ownership vocabulary
- a usable bridge between scripting and systems programming
- a clean documentation model
- a realistic path to future borrow checking

## Implementation guidance

Start with syntax and AST support only.
Then implement:
1. parser support
2. type representation
3. non-enforcing semantic warnings
4. staged ownership rules:
- scope-based borrow conflicts (single `&mut`, no `&` during `&mut`)
- escape restrictions until lifetimes exist:
  - cannot return a reference to a local
  - cannot put references into list/tuple/record literals
  - cannot store references in module-level bindings
