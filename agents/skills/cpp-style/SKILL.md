---
name: cpp-style
description: >-
  Modern C++ style guide, idiomatic practices, and safety rules based on the Google C++
  Style Guide and C++ Core Guidelines. Activate this skill when writing, refactoring,
  or reviewing C++ code (C++17/C++20/C++23), CMake, or clang tooling.
---

# Modern C++ Engineering & Style Guide

Follow these standards for all C++ code, targeting modern standards (C++20 preferred, C++17 minimum).

## 1. Resource Management & Idioms (RAII)
- **Zero Raw Owning Pointers**: Never use raw `new` or `delete`. Manage resources through RAII classes or smart pointers:
  - Prefer `std::unique_ptr` for exclusive ownership: `auto ptr = std::make_unique<Widget>(...);`
  - Use `std::shared_ptr` only when true shared ownership is required.
- **Non-Owning Views**:
  - Prefer `std::string_view` over `const std::string&` for read-only string arguments.
  - Prefer `std::span<const T>` over pointer + size or `const std::vector<T>&` for contiguous sequences.
- **Value Semantics**: Pass cheap-to-copy types (primitives, `std::string_view`, `std::span`) by value; pass expensive types by `const&` or sink by value with `std::move`.
- **Value-Returning Functions**: Mark functions `[[nodiscard]]` when discarding the return value indicates a likely bug (e.g. error checks, factory functions).

## 2. Header & Include Hygiene
- Use `#pragma once` at the top of headers.
- **Strict Include Order** (grouped with a blank line between groups):
  1. The paired header for this implementation file (e.g. `widget.h` for `widget.cc`).
  2. C system headers (e.g. `<sys/types.h>`, `<unistd.h>`).
  3. C++ standard library headers (e.g. `<vector>`, `<string>`, `<memory>`).
  4. Other third-party libraries (e.g. `<boost/...>`, `<fmt/...>`).
  5. Your project's own headers (e.g. `"core/logger.h"`).
- **Include What You Use (IWYU)**: Do not rely on transitive includes. If a file uses `std::unique_ptr`, include `<memory>`.
- **Never use `using namespace ...` in headers.** In `.cc` files, prefer scoped using declarations (`using std::vector;`) or local aliases.

## 3. Naming Conventions (Google Style)
- **Types & Concepts**: `PascalCase` (`class HttpClient`, `struct PacketHeader`, `enum class ErrorCode`).
- **Functions & Methods**: `PascalCase` (`ExecuteQuery()`, `OpenConnection()`) or `camelCase` if matching existing project style.
- **Local Variables & Parameters**: `snake_case` (`connection_timeout`, `retry_count`).
- **Class Data Members**: `snake_case_` with trailing underscore (`socket_fd_`, `buffer_pool_`).
- **Constants & Enums**: `kPascalCase` (`constexpr int kMaxRetries = 3;`, `enum class Status { kOk, kFailed };`).

## 4. Modern Language Features & Safety
- **Enums**: Always use scoped enums: `enum class Color { kRed, kBlue };`.
- **Auto**: Use `auto` when the type is repeated in the initialization (`auto ptr = std::make_unique<T>();`) or for complex iterator types; avoid `auto` where it hides fundamental semantics.
- **Const Correctness**:
  - Mark member functions `const` if they do not modify observable state.
  - Mark local variables `const` by default unless mutation is needed.
- **Constructors**: Explicitly mark single-argument constructors as `explicit` to prevent unintended implicit conversions:
  ```cpp
  class Buffer {
   public:
    explicit Buffer(size_t capacity);
  };
  ```
- **Virtual Functions**: Always use `override` on derived class overrides; use `final` when a class/method should not be further subclassed.

## 5. Verification & Tooling
- Always compile with strict warnings enabled:
  ```sh
  -Wall -Wextra -Wpedantic -Wconversion -Wshadow
  ```
- Format code using `.clang-format`:
  ```sh
  clang-format -i <file.cpp> <file.h>
  ```
- Run static analysis via `clang-tidy`:
  ```sh
  clang-tidy -p build/ <file.cpp>
  ```
