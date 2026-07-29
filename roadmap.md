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
  through all of the slices below, with two exceptions: **races** were pulled
  forward into slice 2 as a real, normalized set of tables (see `readme.md`'s
  ER diagram — `BaseRace`, `BaseRaceAbility`, `RaceAbilityGrant`,
  `RaceAbilityReplacement`), because `characters.race_id` needs a real FK
  target from the start rather than a loose fixture-string reference; **classes**
  got a real `BaseClass` table in slice 3 for the same FK reason
  (`CharacterLevel.base_class_id`), and — unlike races — this was
  deliberately *not* kept identity-only: `BaseClass` also carries `hit_dice`
  and the `arch_class_of` self-FK (root class vs. archetype variant), by
  explicit decision that class is central/complex enough to warrant earlier
  DB investment than race, with more class-mechanical fields expected to
  migrate in over time. Skill points, class skills, and spell type still stay
  in `classes.json` for now. Migrating the rest of feats/spells/items/effects
  (and the remaining class content) into the database remains a later slice
  (#8), done once the schemas that consume this data have stabilized — not
  designed speculatively now.
- **Shared modifier/bonus-stacking design**: items and effects are both
  fundamentally "things that apply modifiers to character stats." Design
  that mechanism once, in slice 5 (Items), and reuse it in slice 6 (Effects)
  rather than building two separate systems.

## Foundation (one-time, not a lifecycle stage)

- [x] PostgreSQL via `docker-compose` (matches the target architecture in
      `readme.md`). Add the vector extension later, only when something
      actually needs it (e.g. compendium search) — not upfront. This machine
      has Podman, not Docker, so `docker-compose.yml` is run with
      `podman-compose` (installed via root `requirements.txt`); the compose
      file itself stays plain/portable.
- [x] SQLAlchemy + Alembic for models and migrations. Wired in
      `backend/app/db.py` + `backend/alembic/`; no revisions yet since no
      domain tables exist (that starts at slice 1).
- [x] Schema conventions: UUID primary keys (matches the ER diagram in
      `readme.md`), English table/column names (`requirements_v2.md` §5),
      timestamps on mutable rows for future history/audit needs. Implemented
      as `UUIDPrimaryKeyMixin`/`TimestampMixin` in `backend/app/models/base.py`.
- [x] `apiPost` / `apiPatch` / `apiDelete` in `frontend/src/api/client.ts`
      (currently `apiGet`-only).
- [x] First pytest integration test harness (FastAPI `TestClient` + a test
      Postgres instance). A handful of Playwright E2E tests cover the
      lifecycle golden path later; per-feature testing is pytest-level.
      `backend/tests/conftest.py` + `backend/tests/test_health.py` (backed by
      a new `GET /api/health` endpoint that round-trips a query through the
      real DB session) prove the harness end-to-end.

## Slices

### 1. User lifecycle (thin only)
Cheapest slice — proves the whole pattern before harder ones.
- [x] `users` table.
- [x] `POST /api/users`, `GET /api/users`, `PATCH /api/users/{user_id}`.
- [x] Wire `AppHeader`'s user picker and "+ Neuer Nutzer" form to these
      endpoints instead of `AppStateContext` local state. Character ownership
      (`characterOwners` in `AppStateContext`) stays local-only for now — the
      two fixture characters start unowned by any user until slice 2 adds a
      real `characters` table with a `user_id` FK.

### 2. Character creation — thin
- [x] Real `races` tables, normalized (no JSONB), covering composition/
      identity only — not computed effects (see the handler-registry pattern
      in `CLAUDE.md`): `BaseRace` (id, code, name, short_description);
      `BaseRaceAbility` as one shared, reusable catalog of abilities/traits
      (id, name, description only — e.g. Darkvision is one row shared by
      Dwarf and Half-Orc, not duplicated per race, and this includes ability-
      score bonuses like Human's "+2 to any attribute" — no separate
      modifier table, since even superficially flat bonuses turn out to have
      exceptions often enough that a growing pile of nullable condition
      columns isn't actually simpler than a handler function); `RaceAbilityGrant`
      join (race_id, ability_id, is_alternate) for which abilities a race has
      by default vs. as an optional pick; `RaceAbilityReplacement`
      (base_race_id, ability_id, replaces_ability_id) scoping alternate-trait
      swaps to one race. Per the rulebook, the "+2 to any attribute" ability
      is one shared row reused by Human/Half-Elf/Half-Orc, not three separate
      ones. Every ability's actual mechanical effect — flat or conditional —
      is resolved by a handler function keyed by the ability's own UUID, not
      by table columns: `backend/app/rules/race_abilities.py` defines a
      handful of literal, hand-frozen UUID constants (one per distinct
      ability-score bonus, e.g. `ABILITY_GE_PLUS2`) and a
      `HANDLERS: dict[UUID, Callable]` — select by id, call the function, get
      `(attribute, value)` back. These ids are the *only* link between that
      module and the seed data; nothing derives or hashes them.
      Seed data itself lives in `backend/app/fixtures/seed/` — one JSON file
      per table (`base_races.json`, `base_race_abilities.json`,
      `race_ability_grants.json`, `race_ability_replacements.json`),
      DB-shaped rather than frontend-shaped, every row carrying its own
      explicit `id`. The old frontend-shaped `backend/app/fixtures/races.json`
      is no longer read by any code (superseded, not deleted — kept only as a
      historical record of the original mock content). Loaded via
      `backend/app/seed/race_seed.py` (idempotent upsert-by-id — rerun any
      time with `python -m app.seed.race_seed`).
      Ability keys are now two-letter codes (`ST`/`GE`/`KO`/`IN`/`WE`/`CH`,
      not the old `sta`/`ges`/`kon`/`int`/`wei`/`cha`) — changed during this
      slice and propagated everywhere a key was hardcoded (fixtures, frontend
      `AbilityKey`, `backend/app/rules/race_abilities.py`).
- [x] Minimal `characters` table: name, user_id, race_id (real FK into
      `BaseRace`), class_name (string, not a FK — classes stay fixture-only;
      see Guiding decisions above), level fixed at 1, current_hit_points (nullable —
      no HP calculation exists yet, `classes.json` has no hit-die field to
      compute from; that's a slice 3 concern, not faked here).
- [x] `POST /api/characters`, `GET /api/characters/{id}`,
      `PATCH /api/characters/{id}`, `DELETE /api/characters/{id}`
      (`backend/app/routers/characters.py`; GET merges with the two existing
      mock-fixture character views in `main.py` rather than replacing them).
- [x] Creation wizard's `SummaryStep` actually persists the character instead
      of showing a mock confirmation banner. The created character now
      appears in the header's character picker (`GET
      /api/users/{user_id}/characters`, added once class storage made a
      freshly created character worth actually finding again). Selecting it
      on the main character sheet still shows a placeholder rather than a
      full sheet — that needs the sheet's full computed shape (later work,
      the "thick" pass).

### 3. Character creation — thick (its own iterations, not one lump)
- [x] Ability scores / point-buy. `characters` stores only the six base
      point-buy scores (`ability_score_st`..`ability_score_ch`), the
      point-buy budget, and (for races with a flex bonus) which attribute it
      was put on — never a computed total; race/item/spell modifiers stay
      applied at read time, same composition-vs-computation split as
      everything else (`CLAUDE.md`). Server validates spend against
      `point_buy_costs.json` and the chosen budget
      (`backend/app/rules/point_buy.py`), and that `flex_ability` is
      set/unset consistent with whether the race actually grants a flex
      bonus (`race_has_flex` in `backend/app/routers/races.py`). Wired end to
      end: `AbilitiesStep`'s point-buy UI already existed and now the wizard
      actually submits it (`CreationWizardPage.tsx`) instead of dropping it.
- [x] Class selection/storage, pulled forward ahead of Skills (which needs a
      class's `skillPointsBase`/`classSkills`) and ahead of its originally
      planned slice 7 (level-up) home, the same way races were pulled forward
      in slice 2. Real `BaseClass` table gives `CharacterLevel.base_class_id`
      a FK target; class rules content (skill points, class skills, spell
      type, archetype/option-group *definitions*) stays in `classes.json`,
      joined by name. `CharacterLevel` (id, character_id, level,
      base_class_id, hit_points) is one row *per character level* per
      `readme.md`'s ER diagram — history from the start rather than a
      `class_name`/`level` pair on `characters`, so multiclassing and future
      level-up need no schema redesign. `Character.level`/`Character.classes`
      are computed properties derived from these rows
      (`backend/app/models/character.py`), not stored columns. Seed data/
      script mirror `race_seed.py`: `backend/app/fixtures/seed/base_classes.json`
      + `backend/app/seed/class_seed.py` (`python -m app.seed.class_seed`).
      Explicitly **not** included here: HP-per-level computation (still
      blocked on `classes.json` having no hit-die field at the time — see the
      next bullet).
- [x] Archetype + class option-group persistence, plus `hit_dice` and favored
      class. By explicit decision, `BaseClass` gained `hit_dice` (int, e.g.
      12 for Barbar) and a self-referencing `arch_class_of` FK (null = root
      class; set = one archetype variant of exactly one parent), matching
      `readme.md`'s pre-existing ER diagram
      (`BaseClasses.arch_class_of`/`BaseClasses |o--o{ BaseClasses:has`).
      Archetype rows are seeded from `classes.json`'s `archetypes` arrays
      (skipping "Keiner") with fresh ids, `arch_class_of` = parent's id,
      `hit_dice` left `None` (resolved via `BaseClass.root`/
      `effective_hit_dice` instead of duplicating it).

      Which classes/archetypes a character has lives in a new
      `CharacterClass` table (`character_classes`: character_id,
      base_class_id, is_favored) — one row per class-or-archetype, since
      roots and archetypes already share the same `base_classes` catalog: a
      Fighter with one archetype is two rows (the Fighter root row and the
      archetype row), so any number of simultaneous archetypes per class
      "just works" with no nested table. `is_favored` only applies to root
      rows and defaults to the first submitted class being favored; nothing
      computes a favored-class bonus yet (forward-looking data — Half-Elf's
      two-favored-classes rule isn't automated either). Whether two chosen
      archetypes actually *conflict* is still unsolved — this makes storing
      several possible, not validated; still the same open item in
      `todos.md` (no conflict-checking metadata in `classes.json`).

      `CharacterLevel.base_class_id` **always** points at the root class now
      (never an archetype row) — archetype selection lives once per
      class-taken in `CharacterClass`, not per level, so a level-up only
      ever needs to record the base class, and there's no possibility of
      "different archetype at a later level of the same class" to guard
      against (an earlier version of this pass added exactly that
      consistency check; removed once archetype selection moved out of
      `CharacterLevel`).

      `POST /api/characters`'s `classes` rows now carry `archetypes:
      list[str]` and `options: dict[str, list[str]]` (domain/bloodline/
      mystery/school/favored-enemy-terrain/... choices, validated against
      that class's `optionGroups` in `classes.json`); `resolve_root_class`/
      `resolve_archetype`/`_validate_options`
      (`backend/app/routers/characters.py`) resolve and validate them,
      written so a future real level-up endpoint (slice 7) can reuse the
      root resolver per new level rather than only at creation. Option-group
      choices land in `CharacterClassOption` (character_id, base_class_id,
      group_key, choice — one row per chosen value, so a max-2 group like
      Kleriker's domains is two rows), keyed by the root class's id.
- [ ] Skills, including racial skill bonuses (e.g. Elf's +2 Knowledge
      (arcana)). Once skill totals actually need to sum these, resolve them
      via the same handler-registry pattern as ability-score bonuses
      (`CLAUDE.md`) — no separate modifier table.
- [ ] Feats.
- [ ] Traits, including persisting a character's chosen alternate racial
      traits — the schema for this exists as of slice 2
      (`RaceAbilityGrant`/`RaceAbilityReplacement`), so this is wiring, not a
      new data-model decision.
- [ ] Starting spellbook/known spells.
- [ ] Deliberately deferred further: archetype-conflict checking for
      classes (needs a data-model decision on which archetypes mutually
      exclude each other — not yet made; the equivalent question for races
      was resolved in slice 2).

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
- [ ] Move classes/feats/spells/items/effects from JSON fixtures into
      database tables + seed scripts, once the schemas from slices 1–7 have
      stabilized against real usage. Races are already handled in slice 2.

## Explicitly out of scope here

Already tracked/deferred elsewhere in `todos.md`: localization content
(DE/EN), auth/login flow, GM view, full-text compendium search.
