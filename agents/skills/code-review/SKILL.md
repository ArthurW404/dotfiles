---
name: code-review
description: >-
  Systematic engineering code review and pre-commit audit checklist. Activate this
  skill before submitting commits, opening pull requests, or when asked to review
  code diffs for correctness, security, safety, and maintainability.
---

# Systematic Code Review & Pre-Commit Audit

Use this checklist to perform rigorous self-review and peer code review before finalizing any change.

## 1. Correctness & Logic
- [ ] **Edge Cases**: Are `null`, `None`, empty strings, empty collections, `0`, and negative numbers handled gracefully?
- [ ] **Off-by-One**: Are loop ranges, slice bounds, and 0-indexed vs 1-indexed values correct?
- [ ] **Failure Paths**: Do error conditions abort cleanly or clean up partial state?
- [ ] **Concurrency & Race Conditions**: Are shared mutable resources synchronized or made immutable?

## 2. Resource & Memory Safety
- [ ] **Leaks**: Are all file handles, network sockets, database connections, and memory allocations closed via RAII (`std::unique_ptr`) or context managers (`with`)?
- [ ] **Exceptions**: Are catch blocks specific rather than catching blanket exceptions?
- [ ] **Timeouts**: Do all remote network, HTTP, or subprocess calls define explicit timeouts?

## 3. Security Audit
- [ ] **Secrets & Credentials**: Are there any hardcoded API keys, passwords, bearer tokens, or `.env` files in the diff?
- [ ] **Input Sanitization**: Are user/external inputs parameterized to prevent SQL, command, or path traversal injection?
- [ ] **Safe Permissions**: Are created files/directories created with safe permissions (e.g. `0700` / `0600` where appropriate)?

## 4. Simplicity & Minimal Diffs
- [ ] **Minimal Diffs**: Does the diff touch only what is necessary for the task? No unrelated formatting churn.
- [ ] **Readability**: Is the logic straightforward and readable without clever obfuscation?
- [ ] **No Dead Code**: Are unused imports, temporary print/debug statements, and commented-out code blocks deleted?
- [ ] **Zero Fake Backwards-Compatibility**: Are there deprecated aliases, compatibility shims, or dead legacy paths that should be cleanly pruned instead?
- [ ] **Interface Segregation**: Does any class implement dummy methods, `pass`, or `NotImplementedError` just to satisfy an oversized protocol? If so, split the protocol.
- [ ] **Complexity Limits**: Are files under ~300 lines and methods under ~40 lines? Decompose monolithic functions into focused private helpers.

## 5. Verification & Test Effectiveness
- [ ] **Automated Tests**: Are there tests covering both the happy path and critical failure/boundary cases (`0`, `-1`, empty collections, `None`, `NaN`)?
- [ ] **Assertion Strength (No Tautologies)**: Do tests assert concrete output values, state transitions, or exact exception messages rather than weak `is not None` checks or merely asserting that a mock was called?
- [ ] **Behavior Over Implementation (Minimal Mocking)**: Do tests exercise public contracts using real lightweight collaborators (e.g. `:memory:` SQLite, `tmp_path`, fake transports) instead of mocking internal private helpers?
- [ ] **Sabotage / Mutation Verification**: For bug fixes and critical branch logic, was the test verified to fail when the production fix or boundary condition is reverted/mutated (Red-Green-Revert, `mutmut`, `cargo-mutants`, or `Stryker`)?
- [ ] **Property-Based Invariants (PBT)**: For parsers, serializers, mathematical/quant routines, and state machines, are behavioral invariants (round-trip, idempotency, reference-oracle equivalence, conservation laws) tested with property-based generators (`hypothesis`, `proptest`, `fast-check`)?
- [ ] **Linters & Formatters**: Did relevant linters pass (`ruff`, `clang-tidy`, `shellcheck`) with zero warnings?
- [ ] **Clean Git Status**: Run `git status -sb` and `git diff --staged` to confirm only intended files are committed.

## 6. PR Sizing & Diff Budget Audit
Audit branch size against `origin/main` (`git diff origin/main...HEAD --shortstat`):
- [ ] **Under Budget**: Is the diff `< 200 lines` across `≤ 3–5 files`?
- [ ] **Split Triggers (>300 lines)**: If the change exceeds 300 lines, flag a `DIFF BUDGET WARNING` and recommend logical split boundaries (e.g. Protocol & Tests -> Engine -> UI) before submitting for review.
