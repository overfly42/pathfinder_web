# Backend build-out roadmap

Sequencing plan for turning the mock endpoints in `backend/app/main.py` and the
frontend-only `AppStateContext` state into a real, database-backed system. See
`todos.md` for the current endpoint-by-endpoint status; this document is the
*order* in which that gap gets closed, not a replacement for that inventory.

## Guiding decisions

- **Vertical slices, not horizontal layers.** Never "stub every endpoint, then
  swap the whole UI, then add the database, then add logic." Each slice below
  goes UI → schema → backend → database → tests, for one feature, before
  moving to the next.
- **Ordered by the character lifecycle**: user → character creation → items →
  effects → possible actions → level-up. This lets each slice double as an
  automated end-to-end test scenario (create user → create character → equip
  item → apply effect → level up → assert state).
- **Thin pass first, thick pass later, per stage.** Every lifecycle stage
  below is split into a minimal "thin" version (prove the full stack works)
  and one or more "thick" follow-up iterations (add rule depth). No stage is
  a single atomic slice — "character creation" and "level-up" in particular
  are each their own multi-iteration mini-roadmap.
- **Reference data stays in JSON fixtures** (`backend/app/fixtures/*.json`)
  through all of the slices below. Migrating races/classes/feats/spells/
  items/effects into the database is deliberately its own later slice (#9),
  done once the schemas that consume this data have stabilized — not
  designed speculatively now.
- **Shared modifier/bonus-stacking design**: items and effects are both
  fundamentally "things that apply modifiers to character stats." Design
  that mechanism once, in slice 5 (Items), and reuse it in slice 6 (Effects)
  rather than building two separate systems.

## Foundation (one-time, not a lifecycle stage)

- [ ] PostgreSQL via `docker-compose` (matches the target architecture in
      `readme.md`). Add the vector extension later, only when something
      actually needs it (e.g. compendium search) — not upfront.
- [ ] SQLAlchemy + Alembic for models and migrations.
- [ ] Schema conventions: UUID primary keys (matches the ER diagram in
      `readme.md`), English table/column names (`requirements_v2.md` §5),
      timestamps on mutable rows for future history/audit needs.
- [ ] `apiPost` / `apiPatch` / `apiDelete` in `frontend/src/api/client.ts`
      (currently `apiGet`-only).
- [ ] First pytest integration test harness (FastAPI `TestClient` + a test
      Postgres instance). A handful of Playwright E2E tests cover the
      lifecycle golden path later; per-feature testing is pytest-level.

## Slices

### 1. User lifecycle (thin only)
Cheapest slice — proves the whole pattern before harder ones.
- [ ] `users` table.
- [ ] `POST /api/users`, `GET /api/users`, `PATCH /api/users/{user_id}`.
- [ ] Wire `AppHeader`'s user picker and "+ Neuer Nutzer" form to these
      endpoints instead of `AppStateContext` local state.

### 2. Character creation — thin
- [ ] Minimal `characters` table: name, user_id, race_id, class_id, level
      fixed at 1, hit_points. Race/class data still comes from fixtures.
- [ ] `POST /api/characters`, `GET /api/characters/{id}`,
      `PATCH /api/characters/{id}`, `DELETE /api/characters/{id}`.
- [ ] Creation wizard's `SummaryStep` actually persists the character instead
      of showing a mock confirmation banner.

### 3. Character creation — thick (its own iterations, not one lump)
- [ ] Ability scores / point-buy.
- [ ] Skills.
- [ ] Feats.
- [ ] Traits.
- [ ] Starting spellbook/known spells.
- [ ] Deliberately deferred further: alternate racial traits and
      archetype-conflict checking (needs a data-model decision on which
      archetypes/traits mutually exclude each other — not yet made).

### 4. Items / Inventory
- [ ] Gear table + equipment slots.
- [ ] `POST /api/characters/{id}/gear`, `PATCH .../gear/{item_id}`,
      `DELETE .../gear/{item_id}`, `PUT .../slots/{slot_id}`.
- [ ] Decide the shared modifier/bonus-stacking design here (see Guiding
      decisions above); reused by Effects in slice 5.
- [ ] AC recompute can stay a stub (store equipped state only); real AC
      computation is a thickening pass once the modifier design exists.

### 5. Effects / Conditions / Time
- [ ] Active-effects table with duration tracking.
- [ ] Activate/deactivate/custom-effect/advance-time/rest endpoints.
- [ ] Reuse the modifier design from slice 4 rather than inventing a second
      one.

### 6. Possible actions / legality checks
- [ ] Scope narrowly first: e.g. "can this spell be prepared/cast right
      now," "does this feat's prerequisites check out" — as checks added to
      existing endpoints, not a new generic legality framework.
- [ ] Depends on slices 3 (feats/spells data) and 5 (effects) being at least
      thin-complete.

### 7. Level-up — thin then thick
- [ ] Thin: single-class HP/BAB/save progression only.
- [ ] Thick: feat/skill/spell choices, multiclassing, archetypes, fighter
      bonus feat, history log (`character_levels`, `history` tables).
- [ ] `POST /api/characters/{id}/level-up`, `GET /api/characters/{id}/history`.
- [ ] Wire `LevelUpWizardPage` to the real endpoint instead of only writing
      to `AppStateContext`.

### 8. Reference-data migration (later, not upfront)
- [ ] Move races/classes/feats/spells/items/effects from JSON fixtures into
      database tables + seed scripts, once the schemas from slices 1–7 have
      stabilized against real usage.

## Explicitly out of scope here

Already tracked/deferred elsewhere in `todos.md`: localization content
(DE/EN), auth/login flow, GM view, full-text compendium search.
