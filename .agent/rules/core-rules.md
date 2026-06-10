# Core Working & Engineering Principles

This rule defines the foundational coding ethics, response parameters, comment regulations, and engineering principles for this repository. It applies universally across all modules and applications.

## Response & Communication Constraints

- **Language of Instruction**: Keep agent instruction files (such as files in `.agent/rules/`) in English.
- **Language of Interaction**: Always use **Traditional Chinese with Taiwan terminology** for final user responses, developer-facing README files, architecture notes, user-facing documentation, commit messages, pull request descriptions, and necessary code comments or docstrings.
- **English Terminology**: Keep code identifiers, library names, protocols, and established technical terms in English unless there is a precise and common Taiwanese translation.
- **Concise Reasoning**: Keep internal reasoning concise and outcome-focused. Present conclusions, not hidden chain-of-thought.
- **No Emojis**: Do not use emojis in commit messages, pull request descriptions, code comments, filenames, or documentation.

## Core Working Rules

- **Atomic Changes**: Prefer one method, one behavior, or one responsibility per edit when practical.
- **Small Steps**: Work in small steps. Avoid broad rewrites unless the task genuinely requires them.
- **Verification**: Verify before and after changes. Confirm the current state before editing, then run the smallest meaningful validation after editing.
- **Simplicity (YAGNI)**: Prefer simple, direct solutions. Avoid speculative abstraction.
- **No Over-design**: Add abstraction only when it removes real complexity, protects a clear boundary, or follows an established local pattern.
- **Refactoring**: After implementing behavior, refactor the touched code to simplify it and remove unused or unnecessary code.

## AI Coding Workflow

- **Implementation Plans**: Before making non-trivial changes, produce a short implementation plan. The plan should list the intended behavior, files likely to change, validation steps, and known risks.
- **Autonomy & Limits**: When implementation discovers necessary follow-up edits not listed in the plan, the agent may proceed if they are direct consequences of the accepted behavior, such as DTO mappings, tests, exports, prompts, fakes, or documentation. The agent must pause for confirmation before changing public API scope, persistence schema, migrations, authorization, destructive behavior, endpoint count, ranking/pagination policy, or cross-boundary ownership.
- **Plan Preservation**: Do not save every exploratory plan. Preserve only accepted plans that have decision value, architectural impact, or review value.
- **Refactoring Boundary**: Separate refactoring from behavior changes when practical.
- **Scope Limitation**: Keep AI-generated changes small enough to review. Do not modify unrelated files.
- **Review Summary**: After editing, provide a review summary with changed files, behavior impact, risk areas, tests run, and manual QA steps when applicable.
- **Large Changes**: For large work, prefer stacked commits or stacked pull requests over one large diff.
- **Zero Blind Trust**: Treat generated code as untrusted until it has been reviewed, tested, and validated.

## Comment and Documentation Rules

- **Self-Documenting Code**: Write self-documenting code. If code is unclear, first improve naming, structure, or extraction before adding comments. Prefer clear names, focused functions, explicit types, and tests over comments.
- **Strictly No Boilerplate**: Strictly avoid boilerplate, empty, or obvious module-level and class-level docstrings (such as `"""Domain entities."""`, `"""Application use cases."""`, or docstrings that merely rephrase the filename/classname). Docstrings are discouraged unless they document non-obvious domain rules, complex constraints, or architectural invariants.
- **Comment Language**: Keep rule files in English, but write necessary code comments and docstrings in Traditional Chinese with Taiwan terminology.
- **No Redundant Comments**: Do not add comments or docstrings that merely restate the class name, method name, parameters, return type, framework role, or obvious code behavior.
- **No Body Comments**: Avoid inline comments inside method bodies unless they explain non-obvious intent, business rules, tradeoffs, performance considerations, security constraints, compatibility constraints, or workarounds.
- **Prefer Better Code First**: If a clearer name, smaller function, explicit type, or focused test can express the intent, use that instead of adding a comment.
- **Test Comment Scope**: For tests, docstrings are completely discouraged. Do not write test docstrings unless the test crosses boundaries, uses live infrastructure, preserves a regression, or the scenario is not obvious from the test name.
- **Up-to-Date Documentation**: When a comment becomes outdated or unnecessary, update it or remove it in the same change.

## Engineering Principles

### Clean Code
- Use names that reveal intent and match the domain language.
- Keep functions, methods, and components focused on one responsibility.
- Prefer explicit control flow and clear data structures over cleverness.
- Avoid hidden side effects. Make dependencies and state transitions visible.
- Keep public APIs small, stable, and easy to reason about.

### Domain-Driven Design (DDD)
- Model the domain using ubiquitous language from the bounded context.
- Keep domain logic independent from frameworks, databases, transport, and external services.
- Use aggregates, entities, value objects, domain services, and domain events only when they clarify real domain behavior.
- Put use case orchestration in the application layer.
- Put persistence, messaging, HTTP clients, SDKs, and external systems in the infrastructure layer.
- Put HTTP, CLI, UI, and transport concerns in the presentation layer.
- Do not let infrastructure or presentation details leak into domain models.

### Test-Driven Development (TDD)
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
- Keep the pattern's purpose visible through naming and tests.

### Extreme Programming (XP)
- Make the smallest change that proves the behavior.
- Keep feedback loops short through focused tests and targeted validation.
- Prefer pairable, readable code over clever code.
- Keep documentation close to decisions, boundaries, and workflows.
