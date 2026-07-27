# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pathfinder 1e web app for character creation, leveling, and play. Designed to run **local-only** (no hosted deployment), so there is intentionally no authentication in the MVP — the data model should still allow adding auth later without a redesign. The UI must support German (default) and English.

Full functional scope: `requirements_v2.md`. Architecture and entity/ER details: `readme.md`.

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
- `readme.md` — architecture and architecture decisions, including the entity-relationship model (Mermaid ER diagram).
- `requirements_v2.md` — current functional requirements (core features, multiclass calculation, spellcasting rules by caster type, equipment/lore, MVP scope/checklist).
- `todos.md` — central open-items list: unresolved architecture/requirements decisions (from the `requirements_v2.md` §8 checklist) plus the gap analysis of the three mock files against `requirements_v2.md` (what's missing or inconsistent in the mocks). Check here before assuming a decision (e.g. tech stack, localization approach) is final. Supersedes the former `offene_punkte_ui_mocks.md`, which was merged into it.
- `roadmap.md` — the sequencing plan for the backend/database build-out: lifecycle-ordered vertical slices (user → character creation → items → effects → actions → level-up), each split into a thin pass then thick passes. Check here before starting backend work to see what slice comes next; `todos.md` remains the endpoint-by-endpoint status inventory.
- `.claude/agents/code-improver.md` — custom subagent for readability/maintainability/performance passes, scoped to this project's current mockup stage vs. target architecture.
- `requirements.txt` — Python dependencies for tooling around the mocks (currently `playwright` + `pytest-playwright`, used to drive/screenshot the mock HTML files for verification). Not app dependencies — there is no Python application code yet.

## Commands

No build, lint, or test tooling exists yet for the app itself. To view a mockup, open the HTML file directly in a browser (e.g. `pathfinder-mock.html`); there is no dev server.

For browser automation (e.g. driving a mock with Playwright to verify a change), use the project's dedicated venv rather than installing packages elsewhere:

```bash
source ~/python/pathfinder_web/bin/activate
pip install -r requirements.txt   # first time / after requirements.txt changes
playwright install chromium       # first time, downloads the browser binary
```

This venv is intended to be used for the whole project going forward, not just Playwright.

## Working Conventions

- Only currently relevant rule elements (classes, feats, spells, etc.) should be shown or loaded — do not front-load the full ruleset "for completeness."
- Rules content (classes, feats, spells, prerequisites) is meant to become data-driven/extensible once the backend exists, not hard-coded — flag hard-coded rule logic that should live in data instead.
- Diagrams in this repo use Mermaid syntax (see the ER diagram in `readme.md`). `.github/instructions/mermaid.instructions.md` documents a GitHub Copilot/VS Code Mermaid-extension workflow (`mermaidChart.*` commands) that is not available to Claude Code — keep new diagrams in plain Mermaid syntax instead of relying on that tooling.
- When a conversation surfaces information relevant to this project (a decision, a requirement clarification, a design rationale, a newly found gap) that isn't yet captured anywhere, ask the user whether it should be added to one of the relevant files — `CLAUDE.md`, `requirements_v2.md`, `readme.md`, or `todos.md` — rather than letting it live only in the conversation.
