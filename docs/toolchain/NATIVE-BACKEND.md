# Native Backend Feasibility Notes

Goal: validate a first native backend target using the standard IR + adapter boundary.

## Proposed target

Start with C for the feasibility spike, then revisit LLVM/Wasm after the IR interface stabilizes.

## Spike scope

- Emit a single C translation unit for an Aster module.
- Minimal runtime: `AsterValue` tagged union, string wrapper, basic helpers.
- Build/run via system `cc`.
- Placeholder C backend adapter exists but returns "not implemented" until IR emission lands.
- Placeholder C backend currently emits a stub `.c` file for visibility.

## Minimal language coverage

- Int arithmetic and comparisons.
- `if/else`, `while`.
- Function calls (no closures in spike).

## Open questions

- How much of the ownership surface should be represented in C stubs vs no-op?
- How to map module imports in a C-only artifact (single TU vs per-module linking)?
- What ABI conventions should be locked down for interop?
- Should the spike emit debug-friendly C with source mapping comments?

## Next actions

- Decide whether the spike should emit one C file per module or a single merged TU.
- Define the minimal `AsterValue` tag set for the spike (Int/Bool/Nil/String).
- Prototype a `cc` build step in the adapter harness once IR emission exists.
- Decide whether to emit debug-friendly C with source mapping comments.

## Feasibility study status

Status: scoped and documented; implementation spike not started.
