# .NET Development Rules

This rule enforces coding styles, solution management, and architecture guidelines for .NET (C#) development in this repository.

## .NET Core Rules & Architecture

- **Separation of Concerns**: Keep domain, application, infrastructure, and presentation responsibilities separated.
- **Dependency Flow**: Do not let the domain layer depend on application, infrastructure, or presentation layers.
- **Dependency Injection**: Prefer constructor injection and avoid service locator patterns.
- **Thin Handlers**: Keep controllers, endpoints, command handlers, and hosted-service entrypoints thin and free of business logic.
- **Naming Conventions**: 
  - Prefer `PascalCase` for types and methods.
  - Suffix asynchronous methods with `Async`.
  - Use `_camelCase` for private fields.
  - Prefix interfaces with `I`.
- **DTOs and Values**: Prefer C# `record` types for DTOs and value objects when appropriate.
- **Modern C#**: Use modern C# features such as pattern matching when they improve clarity.
- **Nullable Context**: Enable and respect nullable reference types.
- **Async Execution**: Do not block on async work with `.Result` or `.Wait()`.
- **Query Boundaries**: Be explicit about query boundaries to avoid LINQ performance issues such as N+1 queries.
- **Error Boundaries**: Prefer centralized exception handling for app boundaries.

## Monorepo & Solution Management

- **Workflow Bounds**: Treat a solution file (`.sln`) as a developer workflow boundary, not as a domain boundary.
- **Scoped Solutions**: 
  - A deployable app may have its own solution file near the app when that keeps local build and test commands focused.
  - A package or library may have its own solution file when it is developed, tested, or versioned independently.
- **Root Solutions**: A root or integration solution may reference multiple apps and libraries when cross-project validation is useful.
- **Reference Rules**: Keep project references aligned with monorepo dependency direction: apps may reference libraries, but libraries must not reference apps.
- **Sharing Code**: Share code through libraries under `packages/` or through explicit service contracts, not through app internals.
- **Dependency Acyclicity**: Keep dependency direction explicit and acyclic.

## Library Rules (Under `packages/`)

- **API Limits**: Keep public APIs intentional and small.
- **Encapsulation**: Do not expose internals only because another app needs a shortcut.
- **Independence**: Keep domain libraries independent from ASP.NET Core, databases, SDKs, queues, and transport concerns.
- **Abstraction**: Prefer interfaces or ports when infrastructure is supplied by an app.
- **Verification**: Add tests that cover public behavior and domain rules.

## API Rules

- **Thin Presentation**: Keep controllers or endpoints thin and free of business logic.
- **REST Paths**: Prefer lowercase plural nouns in paths and kebab-case path segments.
- **HTTP Verbs**: Use `GET`, `POST`, `PUT`, `PATCH`, and `DELETE` according to standard REST semantics.
- **Structured DTOs**: Prefer explicit request and response DTOs.
- **JSON Contracts**: Prefer `camelCase` JSON response properties unless an existing contract requires otherwise.
- **Exception Mapping**: Prefer centralized exception handling that returns RFC 7807 Problem Details for JSON APIs. Do not return infrastructure exceptions directly to clients.
- **Input Validation**: Validate input at the boundary and express failures consistently.

## Worker & Console Rules

- **Thin Entrypoints**: Keep entrypoints thin and move orchestration into application services.
- **Explicit Schema**: Make command, job, and message contracts explicit.
- **Idempotency**: Design retries to be idempotent where practical.
- **Logging Failures**: Record failure reasons instead of silently swallowing exceptions.
- **Observability**: Keep long-running processing observable through structured logs, run status, metrics, or audit records.

## Testing

- **Scope**: Cover domain rules, application use cases, endpoint/job behavior, permissions, validation, failure handling, and boundary contracts.
- **Integration Tests**: Use integration tests for database, messaging, authentication, or external contract behavior when relevant.
- **Stack**: Use xUnit, FluentAssertions, and NSubstitute when the local project follows that stack.
- **Validation**: Run the smallest meaningful local validation before finishing.
