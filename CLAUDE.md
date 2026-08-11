# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Pathfinder 1e web app for character creation, leveling, and play. Designed to run **local-only** (no hosted deployment), so there is intentionally no authentication in the MVP — the data model should still allow adding auth later without a redesign. The UI must support German (default) and English.

Full functional scope: `requirements_v2.md`. Architecture and entity/ER details: `readme.md`.

## Current State vs. Target Architecture

The three root-level `pathfinder-*-mock.html` files are the original static HTML/CSS/JS mockups and remain the reference design surface, but the real build-out has since started in `backend/` (FastAPI) and `frontend/` (React + Vite + TypeScript). See `roadmap.md` for what's been built (foundation + which lifecycle slices) versus what's still mock data/fixtures.

Target architecture:
- Frontend: React (`frontend/`, Vite + TypeScript) — in progress.
- Backend: FastAPI (`backend/`; owns character state/progression logic, exposes domain objects rather than raw rows, evaluates which actions/options are legal for a character's current state) — endpoints so far mostly read static JSON fixtures (`backend/app/fixtures/*.json`), not the database yet; see `roadmap.md`/`todos.md` for per-endpoint status.
- Database: PostgreSQL, via `docker-compose.yml` (`podman-compose up -d`, since this machine has Podman rather than Docker). SQLAlchemy + Alembic are wired (`backend/app/db.py`, `backend/app/config.py`, `backend/app/models/`, `backend/alembic/`), but no domain tables exist yet — that starts at roadmap slice 1 (users). Vector extension deliberately deferred until something needs it (e.g. compendium search).
- Deployment: Docker/Podman containers for backend + database (not set up yet — dev today runs both directly via `dev.sh`, only the database is containerized so far).

Do not migrate remaining mock behavior to the real stack as a side effect of unrelated work — each roadmap slice does that deliberately.

## Files

- `pathfinder-mock.html`, `pathfinder-character-creation-mock.html`, `pathfinder-levelup-mock.html` — the actual UI mockups (character sheet / character creation / level-up flow). Each is a single self-contained file with inline `<style>` and `<script>` (no shared `app.js`/`styles.css`, only a Google Fonts CDN link). This is the current living design surface.
- `readme.md` — architecture and architecture decisions, including the entity-relationship model (Mermaid ER diagram).
- `requirements_v2.md` — current functional requirements (core features, multiclass calculation, spellcasting rules by caster type, equipment/lore, MVP scope/checklist).
- `todos.md` — central open-items list: unresolved architecture/requirements decisions (from the `requirements_v2.md` §8 checklist) plus the gap analysis of the three mock files against `requirements_v2.md` (what's missing or inconsistent in the mocks). Check here before assuming a decision (e.g. tech stack, localization approach) is final. Supersedes the former `offene_punkte_ui_mocks.md`, which was merged into it. Closed items get periodically moved out to `todos_history.md` to keep this file focused on what's still open — check there for the full class-by-class/race-by-race reference-data verification log against `prd.5footstep.de`.
- `roadmap.md` — the sequencing plan for the backend/database build-out: a one-time Foundation (DB/ORM/migrations/test harness — done) followed by lifecycle-ordered vertical slices (user → character creation → items → effects → actions → level-up), each split into a thin pass then thick passes. Check here before starting backend work to see what slice comes next; `todos.md` remains the endpoint-by-endpoint status inventory. Fully completed slices/bullets get periodically moved out to `roadmap_history.md` (design rationale, implementation detail, per-class seeding history) so this file stays focused on the current frontier of work.
- `.claude/agents/code-improver.md` — custom subagent for readability/maintainability/performance passes, scoped to this project's current mockup stage vs. target architecture.
- `requirements.txt` — Python dependencies for tooling that isn't part of the app itself: `playwright`/`pytest-playwright` (drive/screenshot the mock HTML files) and `podman-compose` (bring up the database; see Commands below).
- `docker-compose.yml` — Postgres 16 service (`db`) for local dev. Run with `podman-compose` (see Commands).
- `backend/requirements.txt` / `backend/requirements-dev.txt` — FastAPI app dependencies (`fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `psycopg`, `pydantic-settings`); `-dev` adds `pytest`/`httpx` for the test harness.
- `backend/app/config.py`, `backend/app/db.py` — `Settings` (env-driven, defaults matching `docker-compose.yml`) and the SQLAlchemy engine/session/`get_db` dependency.
- `backend/app/models/` — `Base` plus `UUIDPrimaryKeyMixin`/`TimestampMixin`, the schema conventions every future table should use (UUID PKs, English names per `readme.md`/`requirements_v2.md` §5, timestamps on mutable rows).
- `backend/alembic/`, `backend/alembic.ini` — migrations, wired to `app.config.settings` and `app.models.Base.metadata`. No revisions yet (no tables yet).
- `backend/tests/` — pytest integration harness: `conftest.py` spins up a dedicated `<db>_test` Postgres database (auto-created, schema reset per session) and gives tests a rolled-back-per-test `db_session` and a `client` (FastAPI `TestClient` with `get_db` overridden).
- `frontend/src/api/client.ts` — `apiGet`/`apiPost`/`apiPatch`/`apiDelete` fetch helpers.
- `backend/scripts/` — one-off import scripts pulling rule data from the German PRD (`prd.5footstep.de`) into `backend/app/fixtures/imported/`, staging material for expanding the feat catalog and implementing `HANDLERS` one feat at a time. `backend/scripts/README.md` documents the site's data shapes (bulk JSON index vs. permalink-resolved full-text feat pages vs. prose-only class pages) and known quirks (duplicate index rows, display-name/canonical-name mismatches) — read it before writing another importer against this site.

## Commands

To view a *mockup* HTML file directly (no dev server needed), open it in a browser (e.g. `pathfinder-mock.html`).

To run the real app (frontend + backend + database) for local dev:

```bash
./dev.sh   # brings up Postgres via podman-compose, then FastAPI (reload) + Vite together
```

Manual equivalents, using the project's dedicated venv (`~/python/pathfinder_web`) rather than installing packages elsewhere:

```bash
source ~/python/pathfinder_web/bin/activate
pip install -r requirements.txt                    # playwright + podman-compose; first time / after changes
playwright install chromium                        # first time, downloads the browser binary
podman-compose up -d                                # Postgres, per docker-compose.yml

pip install -r backend/requirements-dev.txt         # backend app + test deps
cd backend && alembic upgrade head                  # apply migrations (no-op until slice 1 adds tables)
uvicorn app.main:app --reload --port 8000           # backend dev server
python -m pytest                                    # backend/tests, uses the <db>_test database

cd frontend && npm install && npm run dev           # frontend dev server
```

This venv is intended to be used for the whole project going forward, not just Playwright.

## Working Conventions

- Only currently relevant rule elements (classes, feats, spells, etc.) should be shown or loaded — do not front-load the full ruleset "for completeness."
- Rules content (classes, feats, spells, prerequisites, racial/class/item abilities) is meant to become data-driven/extensible once the backend exists, not hard-coded — flag hard-coded rule logic that should live in data instead. The data/code boundary is not "flat bonuses vs. special rules" — Pathfinder 1e's bonuses too often turn out to be conditional even when they look flat (e.g. Skill Focus: +3 normally, +6 once you have 10+ ranks), so a data table trying to cover every bonus shape ends up growing ad hoc condition columns per exception, which is worse than code: neither simple data nor flexible logic. The boundary instead is **composition vs. computation**:
  - What abilities/feats/spells/etc. *exist*, and what grants/replaces what (e.g. `BaseRaceAbility` catalog rows, `RaceAbilityGrant`, `RaceAbilityReplacement`) stays pure data — a character's relevant rule elements are just a set of UUIDs, discoverable and loadable without code. Adding a new race/feat/item that reuses existing abilities is a data/fixture change only.
  - *Computing* what an ability actually does — flat or conditional, "+2 Dex" or Skill Focus's threshold or Half-Orc Ferocity's fight-on-at-0-HP — is always resolved by a Python-side handler function, looked up by the ability/feat/spell's own UUID (`HANDLERS: dict[UUID, Callable]`) — no extra schema column needed, since the catalog row's `id` is already the key. Trivial cases (a flat attribute bonus) can share one generic handler factory parameterized per ability; this is still much less code than a modifier table plus the engine that reads it, and it never needs a migration when the next exception shape shows up.
- Handler files (`backend/app/rules/`) are organized by whichever axis is expected to grow large, not uniformly by mechanic family — this is a maintainability call, not a business one. Race abilities stay split by mechanic (`race_abilities.py` for ability-score bonuses, `speed.py` for base land speed): there are few races and their handlers are trivial one-liners, so one file per mechanic reads fine. Class abilities are split **one file per class** instead, under `rules/classes/` (e.g. `barbarian.py`), with closely related variants (a class and its unchained/archetype sibling) sharing a file: PF1e's ~40 classes/archetypes each have many individually complex features, so a single `class_abilities.py` (or splitting by mechanic the way races do) would grow without a natural seam. `rules/effects.py` stays the home for active effects that aren't tied to a single class (conditions, poisons, diseases). Apply the same reasoning — split by the domain entity, not the mechanic — to any other rule-element family that turns out to need many individually complex handlers (spells, feats, ...) once it actually gets there; don't split preemptively before a family shows that growth shape. Every source file's own `HANDLERS` slice merges into `rules/handlers.py`'s single registry (`rules/classes/__init__.py` merges its own class files first, so `rules/handlers.py` only imports one name per family, not one per class).
- Diagrams in this repo use Mermaid syntax (see the ER diagram in `readme.md`). `.github/instructions/mermaid.instructions.md` documents a GitHub Copilot/VS Code Mermaid-extension workflow (`mermaidChart.*` commands) that is not available to Claude Code — keep new diagrams in plain Mermaid syntax instead of relying on that tooling.
- When a conversation surfaces information relevant to this project (a decision, a requirement clarification, a design rationale, a newly found gap) that isn't yet captured anywhere, ask the user whether it should be added to one of the relevant files — `CLAUDE.md`, `requirements_v2.md`, `readme.md`, or `todos.md` — rather than letting it live only in the conversation.
