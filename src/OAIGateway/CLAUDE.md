# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Behavior
- Work on one file at a time
- Stay focused on one thing at a time.
- Before taking action
  - articulate what you want to do & why.
  - prompt the user for feedback first.

## Build/Run Commands
- Focus on helping the user develop their project
- Do not attempt to run the project or any other daemon or service.

## Testing
- No formal test harness present
- Manual verification using the API endpoints

## Code Style Guidelines
- **Indentation**: 4 spaces (no tabs)
- **Line Length**: ~80-100 characters
- **Type Hints**: Required for all function parameters and return values
- **Naming**:
  - Classes: PascalCase
  - Functions/Variables: snake_case
  - Constants: UPPERCASE
- **Imports**: Group by stdlib, third-party, internal
- **Error Handling**: Use specific exception types with descriptive messages
- **Documentation**: Use docstrings for functions/classes
- **Logging**: Use appropriate log levels (debug, info, warning, error)

## Architecture
- FastAPI-based service for OpenAI API Gateway
- Provider pattern for different backend services
- Pydantic models for request/response validation