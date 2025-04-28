# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Behavior
- Work on one file at a time
- Stay focused on one thing at a time.
- Before taking action
  - articulate what you want to do & why.
  - prompt the user for feedback first.
- Consult the README for an overview on the project
- Focus on helping the user develop their project
- Do not attempt to run the project, test the project or any other daemon or service.

## Code Style Guidelines
- **Style & Formatting**: declarative; condensed; readable
- **Indentation**: 2 spaces (no tabs)
- **Typing**: Pydantic; typehints
- **Naming**:
  - Classes: PascalCase
  - Functions/Variables: snake_case
  - Constants: UPPERCASE
- **Imports**:
  - `import` statements: `import foo, bar, baz`
  - `import from` statements: `from foo import *` or `from bar import hello, world`
- **Error Handling**: Use specific exception types with descriptive messages
- **Documentation**: Describe WHAT & WHY; use docstrings for functions/classes; include comprehensive inline comments.

## Architecture
- ASGI (FastAPI/Uvicorn) Gateway for OpenAI API
- Pydantic models for request/response validation
