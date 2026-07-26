# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pathfinder 1e web app for character creation, leveling, and play. Designed to run **local-only** (no hosted deployment), so there is intentionally no authentication in the MVP — the data model should still allow adding auth later without a redesign. The UI must support German (default) and English.

Full functional scope: `requirements_v2.md`. Architecture and entity/ER details: `readme.md`.

**Note:** `requirements.md` is an earlier draft superseded by `requirements_v2.md` (different structure, FR-numbered) — treat `requirements_v2.md` as current; confirm with the user before relying on `requirements.md`.

## Current State vs. Target Architecture

The code in this repo today is **static HTML/CSS/JS mockups only** — there is no build tooling (no `package.json`), no backend, and no database wired up yet.

Target architecture (planned, not yet implemented):
- Frontend: React
- Backend: FastAPI (owns character state/progression logic, exposes domain objects rather than raw rows, evaluates which actions/options are legal for a character's current state)
- Database: PostgreSQL with the vector extension
- Deployment: Docker/Podman containers for backend + database

Do not migrate the mockups to React as a side effect of unrelated work — that migration happens deliberately.

## Files

- `pathfinder-mock.html`, `pathfinder-character-creation-mock.html`, `pathfinder-levelup-mock.html` — the actual UI mockups (character sheet / character creation / level-up flow). Each is a single self-contained file with inline `<style>` and `<script>` (no shared `app.js`/`styles.css`, only a Google Fonts CDN link). This is the current living design surface.
- `index.html`, `app.js`, `styles.css` — an earlier, minimal prototype (simple tab-switching character sheet demo), separate from the three mocks above.
- `readme.md` — architecture and architecture decisions, including the entity-relationship model (Mermaid ER diagram).
- `Database.dia` — Dia diagram of the DB schema (companion to the ER diagram in `readme.md`).
- `requirements_v2.md` — current functional requirements (core features, spellcasting rules by caster type, MVP scope/checklist).
- `todos.md` — central open-items list: unresolved architecture/requirements decisions (from the `requirements_v2.md` §8 checklist) plus the gap analysis of the three mock files against `requirements_v2.md` (what's missing or inconsistent in the mocks). Check here before assuming a decision (e.g. tech stack, localization approach) is final. Supersedes the former `offene_punkte_ui_mocks.md`, which was merged into it.
- `.claude/agents/code-improver.md` — custom subagent for readability/maintainability/performance passes, scoped to this project's current mockup stage vs. target architecture.

## Commands

No build, lint, or test tooling exists yet. To view a mockup, open the HTML file directly in a browser (e.g. `pathfinder-mock.html`); there is no dev server.

## Working Conventions

- Only currently relevant rule elements (classes, feats, spells, etc.) should be shown or loaded — do not front-load the full ruleset "for completeness."
- Rules content (classes, feats, spells, prerequisites) is meant to become data-driven/extensible once the backend exists, not hard-coded — flag hard-coded rule logic that should live in data instead.
- Diagrams in this repo use Mermaid syntax (see the ER diagram in `readme.md`). `.github/instructions/mermaid.instructions.md` documents a GitHub Copilot/VS Code Mermaid-extension workflow (`mermaidChart.*` commands) that is not available to Claude Code — keep new diagrams in plain Mermaid syntax instead of relying on that tooling.
