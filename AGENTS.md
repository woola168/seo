# AGENTS.md

This file is the primary instruction entrypoint for Codex in this repository.
It defines shared engineering rules for a polyglot monorepo. Framework-specific
rules should live in local `AGENTS.md` files close to the code they govern.

## Instruction Scope

- Root `AGENTS.md` applies to the entire repository.
- Add a local `AGENTS.md` when an app, package, worker, or service introduces stack-specific rules.
- Local `AGENTS.md` files should describe the local bounded context, technology stack, dependency boundaries, and validation commands.
- Use `docs/architecture/agent-templates/` as the source for local `AGENTS.md` templates.
- Do not name apps or packages after their implementation technology. Prefer capability or product names such as `admin-portal`, `identity-api`, `ingestion-api`, or `pipeline-worker`.
- Use `AGENTS.override.md` only when a directory must replace normal inherited rules instead of extending them.

## Core Working Rules

- Keep agent instruction files, including `AGENTS.md` and `docs/architecture/agent-templates/*.AGENTS.md`, in English unless the user explicitly asks otherwise.
- Use Traditional Chinese with Taiwan terminology for final user responses, developer-facing README files, architecture notes, user-facing documentation, commit messages, pull request descriptions, and necessary code comments or docstrings.
- Keep code, identifiers, library names, protocols, and established technical terms in English unless there is a precise and common Taiwanese translation.
- Keep internal reasoning concise and outcome-focused. Present conclusions, not hidden chain-of-thought.
- Make atomic changes. Prefer one method, one behavior, or one responsibility per edit when practical.
- Work in small steps. Avoid broad rewrites unless the task genuinely requires them.
- Verify before and after changes. Confirm the current state before editing, then run the smallest meaningful validation after editing.
- Do not use emojis in commit messages, pull request descriptions, code comments, filenames, or documentation.
- Prefer simple, direct solutions. Follow YAGNI and avoid speculative abstraction.
- Do not over-design. Add abstraction only when it removes real complexity, protects a clear boundary, or follows an established local pattern.
- After implementing behavior, refactor the touched code to simplify it and remove unused or unnecessary code.

## Comment and Documentation Rules

- Write self-documenting code. If code is unclear, first improve naming, structure, or extraction before adding comments.
- Prefer clear names, focused functions, explicit types, and tests over comments for describing normal behavior.
- Strictly avoid boilerplate, empty, or obvious module-level and class-level docstrings (such as `"""Domain entities."""`, `"""Application use cases."""`, or docstrings that merely rephrase the filename/classname). Docstrings are discouraged unless they document non-obvious domain rules, complex constraints, or architectural invariants.
- Do not add comments or docstrings that merely restate the class name, method name, parameters, return type, framework role, or obvious code behavior.
- Avoid inline comments inside method bodies unless they explain non-obvious intent, business rules, tradeoffs, performance considerations, security constraints, compatibility constraints, or workarounds.
- If a clearer name, smaller function, explicit type, or focused test can express the intent, use that instead of adding a comment.
- For tests, docstrings are completely discouraged. Do not write test docstrings unless the test crosses boundaries, uses live infrastructure, preserves a regression, or the scenario is not obvious from the test name.
- When a comment becomes outdated or unnecessary, update it or remove it in the same change.

## Engineering Principles

### Clean Code

- Use names that reveal intent and match the domain language.
- Keep functions, methods, and components focused on one responsibility.
- Prefer explicit control flow and clear data structures over cleverness.
- Avoid hidden side effects. Make dependencies and state transitions visible.
- Keep public APIs small, stable, and easy to reason about.

### Domain-Driven Design

- Model the domain using ubiquitous language from the bounded context.
- Keep domain logic independent from frameworks, databases, transport, and external services.
- Use aggregates, entities, value objects, domain services, and domain events only when they clarify real domain behavior.
- Put use case orchestration in the application layer.
- Put persistence, messaging, HTTP clients, SDKs, and external systems in the infrastructure layer.
- Put HTTP, CLI, UI, and transport concerns in the presentation layer.
- Do not let infrastructure or presentation details leak into domain models.

### Test-Driven Development

- Prefer writing or updating tests around behavior before changing behavior when the expected behavior is clear.
- Use the red-green-refactor loop for non-trivial behavior changes.
- Keep tests focused on observable behavior, domain rules, use cases, permissions, validation, and failure handling.
- Avoid brittle tests that assert implementation details without protecting behavior.
- Use fakes or test doubles at boundaries where they improve speed and clarity.
- Add integration tests when behavior crosses module, service, storage, or transport boundaries.

### Design Patterns

- Use design patterns as vocabulary and structure, not as decoration.
- Prefer simple functions, explicit interfaces, and dependency injection before introducing heavier patterns.
- Do not introduce factories, strategies, mediators, repositories, or event buses without a concrete complexity they reduce.
- When a pattern is used, keep its purpose visible through naming and tests.

