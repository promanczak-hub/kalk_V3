# Project Skills & AI Instructions (Kalk v3)

This document contains the core instructions and rules for developers and AI Agents (e.g. Gemini, Cursor, Copilot) working on the `kalk_v3` project. Please adhere strictly to these guidelines.

## 🐍 Environment & Tech Stack

- **Language**: Python 3.12+
  - _Must utilize new syntax:_ PEP 695 type aliases, f-string improvements.
- **Dependency Manager**: Poetry.
- **Environment**: Strict type hinting is mandatory. Use `typing` and `pydantic` for data models.
- **Frontend**: React 19, TypeScript, Vite, Tailwind CSS v4, MUI.

## ✨ Code Quality & Standards (Clean Code)

- **Style Guide**: Follow PEP 8 strictly.
- **Complexity**: Keep functions under 20 lines. If a function is longer, refactor and decompose it into smaller logical units.
- **Single Responsibility**: Each module/class must have only one reason to change.
- **Naming**: Use descriptive, intention-revealing names. Do NOT use generic names like `temp`, `data`, or `process_item()`.
- **DRY & YAGNI**: Don't over-engineer. Focus on current requirements while keeping code modular.
- **File Size**: No source file should exceed 200 lines. Split logic into sub-modules if it grows beyond this limit.

## 🛠️ Linting & Formatting

The backend uses a strict set of modern Python tools:

- **Formatter**: Use `black` and `isort`.
- **Linter**: Use `ruff` for all checks (replaces flake8, pylint).
- **Type Checking**: Use `mypy` in strict mode.
- **Constraint**: Before finishing a task, ensure the agent runs:
  ```bash
  poetry run ruff check .
  poetry run mypy .
  ```

## 🧪 Testing Strategy

- **Framework**: `pytest` with `pytest-asyncio` for async tasks.
- **Edge Cases**: Always include tests for:
  - Empty inputs (`None`, `[]`, `""`).
  - Boundary values (max/min integers, empty dictionaries).
  - Network/Timeout exceptions.
- **Coverage**: Aim for 90%+ coverage.
- **Mocks**: Use `pytest-mock` to isolate external dependencies (APIs, databases, GenAI).
- **Instruction**: When creating a new feature, ALWAYS generate a corresponding test file in the `tests/` directory.

## 🤖 Agent Behavior & Workflow

- **Plan First**: Before writing code, describe the planned architecture and file changes. Ask the user for approval.
- **Atomic Commits**: Suggest logical git commits for each completed sub-task.
- **No Hallucinations**: If a library or API is unknown, ask the user or search the documentation.
- **Refactoring**: If you see messy code in the project, suggest a refactor before adding new features.
- **Documentation**: Keep `README.md` and this `SKILLS.md` up-to-date with architectural decisions.
