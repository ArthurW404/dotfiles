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

## 5. Tooling & Verification Workflow
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
   uv run mypy . # or pyright / ty
   ```
4. **Run Tests**:
   ```sh
   uv run pytest -v
   ```