### Extreme Programming

- Make the smallest change that proves the behavior.
- Keep feedback loops short through focused tests and targeted validation.
- Prefer pairable, readable code over clever code.
- Keep documentation close to decisions, boundaries, and workflows.

## AI Coding Workflow

- Before making non-trivial changes, produce a short implementation plan.
- The plan should list the intended behavior, files likely to change, validation steps, and known risks.
- When implementation discovers necessary follow-up edits not listed in the plan, the agent may proceed if they are direct consequences of the accepted behavior, such as DTO mappings, tests, exports, prompts, fakes, or documentation. The agent must pause for confirmation before changing public API scope, persistence schema, migrations, authorization, destructive behavior, endpoint count, ranking/pagination policy, or cross-boundary ownership.
- Do not save every exploratory plan. Preserve only accepted plans that have decision value, architectural impact, or review value.
- Separate refactoring from behavior changes when practical.
- Keep AI-generated changes small enough to review.
- Do not modify unrelated files.
- After editing, provide a review summary with changed files, behavior impact, risk areas, tests run, and manual QA steps when applicable.
- For large work, prefer stacked commits or stacked pull requests over one large diff.
- Treat generated code as untrusted until it has been reviewed, tested, and validated.

## Review Rules

- Review behavior, correctness, and risk before style.
- Prioritize bugs, regressions, unclear behavior, missing validation, missing tests, security issues, and data-loss risks.
- Require clear test evidence for behavior changes.
- For large diffs, ask for the change to be split by responsibility before reviewing details.
- High-risk areas require careful human review: authentication, authorization, payments, database migrations, concurrency, secrets, production configuration, destructive operations, and external integrations.
- A pull request should explain what changed, why it changed, how it was validated, and how to roll back if needed.

## Monorepo Rules

- The repository is the source-of-truth for product code, shared contracts, documentation, and deployment wiring.
- `apps/` contains deployable or runnable applications, such as web apps, APIs, workers, CLIs, and jobs.
- `packages/` contains reusable libraries, domain modules, shared contracts, and independently testable capabilities.
- `tests/` contains cross-app, cross-package, integration, contract, and end-to-end tests. Local unit tests may live near the app or package they validate.
- `deploy/` contains deployment and runtime composition files. Do not store secrets.
- `tools/` contains repository automation scripts. Do not put product business logic there.
- `docs/architecture/` contains architecture decisions, structure guidance, and system design notes.
- `docs/architecture/agent-templates/` contains local `AGENTS.md` templates for new apps and packages.
- A change that touches shared contracts must update affected apps, packages, tests, and documentation in the same change.
- Avoid direct imports across apps. Share code through packages or explicit service contracts.
- Packages should expose intentional public APIs. Apps should not depend on package internals.
- Keep dependency direction explicit and acyclic.

## Git / Commit / Pull Request Rules

- Use branch names in `type/description` or `type/issue-id-description` format.
- Prefer these branch prefixes: `feat/`, `fix/`, `refactor/`, `docs/`, `test/`, `chore/`.
- Write commit messages in Traditional Chinese with Conventional Commits format: `type(scope): description`.
- Keep each commit focused on one logical change.
- Pull request descriptions should include summary, motivation, validation, risk areas, and rollback notes when relevant.
- Avoid large pull requests. Split by behavior, boundary, or reviewable responsibility.

## API and Error Handling Rules

- For API design, prefer lowercase plural nouns in paths and kebab-case segments.
- Use `GET`, `POST`, `PUT`, `PATCH`, and `DELETE` according to standard REST semantics.
- Prefer `camelCase` for JSON response properties unless the repository already enforces a different contract.
- Do not allow silent failures. Empty `catch` blocks are forbidden unless they log or intentionally translate the failure.
- Prefer RFC 7807 Problem Details for HTTP error responses when the project exposes JSON APIs.

## Security and Configuration Rules

- Do not store secrets in source control.
- Do not print secrets, tokens, credentials, personal data, or sensitive business data in logs.
- Validate inputs at system boundaries.
- Keep authorization checks close to protected use cases or resources.
- Prefer explicit allowlists over blocklists for sensitive operations.
- Treat migrations, destructive commands, and production configuration changes as high-risk changes that require extra validation.

## Local AGENTS.md Workflow

When creating a new app or package:

1. Name the directory by product capability or deployment purpose, not technology.
2. Copy the closest template from `docs/architecture/agent-templates/` into the new directory as `AGENTS.md`.
3. Fill in local context, ownership, architecture boundaries, and validation commands.
4. Keep only rules that apply to that directory.
5. Add or update tests before changing behavior when practical.

Recommended examples:

```text
apps/admin-portal/AGENTS.md
apps/identity-api/AGENTS.md
apps/ingestion-api/AGENTS.md
packages/knowledge-graph/AGENTS.md
packages/pipeline-contracts/AGENTS.md
```
