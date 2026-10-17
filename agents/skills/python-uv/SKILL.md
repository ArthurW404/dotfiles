---
name: python-uv
description: >-
  Python environment, dependency management, script execution, and linting workflow
  using uv and ruff. Activate this skill when initializing Python projects, managing
  dependencies, running scripts, or executing pytest/ruff.
---

# Python with `uv` Skill

Use `uv` for all Python project, environment, and script workflows unless the repository explicitly requires another manager.

## Common Workflows

1. **Initialize a new project**:
   ```sh
   uv init <project-name>
   ```
2. **Add or remove dependencies**:
   ```sh
   uv add <package>
   uv add --dev pytest ruff
   ```
3. **Run commands inside the project environment** (no manual `.venv/bin/activate` needed):
   ```sh
   uv run python <script.py>
   uv run pytest
   ```
4. **Run standalone tools ephemerally**:
   ```sh
   uvx ruff check .
   uvx ruff format .
   ```
5. **Single-file scripts with inline metadata** (PEP 723):
   ```sh
   uv add --script <script.py> <package>
   uv run <script.py>
   ```
