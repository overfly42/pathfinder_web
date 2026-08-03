# Backend build-out roadmap — completed work archive

Archive of everything checked off in `roadmap.md`, moved out to keep that
file focused on what's still open. Guiding decisions, slice ordering
rationale, and the current frontier of work stay in `roadmap.md` — this
file is pure history, in the same order the work was originally planned.
Content below is otherwise unedited (verbatim from `roadmap.md` at the time
each item was checked off), including original heading levels/numbering.

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

### 3. Character creation — thick

Completed items only from this slice — see `roadmap.md` for the items still
open (archetype-conflict checking, class-ability computation, "pick from a
restricted list" phases 5–6, class source-page fetch tooling).

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

#### "Pick from a restricted list" unification — design + phases 1–4

Full design rationale and seeding history for the feat-pool/ability-pool/
spell-pool/deterministic-spell-grant work (originally part of slice 3).
Phases 5–6 (validation/enforcement, frontend) are still open — see
`roadmap.md`.

- [ ] **"Pick from a restricted list" unification (generalizes past
      Kämpfer's hardcoded "combat" filter) — feat pools, ability pools,
      spell pools, and deterministic per-choice spell grants.** Schema
      (phase 1) and seed data (phases 2–4, see the status note after the
      blocking-prerequisite paragraph below) are both fully in now —
      validation/enforcement (phases 5–6) is still open.
      `BONUS_FEAT_SLOT_ABILITY_IDS` (`rules/feat_slots.py`) only tracks *how
      many* bonus feat slots a class grants — not *which* feats are legal
      for that slot. Today that's invisible because Kämpfer is the only
      class tagged, and its slot happens to always mean "any combat feat":
      `LevelFeatStep.tsx`'s bonus-feat picker hardcodes `f.type === 'combat'`,
      and — found while scoping Magier's/Hexenmeister's periodic bonus feats
      (`todos.md`) — **creation-time picking has no restriction at all, for
      any class**: `_feat_max` (`routers/characters.py`) and
      `featMax`/`FeatsStep.tsx` only ever check a raw count, so a 1st-level
      Kämpfer can currently spend their Bonus-Kampftalent on any feat in the
      catalog, not just a combat one.

      Comparing every "pick from a list" class feature across the classes
      done so far (Kämpfer/Waldläufer/Magier/Hexenmeister/Schurke — see
      `todos.md`) shows this isn't one gap but four different shapes,
      depending on what's actually being picked:

      | Class feature | Picks from | Mechanism |
      |---|---|---|
      | Kämpfer Bonus-Kampftalent, Magier Bonustalent, Hexenmeister Talent des Blutes, Waldläufer Kampfstiltalent | an existing `BaseFeat`, filtered by type or an explicit closed list | §1 `BaseClassAbilityFeatOption` |
      | Schurke Trick / Verbesserte Tricks | a *new*, class-specific ability with its own text (some of which then themselves grant a feat or a spell) | §2 — reuse `BaseClassOptionGroup`/`Choice`, not a new table |
      | Schurke Höhere/Niedere Magie | an existing `BaseSpell`, filtered to a class's list at a fixed grade | §3 `BaseClassAbilitySpellOption` |
      | Hexenmeister Zauber des Blutes | an existing `BaseSpell`, but **fixed** per bloodline+level — no real choice at all | §4 `BaseClassSpellGrant` |
      | Kämpfer Waffentraining (weapon group) / Waffenmeisterschaft (specific weapon) | a weapon-group tag / a specific `BaseItem` | deferred — no populated weapon catalog yet (slice 4 only seeded armor/shield) |

      This is why Magier's Bonustalent and Hexenmeister's Talent des Blutes
      were deliberately left untagged rather than reusing
      `BONUS_FEAT_SLOT_ABILITY_IDS` as-is (their eligible sets are narrower
      and differently-shaped than "combat"), and why Schurke's Trick was
      imported as a bare slot with no catalog of the ~23 individual talents
      behind it (`todos.md`) — none of these had anywhere to live yet.

      Blocking prerequisite from when this was first scoped (feat catalog
      too small to make eligibility data meaningful) is **resolved**: the
      catalog has since grown to 325 feats across 8 real `type` tags
      (`combat: 149, general: 141, metamagic: 9, kritischer_treffer: 8,
      item_creation: 8, kampfkunst: 7, questtalente: 2, teamwork: 1`) via
      `build_feats_seed.py`. Both further prerequisites named above turned
      out to already be resolved by existing data, not new work: Magier's
      named exception ("Zaubermeisterschaft"/Spell Mastery) was already a
      seeded feat, and Hexenmeister's ~80 named bloodline talents — assumed
      missing here, based on the catalog's size *before* `build_feats_seed.py`
      ran — all 80 references in `scripts/import_hexenmeister_bloodlines.py`'s
      output (`app/fixtures/imported/hexenmeister_bloodline_bonus_feats.json`)
      resolve by name against the current 325-feat catalog with zero gaps.
      Both are seeded now (see status below).

      **Status (seeded):** §1 for Kämpfer/Magier/Hexenmeister/Waldläufer,
      §2's Trick/Verbesserte-Tricks catalog (23 tricks) plus its
      feat-granting members (Kampfkniff/Schurkenfinesse/Waffentraining-trick,
      and "Talent"'s unrestricted choice via one row per known `feat_type`),
      §3 for Höhere/Niedere Magie, and §4 (Hexenmeister's actual Zauber des
      Blutes) are all real rows now (`base_class_ability_feat_options.json`/
      `base_class_ability_spell_options.json`/`base_class_spell_grants.json`,
      seeded by `app.seed.class_ability_option_seed`/`spell_seed`). Verified
      end-to-end (`test_feat_slots.py`, `test_spells.py`, plus
      `test_character_sheet.py`'s
      `test_class_features_include_picked_trick_via_option_group` — picking
      "Aufspringen" via `options: {"trick": [...]}` surfaces it in
      `classFeatures` with **zero changes to `sheet.py`**, confirming §2's
      core design bet that a repeated-pick group needs nothing beyond what
      domain/bloodline/school already exercise).

      Waldläufer's Kampfstiltalent turned out fully resolvable once actually
      fetched: <http://prd.5footstep.de/Grundregelwerk/Klassen/Waldlaeufer>'s
      prose lists both combat styles' full feat progression (Bogenschießen:
      Fernschuss/Kernschuss/Präzisionsschuss/Schnelles Schießen, +2 at 6th,
      +2 at 10th; Kampf mit zwei Waffen: Doppelschnitt/Kampf mit zwei
      Waffen/Schnelle Waffenbereitschaft/Verbesserter Schildstoß, +2 at 6th,
      +2 at 10th — 8 feats/style, all 16 already in the catalog, zero
      missing). Added a `combat_style` option group (`max_choices: 1`) since
      none existed before. *Not* modeled: which of a style's 8 feats are
      eligible depends on the character's level (only 4 available before
      6th) — `BaseClassAbilityFeatOption` seeds the full eventual union per
      style, same "not yet enforced" scope as everywhere else here.

      Hexenmeister's real Zauber des Blutes (fixed spell per bloodline per
      odd level, 3rd–19th) came from the same class page's per-bloodline
      "Bonuszauber:" lines, cross-checked against real PF1e bloodline data
      (Drachenblutlinie's list matches the SRD's Draconic bloodline exactly).
      78 of the 80 unique named spells (81 counting Elementarhorde, missed
      on the first pass and caught before seeding) didn't exist in the
      23-spell catalog yet — resolved via the PRD's bulk `/cache/
      prd_datatable__zauber.txt` spell index (same shape as the feat index
      `import_feats_from_prd.py` already uses), which supplied name/school/
      description directly, no manual authoring needed. One data quirk found
      and fixed: the index's "Zauber zurückwerfen" description is missing
      its leading "R" ("eflektiert..." → "Reflektiert...") in the source
      itself, not a parsing bug — corrected by hand. Spells resolvable with
      a Hexenmeister-list grade also got a real `BaseClassSpell` row (72 of
      79); several bloodline spells are legitimately off-list entirely
      (e.g. Himmlische Blutlinie's "Segnen"/Bless is a Cleric spell, matching
      real Celestial-bloodline rules) and correctly got no `BaseClassSpell`
      row, only the `BaseClassSpellGrant`.

      A second sweep over the already-imported classes surfaced three more
      instances of this same "pick from a restricted list" shape that
      weren't part of the original plan, all now closed too:
      - Waldläufer's Erzfeind (levels 1/5/10/15/20) and Bevorzugtes Gelände
        (3/8/13/18) already had correct `BaseClassAbilityGrant` rows for
        every repeated occurrence from the original Waldläufer pass — only
        their `BaseClassOptionGroup.max_choices` was still `1` from before
        repeated-pick groups existed. Bumped to 5/4; no new catalog rows
        needed (all 32 enemies/11 terrains already existed).
      - Waldläufer's Bund des Jägers (4th level, previously one ungated
        ability with both branches' text in one paragraph) split into the
        same shape as Hexenmeister's bloodline powers: a short always-on
        overview ability plus two new `option_choice_id`-gated ability rows
        (one per branch) behind a new `hunter_bond` option group. The
        animal-companion branch's text still only names the fixed animal
        list in prose — no animal-companion catalog exists anywhere in the
        schema, deliberately out of scope here.
      - Found and fixed a real bug from the first pass: the `combat_style`
        group's `base_class_id` was Mönch's, not Waldläufer's (a
        copy-paste constant mistake in the seed-data generation script) —
        the original test didn't catch it because it only filtered by
        `key`, not `base_class_id` too. Fixed, and every option-group test
        now asserts `base_class_id` explicitly to catch a repeat.

      **Still open:** phases 5–6 (validation/enforcement, frontend) remain
      entirely unbuilt — every table above is real and queryable, but nothing
      reads them yet at creation or level-up time. Also still open, and
      explicitly out of scope for this whole effort: Kämpfer's Waffentraining/
      Waffenmeisterschaft (§5, needs a populated weapon catalog), Magier's
      familiar-type choice under Arkane Verbindung, and the animal-companion
      branch of Bund des Jägers above — all three need a new catalog concept
      that doesn't exist yet (weapons, familiars, animal companions), not
      just another `BaseClassOptionGroup`.

      ### 1. Feat pools — `BaseClassAbilityFeatOption`
      One new join table, pure composition (no `HANDLERS`-style code):
      ```python
      class BaseClassAbilityFeatOption(Base, UUIDPrimaryKeyMixin):
          """One eligible pick for a bonus-feat-slot ability. A slot's full
          eligibility is the union of its rows. Exactly one of feat_type/
          feat_id is set per row:
          - feat_type: any BaseFeat with this type is eligible (broad
            category — Kämpfer: "combat"; Magier: one row each for
            "metamagic"/"item_creation").
          - feat_id: this exact feat is eligible (closed list — Hexenmeister's
            per-bloodline talent list; Magier's "Zaubermeisterschaft"
            exception; Schurke's Schurkenfinesse → Waffenfinesse and
            Waffentraining-trick → Waffenfokus, both closed lists of one).
          option_choice_id (nullable) narrows the row to characters who
          picked that BaseClassOptionChoice, same meaning as
          BaseClassAbilityGrant.option_choice_id — lets "Talent des Blutes"
          share one ability_id across 10 different eligible lists.
          """
          ability_id: Mapped[UUID]              # FK BaseClassAbility
          option_choice_id: Mapped[UUID | None]  # FK BaseClassOptionChoice
          feat_type: Mapped[str | None]
          feat_id: Mapped[UUID | None]
      ```
      "Is this ability a feat slot" becomes "does it have any rows here" —
      retires the hand-frozen `BONUS_FEAT_SLOT_ABILITY_IDS` set entirely, so
      a future class's bonus feat, whatever shape its eligibility takes, is
      a pure data change (no code edit at all, not even adding an id to a
      set). Doubles as the mechanism for Schurke's feat-granting tricks
      (Kampfkniff, Schurkenfinesse, Waffentraining-trick), keyed off the
      *trick's own* `BaseClassAbility.id` — see §2.

      Enforcement approach: aggregate/budget check, not per-slot
      assignment — don't track which feat fills which grant, just require
      "at least N of the picked feats satisfy this slot's eligibility",
      mirroring how skill points/spells known are already budget-checked
      elsewhere rather than slot-assigned. Simpler, no new creation payload
      shape, and avoids awkwardness where a class has several slots sharing
      one eligibility (Kämpfer has ~10 "combat" slots by 20th level — per-
      slot assignment buys nothing there). Explicit slot assignment (like
      the level-up wizard's separate `draft.newBonusFeat` field) stays a
      fallback only if some future class needs genuinely different
      eligibility for two slots taken at the same level.

      ### 2. Ability pools (Schurke's Trick) — reuse option groups, not a
      new table
      A pool of *new* class-specific abilities (as opposed to a filtered
      slice of an existing catalog) turns out not to need a dedicated
      "pool" concept at all: it's the exact same shape as Kleriker's
      `domain`/Hexenmeister's `bloodline`/Magier's `school` groups, just with
      more members and picked repeatedly instead of once. Trick becomes a
      `BaseClassOptionGroup` (key `"trick"`, `max_choices = 10` — the total
      Trick grants across a Schurke's career), one `BaseClassOptionChoice`
      per trick, and each trick's actual mechanical text lives in the usual
      `BaseClassAbility` + `BaseClassAbilityGrant(option_choice_id=...,
      level=1)` pair — identical to how a domain's granted powers work
      today. "Verbesserte Tricks" is a second group (`"trick_advanced"`)
      following the same shape.

      This was tempting to instead model as a self-referencing
      `BaseClassAbility.pool_ability_id`, which would save the one
      duplicate identity row per trick (name appears once in
      `BaseClassOptionChoice.name`, once in `BaseClassAbility.name`) — but
      that would need `sheet.py`'s `_build_class_features` to gain a
      *second* source of ability grants (pool members have no
      `BaseClassAbilityGrant` of their own to be found by), whereas routing
      through `BaseClassOptionGroup`/`Choice` needs no change there at all:
      whatever already turns "character has a matching `CharacterClassOption`
      row" into "include this `option_choice_id`-gated grant" already works
      unmodified for Trick, since it's just a group with more members and a
      higher `max_choices`. Reusing an existing read path beats adding a
      parallel one, so the minor row duplication is the better trade.

      Needs `CharacterClassOption` (`character.py`) extended, since one-time
      creation picks and Trick's repeated per-level picks both need to live
      in the same table:
      - `level_id: Mapped[UUID | None]` (FK `character_levels`) — which
        `CharacterLevel` this pick was made at. Existing domain/bloodline/
        school picks get this set to the highest `CharacterLevel` row
        created at character creation (same collapse convention as
        `CharacterSkillRank`/`CharacterFeat`), no behavior change. Repeated
        picks (Trick) get the level-up's own row.
      - `grant_id: Mapped[UUID | None]` (FK `base_class_ability_grants`) —
        which specific recurring grant occurrence this pick fills (e.g. *the
        level-12 Trick grant*, not just "a Trick pick"). Null for one-time
        groups. Needed because eligibility for a repeated pick can depend on
        which occurrence it is — "Verbesserte Tricks" only unlocks the
        `trick_advanced` group from the grant at level 10 onward, and
        without `grant_id` that has to be inferred from counting prior picks
        instead of a direct `grant.level >= 10` join.
      - `choice_id: Mapped[UUID | None]` (FK `base_class_option_choices`) —
        finally resolves the model's own long-standing TODO ("`choice` still
        stores the pick as a free string rather than an FK to this table —
        reconciling that is a follow-up"). Safe to populate unconditionally
        at write time: `_validate_options` (`routers/characters.py`) already
        guarantees every stored `choice` string matches a real
        `BaseClassOptionChoice.name` in that group before the row is ever
        created. `choice` (the string) stays for now as a cheap
        display/debug mirror of the resolved row, not removed in this pass.

      `BaseClassOptionGroup.max_choices`'s docstring needs a one-line update
      once a repeated-pick group exists: today it means "pick up to N,
      once, at creation"; for a repeated-pick group it means "one pick per
      qualifying grant, up to N total across a career" — same field, two
      meanings depending on whether the group's abilities also use
      `grant_id`, worth spelling out so the next class that reuses this
      doesn't have to reverse-engineer which one applies.

      ### 3. Spell pools (Schurke's Höhere/Niedere Magie) —
      `BaseClassAbilitySpellOption`
      Sibling to §1, same feat_type/feat_id duality applied to spells,
      reusing `BaseClassSpell` (already `base_class_id` + `spell_id` +
      `grade`) as the source of truth for the broad-filter case instead of
      enumerating every eligible spell by hand:
      ```python
      class BaseClassAbilitySpellOption(Base, UUIDPrimaryKeyMixin):
          ability_id: Mapped[UUID]               # FK BaseClassAbility
          option_choice_id: Mapped[UUID | None]  # FK BaseClassOptionChoice
          spell_id: Mapped[UUID | None]          # closed list entry
          source_class_id: Mapped[UUID | None]   # OR: broad filter — any
          source_grade: Mapped[int | None]       #     spell in this class's
                                                  #     list at this grade
      ```
      Niedere Magie: `source_class_id` = Hexenmeister/Magier, `source_grade
      = 0`. Höhere Magie: same classes, `source_grade = 1` (plus a
      trick-requires-trick prerequisite on Niedere Magie — prerequisite
      *enforcement* stays out of scope, same "recorded but not yet checked"
      state as every other `BaseFeatRequired*` row until slice 6).

      ### 4. Deterministic per-choice spell grants (Hexenmeister's actual
      Zauber des Blutes) — not a pool at all
      Initially assumed this needed pool machinery too, but PF1e grants one
      **fixed** spell per bloodline per level — no player choice. Same
      shape as the bloodline power grants already modeled (Macht des
      Blutes), just for a spell instead of an ability:
      ```python
      class BaseClassSpellGrant(Base, UUIDPrimaryKeyMixin):
          base_class_id: Mapped[UUID]
          option_choice_id: Mapped[UUID | None]  # the bloodline
          spell_id: Mapped[UUID]
          level: Mapped[int]
      ```
      Character side needs nothing new — leveling just auto-inserts the
      matching `CharacterSpell` row, same as any other known-spell grant.

      ### 5. Weapon groups / specific weapons — mostly still blocked
      `BaseItem.weapon_group` (nullable tag, same convention as `category`)
      is cheap to add now, and Waffentraining's "pick a group" would then
      reuse the same `BaseClassOptionGroup`/`Choice`/`CharacterClassOption`
      triple from §2. Waffenmeisterschaft (pick one specific weapon) stays
      deferred — there's no populated weapon catalog yet (slice 4 only ever
      seeded armor/shield rows), so there's nothing real to pick from until
      that lands.

      Phased:
      1. [x] `BaseClassAbilityFeatOption` + `BaseClassAbilitySpellOption` +
         `BaseClassSpellGrant` models/migration (`a92f912d53bf`);
         `CharacterClassOption` gains `level_id`/`grant_id`/`choice_id`
         (the latter now actually populated at creation time, see
         `routers/characters.py`); `BaseItem` gains `weapon_group`.
      2. [x] Feat catalog fill-in — turned out to be a no-op: both
         "Zaubermeisterschaft" and all ~80 named bloodline talents already
         existed in the 325-feat catalog (see the resolved-prerequisite
         note above); nothing to add.
      3. [x] for Kämpfer/Magier/Hexenmeister/Waldläufer —
         `BaseClassAbilityFeatOption` seeded (110 rows total including §2's
         feat-granting tricks and Waldläufer's `combat_style`-gated
         Kampfstiltalent lists); see `class_ability_option_seed.py`.
         `BONUS_FEAT_SLOT_ABILITY_IDS` **not yet retired** — still the only
         mechanism `rules/feat_slots.py` actually reads; phase 5 is what
         would replace it.
      4. [x] Schurke's Trick/Verbesserte Tricks (`BaseClassOptionGroup`/
         `Choice` rows plus `BaseClassAbility`/`Grant` pairs, §2),
         Hexenmeister's Zauber des Blutes (§4, 90 `BaseClassSpellGrant`
         rows), and Höhere/Niedere Magie (§3) are all seeded.
      5. [ ] Backend: extend creation's feat validation to check aggregate
         eligibility counts, not just the total; expose resolved eligibility
         (per-character for Hexenmeister, since it depends on the chosen
         bloodline — same resolution shape as `_build_class_features`'s
         `option_choice_id` filtering). Extend the same validation to
         repeated ability-pool picks (Trick) using `grant_id`.
      6. Frontend: replace `LevelFeatStep.tsx`'s hardcoded `f.type ===
         'combat'` with a lookup against the resolved eligibility from step
         5; optionally surface a hint in `FeatsStep.tsx` at creation ("must
         include N combat feats").

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
