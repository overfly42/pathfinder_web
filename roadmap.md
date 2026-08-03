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

Done — DB/ORM/migrations/test harness. Full detail: `roadmap_history.md`.

## Slices

### 1. User lifecycle (thin only)
Done — thin slice, proved the pattern. Full detail: `roadmap_history.md`.

### 2. Character creation — thin
Done — races tables, minimal `characters` table, creation/read/update/
delete endpoints, wizard persists instead of showing a mock banner. Full
detail: `roadmap_history.md`.

### 3. Character creation — thick (its own iterations, not one lump)
Done: ability scores/point-buy, class selection/storage, archetype + class
option-group persistence (`hit_dice`/favored class), skills, feats, traits,
starting spellbook/known spells, fully playable level-1 character (HP/BAB/
save progression), minimal starting gear. Full detail for all of these:
`roadmap_history.md`.

- [ ] Deliberately deferred further: archetype-conflict checking for
      classes (needs a data-model decision on which archetypes mutually
      exclude each other — not yet made; the equivalent question for races
      was resolved in slice 2).

- [ ] **Class-ability computation (`HANDLERS` registry, mirrors
      `rules/race_abilities.py`).** `BaseClassAbility`/`BaseClassAbilityGrant`
      (introduced for Kämpfer's bonus feat, then Waldläufer/Magier/
      Hexenmeister's data corrections — see `todos.md`) are composition-only
      today: which abilities a class/archetype/school/bloodline choice
      grants, and at what level, is real data, gated correctly by level and
      by `option_choice_id` (`sheet.py`'s `_build_class_features`) — but no
      ability's actual mechanical effect is computed anywhere. Concretely
      inert right now: Kämpfer's Rüstungstraining/Waffentraining/Tapferkeit
      numbers, Waldläufer's Erzfeind/Bevorzugtes-Gelände bonuses, all 26 of
      Magier's arcane-school powers (flat bonuses like Bezauberndes
      Lächeln's +2 Bluffen/Diplomatie/Einschüchtern, level-scaling ones like
      Starke Zauber's spell-damage bonus, and per-day-use pools like "3 + IN-
      Modifikator Mal pro Tag" abilities such as Säuregeschoss), and all 60
      of Hexenmeister's bloodline powers across its 10 bloodlines (same
      three shapes again: flat bonuses like Dämonische Blutlinie's Stärke
      des Abyss, level-scaling ones like Abnormale Blutlinie's Ungewöhnliche
      Anatomie, and per-day-use pools like Säurestrahl). Needs a
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
- [ ] **"Pick from a restricted list" unification** (feat pools, ability
      pools, spell pools, deterministic per-choice spell grants — generalizes
      past Kämpfer's hardcoded "combat" filter). Schema and seed data
      (phases 1–4) are fully in; validation/enforcement (phases 5–6) is
      still open. Full design rationale (the four table shapes), the
      per-class seeding history, and bugs found along the way are archived
      in `roadmap_history.md` (section "Pick from a restricted list
      unification — design + phases 1–4"). Still open:
      5. [ ] Backend: extend creation's feat validation to check aggregate
         eligibility counts, not just the total; expose resolved eligibility
         (per-character for Hexenmeister, since it depends on the chosen
         bloodline — same resolution shape as `_build_class_features`'s
         `option_choice_id` filtering). Extend the same validation to
         repeated ability-pool picks (Trick) using `grant_id`.
      6. [ ] Frontend: replace `LevelFeatStep.tsx`'s hardcoded `f.type ===
         'combat'` with a lookup against the resolved eligibility from step
         5; optionally surface a hint in `FeatsStep.tsx` at creation ("must
         include N combat feats").
      Also still open, out of scope for this effort: Kämpfer's
      Waffentraining/Waffenmeisterschaft (needs a populated weapon catalog),
      Magier's familiar-type choice under Arkane Verbindung, and the
      animal-companion branch of Waldläufer's Bund des Jägers — all three
      need a new catalog concept (weapons/familiars/animal companions), not
      just another `BaseClassOptionGroup`.
- [ ] **Class source-page fetch/preprocess tooling.** Every class data pass
      so far (Kämpfer, Waldläufer, Magier, Hexenmeister — see `todos.md`)
      manually curled the class's page from
      <http://prd.5footstep.de/Grundregelwerk/Klassen/…>, converted it with
      `html2text`, and read the result — repeated, ad-hoc, and wasteful: the
      Hexenmeister fetch alone was ~190 KB of HTML that html2text turned
      into 930 lines of plain text, of which the first ~200 were the
      site-wide nav sidebar (`Übersicht > Grundregelwerk > Klassen > …`,
      repeated on every single page) contributing nothing but token cost.
      The site's TLS cert also doesn't match its hostname (shared hosting —
      cert is for `*.your-server.de`), which is why plain `WebFetch` fails
      outright and a raw `curl -k`/`requests(verify=False)` fetch is needed
      instead; worth a one-line comment at the call site noting this is a
      deliberate, scoped skip (a docs mirror, not a service handling
      secrets) rather than a pattern to copy elsewhere.

      A small `scripts/fetch_prd_page.py` (or similar, root-level next to
      `dev.sh`) should: take a page path or full URL, fetch with cert
      verification disabled, decode as ISO-8859-1 (the site's actual
      encoding — `requests`/`curl` autodetection gets this wrong), strip the
      repeated nav sidebar/footer/license boilerplate before running
      `html2text` (or reimplement the bits of it actually needed — table
      layout survives html2text reasonably but is still fragile, see the
      Hexenmeister level-table parsing glitch below), and write the cleaned
      text to a local cache (e.g. `scratchpad/prd_cache/<slug>.txt` or
      similar, gitignored) keyed by page path so a re-run during the same
      data-entry pass doesn't refetch. Should also flag known parser
      footguns rather than silently mis-parsing: the Hexenmeister fetch's
      "Tabelle: Hexenmeister" (BAB/saves) table silently *dropped* the 1st-
      level row entirely (html2text's table-to-text conversion choked on
      that particular row), only caught because the level-1 text elsewhere
      on the page was cross-checked against it — a preprocessing pass
      should at minimum sanity-check that a level/stufe table's row count
      matches the class's expected level range (1–20) and warn if not.
      Same tool should work for the other outstanding source pages this
      project already links to (feats index, spell lists, races, prestige
      classes) so it isn't Klassen-specific.

### 4. Items / Inventory
Done — armor/shield gear table + equip slots, gear CRUD endpoints, shared
modifier/bonus-stacking design, real computed AC. Full detail:
`roadmap_history.md`.

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
