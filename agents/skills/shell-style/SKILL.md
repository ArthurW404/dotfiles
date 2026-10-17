---
name: shell-style
description: >-
  Shell scripting safety standards, defensive practices, and formatting based on the
  Google Shell Style Guide. Activate this skill when writing, reviewing, or debugging
  Bash, POSIX sh, or Fish scripts.
---

# Shell Scripting Safety & Style Guide

Follow these defensive standards for all shell scripts.

## 1. Safety Header
Every executable Bash script must start with the strict safety header:

```bash
#!/usr/bin/env bash
set -euo pipefail
```
- `-e`: Exit immediately on command failure.
- `-u`: Treat unset variables as errors and exit immediately.
- `-o pipefail`: Return the exit status of the first failed command in a pipeline.

## 2. Defensive Coding Rules
- **Always Quote Variables**: Double-quote all variable and command substitutions: `"$var"`, `"$(cmd)"`, `"$@"`. Never leave bare `$var` unless intentional word-splitting is strictly required.
- **Prefer `[[ ... ]]` over `[ ... ]` in Bash**: Double brackets prevent word-splitting bugs and provide regex matching (`=~`) and pattern matching.
- **Functions & Scope**:
  - Always declare variables inside functions with `local`:
    ```bash
    process_file() {
        local input_path="$1"
        local temp_dir
        temp_dir="$(mktemp -d)"
        ...
    }
    ```
- **Error Messages to Stderr**: Send errors, warnings, and diagnostic output to stderr:
  ```bash
  echo "Error: Configuration file not found at $config_path" >&2
  return 1
  ```
- **Temporary Files & Cleanup**: Always register a `trap` for cleanup of temporary directories:
  ```bash
  scratch_dir="$(mktemp -d)"
  trap 'rm -rf "$scratch_dir"' EXIT
  ```

## 3. Resolving Script Directory
Never assume the current working directory is where the script resides:

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

## 4. When to Use Python Instead (Google Shell Guide Rule)
If a script meets any of the following criteria, **do not write it in Bash**:
- It exceeds ~100 lines of code.
- It requires complex data structures (nested maps, lists of objects).
- It needs robust JSON, YAML, or TOML parsing.
- Performance or complex string manipulation is critical.

Instead, write a single-file Python script using PEP 723 metadata:
```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["rich", "click"]
# ///
import click
...
```

## 5. Verification
Verify all bash scripts using `shellcheck`:
```sh
shellcheck <script.sh>
```
