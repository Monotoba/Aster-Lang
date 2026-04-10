# Aster Language Overview

Aster is designed as a human-first general-purpose language.

## Core principles

- visible structure
- explicit mutation
- explicit effects
- expression-first composition
- regular syntax
- strong tooling
- readability over clever terseness

## Surface direction

Aster uses:
- indentation-sensitive blocks
- `:` to introduce blocks
- `:=` for inferred bindings
- `<-` for mutation
- `name: Type` for type annotations
- algebraic data types and pattern matching
- references and ownership-aware pointer types
- explicit effect and async markers
- formatter-friendly syntax

## Ownership direction

Recommended surface types:
- `&T` shared reference
- `&mut T` mutable reference
- `*own T` unique owning pointer
- `*shared T` ref-counted shared ownership
- `*weak T` weak non-owning pointer
- `*raw T` unsafe/raw interop pointer

The static semantics for these should be documented before implementation begins in earnest.
