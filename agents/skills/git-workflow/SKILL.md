---
name: git-workflow
description: >-
  Standard Git branching, commit formatting, review hygiene, and pull request workflow.
  Activate this skill when creating branches, crafting commits, staging changes,
  rebasing, or preparing pull requests to enforce branch safety and clean commit history.
---

# Git Workflow & Best Practices Skill

Follow these engineering standards whenever branching, staging, committing, or preparing pull requests.

## 1. Branch Safety & Lifecycle
- **Never commit or push directly to `main` or `master`.**
- Always create a descriptive feature or fix branch from up-to-date main:
  ```sh
  git checkout main
  git pull --rebase
  git checkout -b <type>/<short-description>
  ```
- **Standard Branch Types**:
  - `feat/` — New user-facing feature or enhancement
  - `fix/` — Bug fix
  - `refactor/` — Code restructuring with no behavior change
  - `perf/` — Performance optimization
  - `test/` — Adding or correcting tests
  - `docs/` — Documentation updates
  - `chore/` — Tooling, dependency updates, dotfile configuration

## 2. Atomic Commits
- Each commit must represent a **single logical change** that builds cleanly and passes tests independently.
- **Never mix formatting/refactoring with behavioral changes in the same commit.** If you format a file and fix a bug, split into two commits: `refactor(...)` followed by `fix(...)`.
- Use interactive staging to split unrelated edits:
  ```sh
  git add -p <file>
  ```

## 3. Commit Message Anatomy
Follow the Conventional Commits specification and Chris Beams' rules for commit messages:

```text
<type>(<scope>): <imperative subject line in 50 characters or less>

<Optional detailed body explaining the "why" and trade-offs, wrapped at
72 characters per line. Do not merely restate what lines changed; explain
the motivation, context, and any alternatives considered.>

<Optional footer, e.g. Refs #123 or Resolves #456>
```

### The 7 Golden Rules of Commit Subject Lines:
1. Separate subject from body with a blank line.
2. Limit the subject line to 50 characters (hard ceiling at 72).
3. Do not capitalize the first letter after `<type>(<scope>):`.
4. Do not end the subject line with a period.
5. Use the **imperative mood** (e.g. `add feature`, `fix bug`, `refactor auth` — never `added`, `fixes`, `fixing`).
6. Wrap the body at 72 characters.
7. Use the body to explain **what and why** vs. *how*.

## 4. Pre-Commit Secret & Diff Audit
Before running `git commit`:
1. Check working directory status:
   ```sh
   git status -sb
   ```
2. Review staged changes line-by-line:
   ```sh
   git diff --staged
   ```
3. Audit for secrets: Ensure no `.env`, API tokens, private keys, or test credentials are staged.

## 5. History & Rebasing Hygiene
- Keep history linear by rebasing feature branches against main:
  ```sh
  git fetch origin
  git rebase origin/main
  ```
- If you need to update a remote feature branch after rebasing, **never use `--force`**. Always use `--force-with-lease`:
  ```sh
  git push --force-with-lease origin <branch-name>
  ```

## 6. Debugging with `git bisect`
When hunting for a regression:
```sh
git bisect start
git bisect bad HEAD
git bisect good <known-good-commit>
git bisect run <test-command>
git bisect reset
```
