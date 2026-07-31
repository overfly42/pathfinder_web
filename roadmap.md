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
  through all of the slices below, with three exceptions: **races** were
  pulled forward into slice 2 as a real, normalized set of tables (see
  `readme.md`'s ER diagram — `BaseRace`, `BaseRaceAbility`, `RaceAbilityGrant`,
  `RaceAbilityReplacement`), because `characters.race_id` needs a real FK
  target from the start rather than a loose fixture-string reference; **classes**
  got a real `BaseClass` table in slice 3 for the same FK reason
  (`CharacterLevel.base_class_id`), and — unlike races — this was
  deliberately *not* kept identity-only: `BaseClass` also carries `hit_dice`
  and the `arch_class_of` self-FK (root class vs. archetype variant), by
  explicit decision that class is central/complex enough to warrant earlier
  DB investment than race, with more class-mechanical fields expected to
  migrate in over time; and **skills** got real `BaseSkill`/`BaseClassSkill`
  tables, also in slice 3, so `classSkills` has a real FK target instead of
  fixture-key strings and skill names have a stable id a future translation
  layer can key off of (`name` stays a single unlocalized string for now —
  DE/EN is still an open item, see `todos.md`). Skill points, spell type, and
  archetype/option-group *definitions* still stay in `classes.json` for now.
  Migrating the rest of feats/spells/items/effects (and the remaining class
  content) into the database remains a later slice (#8), done once the
  schemas that consume this data have stabilized — not designed
  speculatively now.
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
- [x] Skills. Real `BaseSkill` (id, name, `ability` — the fixed 2-letter
      code, not a `BaseAttribute` FK; see Guiding decisions above) and
      `BaseClassSkill` (base_class_id, skill_id — replacing `classes.json`'s
      `classSkills: string[]` arrays, root classes only) tables, seeded from
      `backend/app/fixtures/seed/base_skills.json`/`base_class_skills.json`
      via `backend/app/seed/skill_seed.py` (same idempotent upsert-by-id
      pattern as `race_seed.py`/`class_seed.py`). `/api/skills`
      (`backend/app/routers/skills.py`) is now fully database-backed;
      `/api/classes` overwrites its `classSkills` field with real skill ids
      at read time, the rest of `classes.json` unchanged.

      What a character actually invested is `CharacterSkillRank` (level_id,
      skill_id, ranks) — an audit entry per `CharacterLevel`, not a running
      total (a character's current ranks in a skill is always `SUM(ranks)`
      across these rows, computed via `Character.skill_ranks`, never stored
      redundantly). Multi-level creation (the wizard doesn't ask which level
      a rank came from) collapses the whole selection onto the highest
      `CharacterLevel` row being created, as one row per skill touched; a
      later level-up (slice 7) will instead add one new row per skill tied
      to the new level, holding only that level's newly bought ranks — same
      table, same insert shape, just a smaller delta, so creation and
      level-up never need different persistence logic. Server-side
      validation (`backend/app/routers/characters.py`) mirrors the wizard's
      client-side math (`skillPointsTotal`/`skillBonus` in
      `creationCalculations.ts`): per-skill ranks capped at total character
      level, and total ranks capped at the skill-point budget computed from
      each class's `skillPointsBase` (`classes.json`) plus the character's
      *effective* INT modifier (base score + race flat bonus + flex pick,
      via the new `race_ability_score_mods` helper in `routers/races.py`).

      Racial skill bonuses (e.g. Elf's +2 Knowledge (arcana)) are not yet
      modeled — no such `BaseRaceAbility` rows exist in the seed data yet;
      when they're added, they resolve via the same handler-registry pattern
      as ability-score bonuses (`CLAUDE.md`), not a separate modifier table.
- [x] Feats. Real `BaseFeat` (id, name, description, `type` — a plain
      categorization tag like `BaseSkill.ability`, e.g. "combat"/"general",
      used both by prerequisite display later and today by the level-up
      wizard's fighter bonus-feat slot to filter to combat feats) plus six
      `BaseFeatRequired*` prerequisite tables (feat, skill, class level, class
      ability, race, ability score, BAB) from an earlier pass
      (`backend/app/models/feat.py`) — schema only, unused until this pass.
      Seed data now exists too: `backend/app/fixtures/seed/base_feats.json`
      (the 16 feats from the old `feats.json`, migrated to the DB-shaped id/
      name/description/type rows `BaseFeat` expects) via
      `backend/app/seed/feat_seed.py` (same idempotent upsert-by-id pattern as
      `skill_seed.py`). `/api/feats` (`backend/app/routers/feats.py`) is now
      fully database-backed, replacing the old fixture-reading mock endpoint
      in `main.py`.

      What a character actually took is `CharacterFeat` (level_id, feat_id) —
      same per-`CharacterLevel` audit shape as `CharacterSkillRank`, exposed
      as `Character.feat_ids` (flattened across all levels, never stored as
      its own list). `POST /api/characters`'s new `feat_ids: list[UUID]`
      field is validated server-side (`backend/app/routers/characters.py`):
      each id must exist in `base_feats`, and the count is capped by
      `backend/app/rules/feat_slots.py`'s `_feat_max` — base progression
      (`(total_level + 1) // 2`: 1st level, then every odd level after) plus
      bonus feat *slots* granted by race or class, resolved from real data
      rather than a hardcoded class name (an earlier version of this pass
      special-cased `class_name == "Kämpfer"`, which is wrong — Fighter isn't
      the only bonus-feat source in the core rules, and hardcoding one name
      would silently miss the rest). Race: whether the character's race has
      a non-alternate `RaceAbilityGrant` for the "Bonustalent" ability
      (Human's bonus feat at 1st level), minus a check that the character
      didn't trade it away via the "Bemerkenswerte Fertigkeit" alternate
      trait. Class: `BaseClassAbilityGrant` rows tagged as feat slots
      (`BONUS_FEAT_SLOT_ABILITY_IDS`, the same hand-frozen-UUID convention as
      `rules/race_abilities.py`), counted per class at `grant.level <=` that
      class's cumulative level (summed across non-contiguous selections of
      the same class first, since the grant's level is the class's own, not
      the character's). Today only Kämpfer's recurring bonus combat feat
      (1st, then every even level) is seeded this way: one shared
      `BaseClassAbility` catalog row ("Bonus-Kampftalent") granted via 11
      `BaseClassAbilityGrant` rows, one per granting level
      (`backend/app/fixtures/seed/base_class_abilities.json` +
      `base_class_ability_grants.json` via
      `backend/app/seed/class_ability_seed.py`) — `BaseClassAbilityGrant`'s
      unique constraint now includes `level` (migration `d925ead90c76`)
      precisely so the same ability can recur across levels instead of
      needing a near-duplicate catalog row per level. Adding another class's
      bonus feats later is a pure data change (seed rows + one more id in
      that set), not a new code path. `GET /api/classes` exposes each
      class's `bonusFeatLevels: number[]` (from the same grant data) so the
      frontend's `featMax` (`creationCalculations.ts`) can mirror this
      without its own class-name hardcoding either. Multi-level creation
      collapses feat picks onto the highest `CharacterLevel` row being
      created, same reasoning as `skill_ranks`. Prerequisite *checking* (the
      six `BaseFeatRequired*` tables) is still unevaluated anywhere — that's
      slice 6 territory, not this pass.

      `CreationWizardPage.tsx` now actually submits `draft.feats` (feat ids,
      previously collected by `FeatsStep.tsx` but silently dropped on
      submit); `PickList` (shared with `TraitsStep.tsx`) was generalized from
      plain name strings to `{id, label}` items so `FeatsStep` can pick by id
      while displaying names, without changing `TraitsStep`'s behavior
      (traits stay name-keyed, wrapped as `{id: name, label: name}`). The
      level-up wizard's `LevelFeatStep.tsx` (a later, still-local-only slice
      7 concern) was adapted to the new `FeatDef[]` shape from `/api/feats`
      without migrating its own persistence — and its fighter bonus-feat
      slot now actually filters to `type === 'combat'` instead of offering
      the full feat list, closing the gap noted in `todos.md`.
- [x] Traits (PF1e background traits, e.g. "Reaktionsschnell" — distinct from
      racial *alternate* traits, which are a different rule concept already
      persisted via `CharacterRacialChoice`/`alt_traits` since the ability-
      scores pass above; this bullet was previously miswritten as if it meant
      that). Real `BaseTrait` (id, name, description, `area`) — `area` is a
      plain categorization tag like `BaseFeat.type` (e.g. "combat", "faith",
      "magic", "region", "social", "campaign", "general"), but unlike
      `type`, it's load-bearing here: PF1e caps a character at one trait per
      area, enforced in `create_character` via a DB lookup (can't live in a
      `CharacterCreate` field validator alone, which never sees the
      database). Seed data migrated from the old frontend-shaped
      `backend/app/fixtures/traits.json` (10 names only) into DB-shaped rows
      with placeholder descriptions/areas in
      `backend/app/fixtures/seed/base_traits.json`, via
      `backend/app/seed/trait_seed.py` (same idempotent upsert-by-id pattern
      as `feat_seed.py`). `/api/traits` (`backend/app/routers/traits.py`) is
      now fully database-backed, replacing the old fixture-reading mock
      endpoint in `main.py`.

      What a character took is `CharacterTrait` (level_id, trait_id) — same
      per-`CharacterLevel` audit shape as `CharacterFeat`, exposed as
      `Character.trait_ids`. `POST /api/characters`'s new `trait_ids:
      list[UUID]` field is validated server-side
      (`backend/app/routers/characters.py`): each id must exist in
      `base_traits`, count capped at a flat 2 (a Pydantic validator on
      `CharacterCreate`), and no two chosen traits may share an `area`
      (checked after resolving the ids, alongside the existence check).
      Collapsed onto the highest `CharacterLevel` row being created, same
      reasoning as `feat_ids`.

      `CreationWizardPage.tsx` now submits `draft.traits`; `TraitsStep.tsx`
      switched from picking by trait *name* to picking by id (mirroring
      `FeatsStep.tsx`) and mirrors the one-trait-per-area rule client-side —
      chips are labelled with their area and traits whose area is already
      taken are disabled, via a new optional `disabledIds` prop on the
      shared `PickList` (defaults to none, so `FeatsStep` is unaffected).
      `useCreationOptions`/`CreationOptions.traits` was retyped from
      `string[]` to a new `TraitDef[]` (id/name/description/area).
- [x] Starting spellbook/known spells. Decided ahead of implementation (unlike
      classes/skills, spells had no ER-diagram entities at all until now, and
      `spells_by_class.json` is bare name lists with no per-spell grade
      anywhere — the only place "grade" existed was hardcoded per-character
      mock data in `character_1.json`, disconnected from the class spell
      list): pull spells into the database this slice rather than deferring
      to slice 8, same reasoning as feats/traits — `CharacterSpell` needs a
      real FK target, and a shared spell catalog needs a stable id to hang a
      grade on. Scope for this pass is the known/spellbook list only
      (creation + level-up picker persistence + the add/remove-during-play
      endpoint) — daily prepare/cast tracking and "is this legal right now"
      checks stay deferred to slice 6, since `Spellbook.tsx`'s prepare-toggle
      UI is still driven by mock per-character fixture data, not a real
      per-day tracking model. Bonus spell slots from a high ability score
      (e.g. CHA 12 granting an extra grade-1 slot/day) are part of that
      deferred per-day tracking too, and out of scope here.

      Schema, finalized against real PF1e mechanics (not just mirroring the
      feat/trait shape) after a design pass:
      - `BaseSpell` (id, name, school, description) — identity only, same
        composition-vs-computation split as everywhere else.
      - `BaseSpellComponents` (spell_id, tradition, verbal, somatic,
        material, material_description, focus, focus_description) — a
        spell's verbal/somatic/material/focus components can differ between
        its arcane and divine version, so this is keyed by
        `(spell_id, tradition)`, not by spell alone. Modeled now for a later
        "available actions" pass (slice 6) that will actually check for a
        component pouch/focus item; has no effect yet.
      - `BaseClassSpell` (base_class_id, spell_id, grade) — a spell's grade
        is per-class in PF1e (e.g. Cleric 3rd / Bard 2nd for the same
        spell), not a spell-level constant. Mirrors `BaseClassSkill`'s join
        shape.
      - `BaseClassSpellsKnown` (base_class_id, level, grade, count) — the
        classic per-class spells-known-by-level table (e.g. a 3rd-level
        Sorcerer knows 4× grade-0, 2× grade-1). Doubles as the grade-gate:
        if no row exists for a given `(base_class_id, level, grade)`, that
        grade isn't accessible at that level, for any casting style. For
        spontaneous casters (`spellType: 'spontaneous'`) `count` is the
        cumulative known-spells cap at that level/grade — a level-up only
        grants the *delta* from the previous level's count (e.g. 2 known at
        level 1 → 3 known at level 2 grants exactly one new pick, not three).
        For arcane-prepared (Wizard-style) classes, `count` isn't used to
        cap known spells (the spellbook has no cap); only row *presence*
        matters, for grade-gating.
      - `BaseClass` gains two real columns (not fixture fields, since these
        are new and the intent is fewer fixtures over time, not more):
        `casting_ability` (2-letter code, e.g. CH for Bard/Sorcerer, IN for
        Wizard, WE for Druid/Cleric/Ranger; null for non-casters) and
        `spell_tradition` (`arcane`/`divine`/null) — the latter is what
        `BaseSpellComponents` keys off of.
      - Arcane-prepared (Wizard-style) spellbook growth: at class level 1,
        all grade-0 spells plus `2 + casting-ability-mod` grade-1 spells;
        each level after that, +2 new spells of any grade currently
        accessible (per `BaseClassSpellsKnown`'s gate) — "below its maximum"
        grade is an allowed pick, not a forced one. Separately, and
        independent of level-up, the player can add further spells to the
        spellbook at any time via the in-play add-to-spellbook action, with
        no server-side cap (gold/downtime cost isn't tracked yet).
      - Non-spontaneous, non-arcane-prepared casters (`spellType:
        'divine-prepared'` — Cleric/Druid/Ranger-style) have no known-spell
        list at all; they prepare from the full class spell list. No
        `CharacterSpell` rows or picker for these classes in this pass,
        matching `SpellsStep.tsx`'s existing messaging.
      - `CharacterSpell` (level_id, base_class_id, spell_id) — per-
        `CharacterLevel` audit row, same shape as `CharacterFeat`/
        `CharacterTrait`, but also keyed by `base_class_id` since a
        multiclassed character's known-spell budget is tracked separately
        per class. The in-play "add to spellbook" action
        (`requirements_v2.md` §2.2, `POST /api/characters/{id}/spellbook`,
        plus `DELETE .../spellbook/{spell_id}`) collapses onto the
        character's current highest `CharacterLevel`, same pattern used for
        multi-level creation elsewhere.

      Implementation: `backend/app/models/spell.py`, migration
      `c2c1f53b71b2`, seed data + idempotent seed script
      (`backend/app/fixtures/seed/base_spells.json` +
      `base_spell_components.json` + `base_class_spells.json` +
      `base_class_spells_known.json`, `backend/app/seed/spell_seed.py`;
      `base_classes.json` gained `casting_ability`/`spell_tradition` per
      caster class), budget/gating logic in `backend/app/rules/spells.py`
      (mirrored on the frontend in `creationCalculations.ts` — keep both in
      sync), validation wired into `POST /api/characters`
      (`CharacterCreate.spell_ids`) and the two new endpoints in
      `routers/characters.py`. `GET /api/spells` and `GET /api/spells-by-class`
      (`routers/spells.py`) are now real, replacing the old
      `spells_by_class.json` fixture endpoint; `GET /api/classes` additionally
      exposes each class's `id`/`castingAbility`/`spellTradition`/
      `spellsKnownByLevel`. `SpellsStep.tsx` (creation) and `LevelSpellStep.tsx`
      (level-up) pick by spell id against the real per-grade budgets instead
      of the old flat `spellPickMax` guess; `spellIdsForSubmission`
      (creationCalculations.ts) unions in the mandatory grade-0 spells for
      arcane-prepared classes before `POST /api/characters`. Covered by 18
      new backend tests (`backend/tests/test_spells.py` +
      `test_characters.py`) and an end-to-end browser smoke test through the
      real creation wizard.

      **Not done in this pass** (explicitly out of scope, see above): the
      character *sheet*'s `Spellbook.tsx`/`CharacterSheetPage.tsx` still run
      entirely on the two mock character fixtures, not a real backend
      character, so the new `POST`/`DELETE .../spellbook` endpoints aren't
      wired into the sheet UI yet — same "thin shape only" limitation as
      gear/inventory. They're ready to use once the sheet gets its full
      computed shape (later slice-3-adjacent work).
- [ ] Deliberately deferred further: archetype-conflict checking for
      classes (needs a data-model decision on which archetypes mutually
      exclude each other — not yet made; the equivalent question for races
      was resolved in slice 2).
- [x] Fully playable level-1 character: HP/BAB/save progression, computed
      (not stored) from real per-class data — `BaseClass` gains
      `bab_progression` (`float`: 1.0 full/0.75 ¾/0.5 ½) and
      `fort_save`/`ref_save`/`wil_save` (`bool`: good/poor), matching the
      fields already sketched in `readme.md`'s ER diagram but never
      implemented until now (migration `fa831e2478e2`; only ever set on root
      rows, same as `hit_dice` — an archetype doesn't change its parent's
      progression). Seeded with the real PF1e core-rulebook values for all
      12 root classes (`backend/app/fixtures/seed/base_classes.json` via
      `class_seed.py`). `GET /api/classes` exposes them as `babProgression`/
      `fortSave`/`refSave`/`willSave`, same convention as `castingAbility`/
      `spellTradition`.

      BAB and saves are genuinely computed, not stored: `Character.bab`/
      `Character.saves` (`backend/app/models/character.py`) group `levels`
      by root class the same way `Character.classes` already does, then sum
      each class's own contribution — `rules/progression.py`'s
      `class_bab`/`class_save_bonus` — against that class's own level count,
      never the total character level run through one averaged progression
      (`requirements_v2.md` §2's multiclass rule; a Kämpfer 2/Schurke 1
      character's BAB is `floor(2*1.0) + floor(1*0.75)`, not
      `floor(3*something)`). Exposed as new `bab`/`saves` fields on
      `CharacterRead`.

      `CharacterLevel.hit_points` (already a column, previously always
      unset) does get stored per level, unlike BAB/saves — it already had
      per-level storage in the ER diagram, presumably as an audit trail
      (which level contributed how much HP). Per an explicit decision with
      the user (not assumed): the character's very first level ever is
      auto-maxed (its class's hit die at max value, no input needed — PF1e
      RAW is unconditional here); every level after that (including a newly
      multiclassed class's first level) is a player-entered roll, submitted
      via `CharacterCreate.hit_points` (level number as a string key -> HP
      value) and validated against that level's class's hit die range
      (`rules/progression.py`'s `is_valid_rolled_hit_points`, `1 <= value <=
      hit_dice`) — creation rejects with 422 if a level 2..total_level entry
      is missing, extra, out of range, or if level 1 is included at all.
      `current_hit_points` (still "current, not max" per its existing
      docstring) is server-computed once those rolls are validated, as
      `sum(level.hit_points) + effective_CON_mod * total_level`
      (`requirements_v2.md` §2's formula) — `CharacterCreate.current_hit_points`
      (a flat client-supplied number, which nothing actually sent) was
      removed in favor of this. Effective CON mod reuses the same
      `race_ability_score_mods`/`_effective_ability_mod` helper already used
      for INT (skill points) and casting-ability (spell budgets), so a
      race's flat ability bonuses (e.g. Elf's -2 CON) apply to HP the same
      way they apply everywhere else.

      `BaseClass` also gained `skill_points_base` (int, only set on root
      rows) in this pass, migrating `classes.json`'s `skillPointsBase` field
      into the database the same way `bab_progression`/the saves were —
      `_skill_points_total` (`routers/characters.py`) now reads
      `root.skill_points_base` instead of looking the class up by name in
      the fixture, and `GET /api/classes` overwrites its `skillPointsBase`
      field with the real column at read time (migration `dc0c837e77bb`).

      Moved here from slice 7's original "thin: HP/BAB/save progression"
      bullet, by explicit decision: a level-1 character already has BAB and
      saves — computing them is what makes a *created* character playable,
      not a leveling concern, so it belongs at the end of character
      creation rather than gated behind items (4)/effects (5)/actions (6),
      none of which a fresh level-1 character strictly needs. Level-up
      (slice 7) reuses this computation per new level rather than
      rebuilding it.
- [x] Minimal starting gear: real `BaseItem` catalog (id, name, `category` —
      a plain categorization tag, e.g. "weapon"/"armor"/"shield"/"gear"/
      "tool"/"consumable", same convention as `BaseFeat.type`/`BaseTrait.area`
      — not evaluated by any rule logic yet, only there so a picker can
      group/filter by it now instead of a schema change later; `price`),
      replacing `items.json`'s flat name/price list, seeded via
      `backend/app/fixtures/seed/base_items.json` +
      `backend/app/seed/item_seed.py` (same idempotent upsert-by-id pattern
      as the other slice-3 catalogs). `GET /api/items`
      (`backend/app/routers/items.py`) is now fully database-backed,
      replacing the old fixture-reading mock endpoint in `main.py`.

      What a character starts with is `CharacterGear` (character_id, item_id,
      quantity) — unlike `CharacterFeat`/`CharacterTrait`/`CharacterSpell`,
      *not* a per-`CharacterLevel` audit row: gear is bought/found/dropped
      during play, not gained at a level, so it's keyed by `character_id`
      directly, matching slice 4's planned character-scoped
      `POST/PATCH/DELETE .../gear` endpoints (still those exact endpoints,
      still ❌ — this pass only covers gear picked at creation time).
      `POST /api/characters`'s new `gear: [{item_id, quantity}]` field is
      validated server-side (`backend/app/routers/characters.py`): every
      `item_id` must exist in `base_items`, quantity must be positive, and
      duplicate `item_id`s in the same submission are rejected (rather than
      silently overwriting) — descriptive only, no equip slots, no
      AC/attack-bonus computation (still slice 4, along with the shared
      modifier/bonus-stacking design and the in-play gear endpoints above).

      `EquipmentStep.tsx` no longer accepts a freeform item name typed
      against a `<datalist>` — it now picks by id from the real catalog
      (a category filter plus an item dropdown, mirroring
      `FeatsStep.tsx`/`TraitsStep.tsx`'s id-based-picker convention), with
      picking the same item twice merging into one higher-quantity entry
      rather than a duplicate row. `ItemCatalogEntry` gained `id`/`category`
      fields; `CreationWizardPage.tsx` now submits `draft.gear`. Starting
      gold (`draft.gold`) remains session-local/unsubmitted — out of scope
      for this pass, no `characters.gold` column exists yet.
- [ ] **Class-ability computation (`HANDLERS` registry, mirrors
      `rules/race_abilities.py`).** `BaseClassAbility`/`BaseClassAbilityGrant`
      (introduced for Kämpfer's bonus feat, then Waldläufer/Magier's data
      corrections — see `todos.md`) are composition-only today: which
      abilities a class/archetype/school choice grants, and at what level,
      is real data, gated correctly by level and by `option_choice_id`
      (`sheet.py`'s `_build_class_features`) — but no ability's actual
      mechanical effect is computed anywhere. Concretely inert right now:
      Kämpfer's Rüstungstraining/Waffentraining/Tapferkeit numbers,
      Waldläufer's Erzfeind/Bevorzugtes-Gelände bonuses, and all 26 of
      Magier's arcane-school powers (flat bonuses like Bezauberndes
      Lächeln's +2 Bluffen/Diplomatie/Einschüchtern, level-scaling ones like
      Starke Zauber's spell-damage bonus, and per-day-use pools like "3 + IN-
      Modifikator Mal pro Tag" abilities such as Säuregeschoss). Needs a
      `rules/class_abilities.py` `HANDLERS: dict[UUID, Callable]` keyed by
      `BaseClassAbility.id`, same hand-frozen-UUID convention as
      `race_abilities.py` — flat-bonus cases can likely share one generic
      handler factory (per CLAUDE.md's composition-vs-computation split),
      conditional ones (level-scaling, per-day pools) each need their own
      function. Where the effect is a passive numeric bonus (e.g. Bannzauber's
      Resistenz, Verzauberung's Bezauberndes Lächeln), this should feed the
      same `Modifier`/`stack()` design from slice 4/5 rather than a third
      bonus system. Scope this once slice 5 (Effects) has landed, since
      several of these abilities are duration/use-limited in the same way
      active effects are — not a slice-3 concern to retrofit now.

### 4. Items / Inventory
- [x] Gear table + equipment slots — scoped to armor/shield, the only two
      categories with a real, well-defined, unconditional mechanical effect
      (AC). `BaseItem` gains `ac_bonus`/`max_dex_bonus` (nullable, only
      populated for category "armor"/"shield" — armor's `max_dex_bonus`
      caps the Dex bonus to AC while worn, per PF1e). `CharacterGear` gains
      `equipped_slot` (one of the paperdoll's slot keys, `"ruestung"`/
      `"schild"` today), `enhancement` (an item instance's own magic "+N",
      previously a throwaway frontend-only field), and `properties`
      (descriptive weapon properties, same "not evaluated by rule logic
      yet" convention as `BaseItem.category`). Migration `8363bc616626`.

      Explicit scope decision, not a partial implementation: the mock
      paperdoll's other 12 "wondrous item" slots (ring, belt, amulet, ...)
      are left exactly as before (cosmetic, frontend-only) — there are no
      real magic-item catalog rows behind them (the fixture characters'
      slot `options` are hand-typed flavor strings), and inventing
      mechanical values for them now would be exactly the guessed-content
      problem `todos.md` already flags, not a schema gap to close here.
      `backend/app/rules/equipment_slots.py`'s `SLOT_DEFINITIONS` (the
      paperdoll's fixed 15-slot layout — pure UI layout data, not rule
      content) also adds a `"schild"` (shield) slot that never existed in
      the original mock at all, and `SLOT_CATEGORY` maps only those two
      keys to the `BaseItem.category` they accept.

      Real PF1e SRD values (not guessed) seeded for the 6 armor + 2 shield
      rows already in `base_items.json` (e.g. Lederrüstung +2 AC/max Dex
      +6, Kettenhemd +4/+4, Vollplatte +9/+1, Turmschild +4 AC) — standard,
      well-documented stats, unlike the flavor-heavy placeholder content
      `todos.md` flags elsewhere.
- [x] `POST /api/characters/{id}/gear` (upserts — adding an already-owned
      item increases quantity instead of erroring, unlike creation's
      duplicate-rejecting `gear` validator), `PATCH .../gear/{item_id}`
      (quantity/enhancement/properties, any subset), `DELETE
      .../gear/{item_id}`, `PUT .../slots/{slot_key}` (`slot_key` restricted
      to `"ruestung"`/`"schild"`; validates the item is owned and its
      category matches the slot; unequips whatever was previously in that
      slot). All in `backend/app/routers/characters.py`, same
      `CharacterRead`/204 response convention as the existing spellbook
      endpoints. CORS `allow_methods` gained `PUT` (only `GET`/`POST`/
      `PATCH`/`DELETE` before).
- [x] Shared modifier/bonus-stacking design: `backend/app/rules/modifiers.py`
      — a `Modifier(source, type, value)` dataclass and `stack()` applying
      PF1e's real stacking rule (same-type bonuses take the max, not the
      sum; dodge/circumstance/untyped always stack). Only "armor"/"shield"
      types are actually produced today; the type-max logic is inert until
      slice 5 gives it a second source (e.g. a spell granting natural
      armor) — built once now, per the Guiding decision above, not
      redesigned when effects arrives.
- [x] AC recompute went further than the originally-planned stub: `armorClass`
      is genuinely computed in `sheet.py` (`10 + min(dex_mod, max_dex_bonus
      or dex_mod) + stack(modifiers)`) from whichever `CharacterGear` rows
      have `equipped_slot` set, not just stored equip state with a
      placeholder AC. Verified end-to-end through the real browser UI
      (Playwright): equipping a +2 armor and +4 shield took AC 12 → 18,
      unequipping the shield reverted it to 14, and a page reload (with a
      fresh user/character reselect, since selection isn't persisted
      client-side) still showed 14 with the armor still equipped —
      confirming server-side persistence, not local state.

      Frontend: `GearList.tsx`'s add/edit form switched from freeform
      name+qty text input to a category-filtered catalog id picker
      (mirrors `EquipmentStep.tsx`'s existing convention exactly — dropped
      the rename affordance, since real items are catalog rows now, not
      renameable); new `useItemsCatalog.ts` hook (mirrors
      `useEffectsCatalog.ts`) and `useCharacter.ts` gained `refetch()`.
      `CharacterSheetPage.tsx`'s gear/slot/item-detail handlers now branch
      on whether the current character is real (a database UUID) vs. one
      of the two mock sheet fixtures (`"1"`/`"2"`, no backing row) — real
      characters call the new endpoints and `refetch()`, fixtures keep
      their original local-only behavior unchanged.

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
- [ ] Thin: single-class new-level choices (feat/skill/spell as applicable)
      plus extending slice 3's HP/BAB/save computation by one level — not
      building that computation fresh here (moved to slice 3: a level-1
      character needs it too, not just a leveled-up one).
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
