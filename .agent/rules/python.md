# Python Development Rules

This rule enforces coding styles, tools, and architectures for Python development in this repository.

## Python Tooling & Package Management

- **Dependency Management**: Use `uv` for dependency management, environment synchronization, and command execution.
- **No Direct Pip**: Do not use standalone `pip install` in project workflows.
- **Run Via UV**: Prefer running Python commands through `uv run`.
- **pyproject.toml**: Define project dependencies in `pyproject.toml`.
- **Workspace Bounds**: Treat a uv workspace as a Python dependency-management boundary, not as a domain boundary.
- **Independent Package Dependencies**: Keep each workspace member's dependencies declared in its own `pyproject.toml`. Use workspace dependencies for local references (`workspace = true` in `tool.uv.sources`).
- **No Internal Overreach**: Do not use workspace membership as a reason to import another package's internals.

## Layout & Typing

- **Folder Layout**: Prefer `src/` layout for apps and packages unless the local project has a clear reason otherwise.
- **Virtual Environment**: Assume the project virtual environment lives at `.venv` unless specified otherwise.
- **Type Hints**: Add type hints to function parameters and return values. Prefer concrete modern annotations such as `list[str]` and `dict[str, int]`.
- **Data Models**: Use Pydantic models for DTOs, structured request/response data, job payloads, extracted data, and external contracts when schemas are required.
- **No Untyped Dictionaries**: Avoid passing untyped dictionaries across application boundaries.
- **Dependency Injection**: Prefer explicit dependency injection over instantiating important dependencies deep inside handlers or jobs.

## Python DDD Project Structure

Use this structure as the default for Python DDD projects. Create only the layers that apply to the local project.

- `domain`: domain models, value objects, domain services, domain events, and domain errors.
- `use_cases`: application behavior and orchestration.
- `interfaces`: external capabilities required by use cases, defined as protocols or abstract contracts.
- `contracts`: stable DTOs, commands, results, event payloads, or integration schemas.
- `infrastructure`: database, LLM, vector store, object storage, queue, HTTP client, and SDK implementations.
- `presentation`: FastAPI routes, CLI commands, worker entrypoints, and request/response mapping.

### Dependency Direction Constraints

```text
presentation -> use_cases
infrastructure -> interfaces / domain / contracts
use_cases -> domain / interfaces / contracts
interfaces -> domain / contracts
domain -> no project layer dependency
```

## Package Rules (Under `packages/`)

- **Intentional API**: Keep the public API intentional and documented through names, tests, and examples.
- **No Downward Dependencies**: Do not depend on apps.
- **Framework Independence**: Keep domain packages independent from frameworks, databases, queues, SDKs, and transport concerns.
- **Ports & Adapters**: Prefer protocols, interfaces, or ports when the package must interact with infrastructure supplied by an app.
- **No Cycles**: Keep dependency direction explicit and acyclic.

## API & Service Rules

- **Thin Handlers**: Keep route or endpoint handlers thin and free of business logic.
- **Organized Routes**: Keep route definitions out of a monolithic `main.py` when the service grows beyond trivial size.
- **Structured Contracts**: Define explicit request and response models when the framework and codebase support them.
- **Boundary Validation**: Validate input at the boundary. Use framework exceptions or centralized exception handlers for transport failures.
- **RFC 7807**: Prefer RFC 7807 Problem Details for JSON API errors when practical.
- **No Transport Leaking**: Do not let FastAPI or transport concerns leak into domain models or application use cases.

## Worker / Pipeline Rules

- **Explicit Contracts**: Make job input and output contracts explicit.
- **Clear Separation**: Keep orchestration in the application layer and infrastructure integrations in adapters.
- **Idempotency**: Design retries to be idempotent where practical.
- **Exception Logging**: Record failure reasons instead of silently swallowing exceptions.
- **Observability**: Keep long-running processing observable through structured logs, run status, metrics, or audit records.
- **Data Provenance**: Preserve source evidence, provenance, validation status, and conflict information when processing extracted or generated data.
- **Process Separation**: Separate parsing, extraction, validation, transformation, and persistence steps when that improves readability or testability.

## LLM & AI Service Rules

- **Infrastructure Layer**: Treat model calls, embedding providers, vector stores, document parsers, and external APIs as infrastructure adapters.
- **Testable Prompting**: Keep prompts, schemas, validation, and retry policies explicit and testable.
- **Provenance**: Store provenance, evidence, validation status, and conflict information when behavior depends on generated outputs.
- **No Blind Trust**: Do not treat model confidence text as authoritative without independent validation.

## Testing

- **Framework**: Prefer pytest function tests, fixtures, and fakes over `unittest.TestCase` unless the local test suite already standardizes on `unittest`.
- **Execution**: Use `uv run pytest` for test execution.
- **Coverage**: Cover domain logic, use case behavior, endpoint or job behavior, permission rules, validation, failure handling, idempotency, and boundary contracts.
- **Contract Tests**: Add contract tests when downstream apps depend on stable behavior.
- **Incremental Validation**: Run the smallest meaningful local validation before finishing.
