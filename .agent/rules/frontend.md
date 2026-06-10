# Frontend & UI Development Rules

This rule enforces coding styles, structure, and UI/UX design standards for frontend development (Vue / TypeScript) in this repository.

## Vue & TypeScript Coding Standards

- **Composition API**: Prefer Vue Composition API with `<script setup lang="ts">` unless the local codebase already uses another established pattern.
- **Component Focus**: Keep components focused on presentation and move reusable stateful logic into composables.
- **No Direct HTTP**: Do not call HTTP clients such as `axios` directly from view components when a service layer exists.
- **Composable Extraction**: If component logic becomes large or hard to scan, extract composables instead of growing a single file indefinitely.
- **Component Naming**: Prefer `PascalCase` for component filenames and exported component names.
- **TypeScript Usage**: Use TypeScript intentionally. Avoid `any` unless there is a documented reason that cannot be reasonably eliminated.
- **Props Definition**: Prefer explicit prop typing and defaults where appropriate.
- **Pinia Stores**: If the app uses Pinia, prefer setup stores (`defineStore('id', () => { ... })`) for consistency with composables.
- **Styles Scoping**: Prefer scoped component styles (`<style scoped>`) by default. Keep global styles limited to explicit shared style entrypoints.
- **CSS Architecture**: 
  - Use maintainable CSS naming, avoid deep selector chains, and avoid `!important` unless overriding third-party code is the only practical option.
  - Prefer CSS variables for shared colors, spacing, and typography tokens.
  - Avoid ad-hoc utility classes for styling. Follow a structured typography and layout token set.

## UI / UX & Aesthetics Guidelines

- **Product First**: Build the actual product experience first, not a marketing page, unless the task explicitly asks for a landing page.
- **Familiar Controls**: Keep controls familiar to users: icons for tool buttons, segmented controls for modes, toggles for binary settings, inputs or sliders for numeric values, and menus for option sets.
- **Efficiency**: Make common workflows efficient and complete for repeated use.
- **Responsiveness**: Ensure text does not overflow or overlap on desktop or mobile viewports.
- **Rich Aesthetics**: Interfaces should feel premium, sleek, and modern:
  - Avoid browser defaults; use curated modern typography (e.g., from Google Fonts like Inter, Roboto, or Outfit).
  - Use harmonious HSL tailored color schemes and sleek dark modes.
  - Implement smooth gradients, dynamic transitions, and subtle hover animations to make the application feel alive and responsive.
- **No Placeholders**: Never use generic placeholders for visual assets (e.g., images). Generate high-quality assets using image generation tools when building UI components that require visual context.

## Testing

- **Scope**: Cover behavior that affects routing, permissions, forms, state transitions, API integration, and user-visible workflows.
- **Behavior-Driven**: Prefer testing observable behavior over component internals.
- **Tools**: Use Vitest and Vue Test Utils for unit tests when the app follows that stack.
- **Validation**: Run the smallest meaningful local validation before finishing.
