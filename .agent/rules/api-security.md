# API Design & Security Rules

This rule enforces standards for REST API design, HTTP transport rules, error formatting, and security boundaries.

## API Design Rules

- **Path Naming**: Prefer lowercase plural nouns in paths and kebab-case segments (e.g., `/api/v1/user-profiles`).
- **REST Semantics**: Use HTTP methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) strictly in accordance with standard REST semantics:
  - `GET`: Retrieve representation. Safe and idempotent.
  - `POST`: Create resource or execute action. Not idempotent.
  - `PUT`: Replace resource entirely. Idempotent.
  - `PATCH`: Partially update resource. Non-idempotent (or conditionally idempotent).
  - `DELETE`: Remove resource. Idempotent.
- **Properties Naming**: Prefer `camelCase` for JSON response and request body properties unless the repository/existing service contract already enforces a different convention.
- **No Silent Failures**: Empty `catch` blocks are strictly forbidden. Always log exceptions or intentionally translate the failure to a domain-specific exception.

## Error Handling Standards

- **RFC 7807 Problem Details**: Prefer returning RFC 7807 Problem Details for all HTTP JSON API error responses when exposing JSON APIs.
- **No Raw Exceptions**: Do not expose raw infrastructure exceptions or stack traces directly to the API clients. Map technical exceptions to clean, localized API errors at the boundary.

## Security & Secrets Management

- **No Secrets in Source**: Never store secrets, API tokens, database credentials, certificates, or personal access tokens in source control. Use environment variables or secure vault integrations.
- **Privacy in Logs**: Do not print, output, or record secrets, access tokens, credentials, personal data (PII), or sensitive business data in application logs.
- **Boundary Validation**: Validate and sanitize all inputs at system boundaries (presentation layer, public APIs, message queues, file uploads).
- **Authorization Placement**: Keep authorization checks (RBAC/ABAC) close to protected application use cases or resource domains, preventing authorization bypass.
- **Allowlists Prefered**: Prefer explicit allowlists over blocklists for sensitive parameters, file types, and allowed network operations.
- **High-Risk Operations**: Treat database migrations, destructive operations, production configurations, and external vendor integrations as high-risk changes that require extra validation and manual checks.
