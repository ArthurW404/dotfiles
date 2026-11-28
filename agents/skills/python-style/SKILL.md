---
name: python-style
description: >-
  Modern Python style guide, type annotation standards, and idioms based on the Google
  Python Style Guide and PEP 8. Activate this skill when writing, reviewing, or
  refactoring Python code, managing types, docstrings, or configuring ruff/pytest.
---

# Modern Python Engineering & Style Guide

Follow these standards for all Python projects, targeting modern Python (3.10+ syntax required, 3.11/3.12+ preferred).

## 1. Type Annotations (Strict Typing)
- All public functions, methods, and class attributes **must be fully type-annotated**.
- Use modern 3.10+ union and built-in collection syntax:
  - `int | None` instead of `Optional[int]`
  - `list[str]`, `dict[str, Any]`, `set[int]` instead of `typing.List`, `typing.Dict`, `typing.Set`
  - `tuple[int, ...]` for variable-length tuples; `tuple[int, str]` for fixed-length.
- For function parameters, prefer abstract interfaces from `collections.abc`:
  - Use `Sequence[T]` instead of `list[T]` when only indexing or iteration is needed.
  - Use `Mapping[K, V]` instead of `dict[K, V]` for read-only dictionary lookups.
  - Use `Iterable[T]` for generator or streaming inputs.
- Use `typing.Protocol` for structural typing (duck typing) instead of tight inheritance.

## 2. Data Modeling & Modern Idioms
- **Structured Data**:
  - Prefer `@dataclass(slots=True, frozen=True)` for immutable data transfer objects.
  - Use `pydantic.BaseModel` when serialization, deserialization, or validation against external data (API, JSON) is needed.
  - Never pass untyped `dict[str, Any]` across module boundaries when structured data can be defined.
- **Filesystem**:
  - Always use `pathlib.Path` instead of raw `os.path` strings:
    ```python
    from pathlib import Path
    config_path = Path.home() / ".config" / "app" / "config.toml"
    ```
- **Context Managers**: Always use `with` statements for files, sockets, locks, and database sessions.
- **Default Arguments**: **Never use mutable default arguments.**
  ```python
  # Correct
  def process_items(items: list[str] | None = None) -> list[str]:
      target_items = items if items is not None else []
      ...
  ```

## 3. Error Handling
- Never use bare `except:` or catch generic `Exception` unless re-raising or logging at the top-level application boundary.
- Catch specific exceptions (`ValueError`, `FileNotFoundError`, `KeyError`).
- Use exception chaining when translating exceptions:
  ```python
  try:
      raw = config_file.read_text()
  except OSError as err:
      raise ConfigurationError(f"Failed to read config from {config_file}") from err
  ```

## 4. Documentation & Google-Style Docstrings
Include Google-style docstrings for non-trivial public modules, classes, and functions:

```python
def fetch_user_record(user_id: str, timeout_seconds: float = 5.0) -> UserRecord:
    """Fetches user metadata from the primary repository.

    Args:
        user_id: Unique string identifier for the user.
        timeout_seconds: Maximum duration to wait before aborting.

    Returns:
        UserRecord containing validated account details.

    Raises:
        UserNotFoundError: If no record matching user_id exists.
        NetworkTimeoutError: If the remote query exceeds timeout_seconds.
    """
```

## 5. Complexity & Standard `pyproject.toml` Baseline
Enforce cyclomatic/structural complexity and strict typing automatically so functions stay small and shallow (`~/.config/ruff/ruff.toml` acts as a user-level fallback when a project has no local config):

- **Complexity Rules (Ruff)**: `C901` (`max-complexity = 10`), `PLR` (`max-branches = 10`, `max-returns = 6`, `max-args = 6`, `max-statements = 40`), plus `SIM` and `RET` to simplify nesting and redundant branches.
- **Reducing Complexity**: When `C901` or `PLR` triggers, extract focused private helpers, invert conditions into guard clauses / early returns, or replace branch chains with dispatch mappings (`dict` / `match`). Never silence warnings with `# noqa: C901`.
- **Cognitive Complexity (Optional Audit)**: For deeply nested loops or conditionals that flat McCabe counts understate, run:
  ```sh
  uvx complexipy . --max-complexity-allowed 15
  ```
- **Standard `pyproject.toml` Template**: Use `"strict"` mode in `basedpyright` for new applications (or `"standard"` when incrementally tightening existing codebases). Use `uv run mypy --strict .` instead when an app depends on mypy plugins (e.g., SQLAlchemy, Django).

```toml
[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "RET", "C901", "PLR", "ANN"]
ignore = ["E501", "ANN401", "PLR2004"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.pylint]
max-returns = 6
max-branches = 10
max-args = 6
max-statements = 40

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["ANN", "PLR0913"]
"**/test_*.py" = ["ANN", "PLR0913"]
"test_*.py" = ["ANN", "PLR0913"]
"**/*_test.py" = ["ANN", "PLR0913"]
"*_test.py" = ["ANN", "PLR0913"]
"**/conftest.py" = ["ANN", "PLR0913"]
"conftest.py" = ["ANN", "PLR0913"]

[tool.basedpyright]
typeCheckingMode = "strict" # or "standard" for existing codebases
```

## 6. Tooling & Verification Workflow
Always verify Python code using `uv` and `ruff`:

1. **Lint and Auto-Fix**:
   ```sh
   uvx ruff check --fix .
   ```
2. **Format**:
   ```sh
   uvx ruff format .
   ```
3. **Type Check**:
   ```sh
   uv run basedpyright  # or uvx basedpyright; use `uv run mypy --strict .` for plugin-heavy stacks (SQLAlchemy/Django), or `uvx ty check` for fast checks
   ```
4. **Run Tests**:
   ```sh
   uv run pytest -q --tb=short
   ```
5. **Property-Based & Invariant Testing (`hypothesis`)**:
   - Prefer `hypothesis` (`@given(...)`) over hardcoded example tables for parsers, serializers, mathematical/financial routines, and state machines:
     - **Round-Trip**: `decode(encode(x)) == x`
     - **Idempotency**: `normalize(normalize(x)) == normalize(x)`
     - **Oracle / Differential**: `fast_impl(x) == naive_reference(x)`
     - **Structural / Conservation Invariants**: e.g. portfolio weights sum to `1.0`, sort preserves multiset elements, bounds hold across `st.floats(allow_nan=False, allow_infinity=False)`.
   - Exercise real lightweight collaborators (`tmp_path`, in-memory `sqlite3`) rather than patching internal functions with `unittest.mock`. Never write tests whose sole assertion is `mock_fn.assert_called_once_with(...)`.
6. **Test Effectiveness & Mutation Verification**:
   - **Sabotage Check (Red-Green-Revert)**: For bug fixes and critical boundary conditions (`<` vs `<=`) only, verify the test fails when the fix is temporarily reverted.
   - **Mutation Testing (`mutmut`)**: Run only when explicitly requested for auditing assertion coverage on critical modules:
     ```sh
     uv run --with mutmut mutmut run "<module>*"
     ```
