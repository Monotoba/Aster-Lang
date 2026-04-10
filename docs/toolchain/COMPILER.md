# Compiler Design Notes

## Goal

Compile Aster from source to an analyzable intermediate form and eventually to bytecode and/or native code.

## Recommended pipeline

1. source text
2. tokens
3. concrete syntax tree
4. abstract syntax tree
5. name resolution
6. typed high-level IR
7. lowered ownership/effect-aware IR
8. backend IR
9. bytecode or native artifact

## Why multiple IR levels

Aster has:
- expressive syntax
- structured patterns
- ownership and reference forms
- effect tracking aspirations

A staged compiler will make the language easier to validate and extend.
