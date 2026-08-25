# Pathfinder 1e Web Character
This Project shall provide a multilingual Pathfinder (at least german) web site. It will be designed to server the players as an easy to handle tool for
- character creation
- character leveling
- playing

The whole system will be designed in a way, only currently relevant elements are added. If this are classes, feats or spells.

**The System is designed to run only local**
# Architecture
The system posesses of serveral parts:
- Web UI for Player interaction
- Backend service to serve the frontend and store the data
- Database

Backend and Database are created as docker images for easy migration between systems.

As this is created as local only system, without any valid data, beside of the username, there is no security done by intention.
## Web UI
The Web UI is the interface to the user. It shows the character sheet, and the options. Available.
For this there are some different Screens:
### Main Screen
The Main screen is split into 3 Parts. On the left half of the screen, there is the players sheet. On the right top corner, there is the current available actions, such as use a daily power. In the lower right corner there are modifications available such as Conditions and Spells. 
### Level Up Screen
In this sepearte Screen, the single elements of the character become editable. When leveling up, at first a class must be selected, than any further decisions need to be taken, after confirmation, this could not be undone. 
### Inventory screen
While the base inventory is part of the players main sheet, adding new Items is done here. There could be regular predefined items, or custom items, which option to be found, self crafted or bought.
### Item Screen
When adding a new (magic) Item it need to be defined, if it is not one of the predefined ones. For this weapons and amor need to be customized with features.
## Backend
The backend interacts with the storage systems and provides objects rather than table data to the frontend. Further more it provides the information what actions / options are legal at the current state of character.
The backend is the central rules engine and application core of the system. It owns the character state and progression logic, and it provides structured domain objects to the frontend instead of exposing raw database rows. It also evaluates which actions and options are legally available for a character based on their current state, including class features, prerequisites, equipment, effects, and other game rules.

Because Pathfinder contains many special rules, the backend must be designed as an extensible rules system. Classes, feats, spells, abilities, effects, and prerequisites should be added as reusable rule elements rather than being fully hard-coded from the beginning. This allows the system to grow step by step, starting with the core character workflow and later adding more detailed rules and content.

Concretely: which rule elements apply to a character (race, class features, feats, effects, ...) is tracked as data — catalog tables plus grant/replacement relations, e.g. `BaseRaceAbility`/`RaceAbilityGrant`/`RaceAbilityReplacement` for races. Computing what each one actually does is not modeled as further data columns, even for bonuses that look flat (Pathfinder has too many superficially-simple bonuses that turn out to be conditional, e.g. Skill Focus granting +3 normally but +6 at 10+ ranks). Instead, each rule element's effect is resolved by a small handler function, looked up by the element's own UUID (see `CLAUDE.md`). This keeps "what exists and what's granted to what" in data while "how it's computed" stays in code, without needing a schema migration every time a new kind of exception shows up.

### Request pipeline: from stored character to full sheet

Reading a character (`GET /api/characters/{id}`, `backend/app/sheet.py`'s `build_character_sheet`) follows the same sequence every time, regardless of which rule elements are actually involved. Decided 2026-08-10; fully implemented as of 2026-08-25 (`rules/context.py`'s `CharacterContext` is real and every handler family takes it — see the note at the end of this section for what changed since the original design, kept for history).

1. **Collect composition, scoped to the character's current state.** Which race/class/feat/trait/spell/item/active-effect ids apply — and, for anything level-gated (class features, a Fighter's recurring bonus feat, ...), only the grants whose own `level` is at or below what the character has actually reached in that class. A level-2 Barbarian only pulls in level-1 and level-2 grants for Barbarian, not level-3+. This is plain data lookups (`Character.feat_ids`/`trait_ids`/`classes`/`effects`/... in `backend/app/models/character.py`, `BaseClassAbilityGrant.level <=` the class's level in `sheet.py`'s `_build_class_features`) — no rule logic runs yet, it's just gathering which UUIDs are in play. A character, at this level, really is nothing more than a bag of UUIDs (which race/class/feats/traits/spells/items/effects it has) plus a handful of raw numbers (ability scores, skill ranks, HP) — everything else on the sheet is *derived* from that bag by the steps below.
2. **Build the raw `CharacterContext`** (`rules/context.py`) — a single dataclass holding every piece of a character's own state a handler could plausibly need to compute its effect: raw ability scores, `skill_ranks: dict[BaseSkill.id, int]`, levels/classes, the composition ids from step 1 (feat/trait/granted-ability/active-effect ids), and equipped gear — straight off the `Character`/`CharacterLevel`/... rows, no rule logic yet. One typed object every handler is called with, instead of each `sheet.py` function threading its own slice of loose local variables by hand.
3. **Resolve every collected UUID exactly once, in one flat pass** — looked up against that ability's own handler, called with the *same* raw `CharacterContext` from step 2, never a mutated character. No target is privileged and no handler family goes "first" — every handler decides its output from raw composition data alone (its own instance/level/chosen-sub-option, or raw skill ranks for something like Skill Focus's +3-vs-+6-at-10-ranks threshold, `CLAUDE.md`'s own example), never from another handler's *computed* result. An id with no handler anywhere (e.g. Darkvision, or a race's size trait today) just passes through as flavor text with no computed effect.

   "Its own handler" is not one single dict, though — `rules/handlers.py` merges **several** sibling registries, one per *shape* of effect, all keyed into the same globally-unique ability-UUID space so a given id lands in exactly the ones its actual effect needs:
   - `HANDLERS: dict[UUID, Callable[[CharacterContext], list[Modifier]]]` — the common case, a flat bonus feeding step 4 below.
   - `NATURAL_ATTACK_HANDLERS` (a bite/claw attack), `WEAPON_BONUS_DAMAGE_HANDLERS` (an extra melee damage die), `WEAPON_PROFICIENCY_HANDLERS` (a fixed set of weapon ids, unconditional — not even a `Callable`) — consumed directly by `sheet.py`'s weapon-attack building, not through `stack()`.
   - `SITUATIONAL_SKILL_HANDLERS` (a conditional skill note, rendered as text rather than folded into a number) — see that dict's own docstring for why.
   - `DAILY_LIMITS`, `TEMP_HP_GRANTS`, `ON_END`, `SPELL_SLOT_DELTAS` — smaller special-purpose lookups (uses/day, temp HP on activation, what condition an effect ends into, a spell-slot-table adjustment) each read by exactly one other piece of code that needs that one number.

   An ability with no real mechanical effect appears in none of these. One with a genuinely computed effect appears in whichever one (rarely more than one) matches its effect's shape — never in `HANDLERS` "by default" just because that's the first one anyone thinks of. **Consequence:** "does ability/feat/trait X have a computed effect at all" is its own question, not the same as "is X in `HANDLERS`" — answered once, centrally, by `rules/handlers.py`'s `has_mechanical_effect(ability_id)`, which checks every registry above. Every consumer of that question (the sheet's/catalog's "Nur Text" badge, today; a future prerequisite check, tomorrow) must go through that one function rather than re-deriving its own partial subset — checking only `HANDLERS` directly mislabeled Waffenfinesse/Waffenfokus, Kensai's own weapon-choice/Weapon-Focus grant, and Elf's "Elfische Waffenvertrautheit" as flavor-only ("Nur Text") independently, on three separate occasions, before this was fixed for good on 2026-08-25.
4. **Group every returned `Modifier` (from `HANDLERS` only), by target, and `stack()` each target's pool** (`ModifierTarget.SCORE`/`AC`/`SPEED`/`SAVE_*`/`SKILL`/`ATTACK`/`DAMAGE`/`CONCENTRATION`) — one number per target, still detached from any base value. The other registries listed in step 3 skip this step entirely; each is consumed directly in whatever shape it already has (a `NaturalAttack` becomes a weapon-section row, a `WEAPON_PROFICIENCY_HANDLERS` id set gets unioned into `chosen_weapon_ids`, ...).
5. **Apply each target's stacked value on top of its base formula** to get the final sheet numbers — 10 + Dex mod + `stack(AC modifiers)` for AC, the class save-progression value + ability mod + `stack(SAVE_* modifiers)` for a save, caster level + casting-ability mod + `stack(CONCENTRATION modifiers)` for a Konzentrationswurf, and so on. This is ordinary sequential arithmetic in `sheet.py`, nothing more: it computes `ability_mods` before the line that needs them to build the `saves` list, and total land speed before `jump_skill_bonus(total_land_speed)`, the same way any function computes an intermediate value before using it. That ordering is real, but it's local to `sheet.py`'s own formulas, not a rule the handler-calling contract in step 3 has to enforce — no handler anywhere currently reads another handler's stacked output as its own input, so step 3 doesn't need phases. (If a future handler ever does need a resolved ability modifier as an input to its *own* decision logic — e.g. a class ability whose bonus scales directly off the character's effective Wisdom modifier, rather than off raw levels/ranks — *that* handler would gain a dependency step 3 doesn't have today, and this section should be revisited then; not designed for speculatively now.)
6. **Assemble the result**: the fully computed character (abilities, saves, BAB/CMB/CMD, AC, skills, ...) plus, eventually, the set of actions/options legal at the character's current state. That last part — `"actions"` in the sheet response — is deliberately still an empty stub; it's roadmap slice 6 ("Possible actions / legality checks"), not built yet.

**History (kept for context, no longer current):** as of 2026-08-10 this was still a target design — no `CharacterContext` existed yet, `rules/race_abilities.py`/`rules/speed.py`'s `HANDLERS` took zero arguments, and `rules/effects.py`'s `EFFECT_HANDLERS` was a separate registry with its own narrower signature (only that effect's own `list[CharacterEffect]` instances). All of that migrated to the uniform signature described above by 2026-08-11 (`roadmap.md`'s "Uniform CharacterContext handler signature"), and `EFFECT_HANDLERS` merged into `rules/handlers.py`'s `HANDLERS` once the signature gap that justified keeping it separate closed.

This approach keeps the implementation maintainable: the first version can focus on character creation, leveling, and basic sheet data, while later iterations add more specific rules and features without requiring a redesign of the whole backend.
# Database
The Database is heart of the backend. For this it is composed of tree main parts:
- Definitions (Classes, Feats, etc.)
- Character data (Name, Stats, etc.)
- descriptions


## Explaination
One, and only one to zero or many: ||--o{
One to zero or |o--o{

```mermaid
erDiagram
    BaseClasses ||--o{ BaseClassLevelAbility: has
    BaseClasses {
        uuid id
        uuid arch_class_of
        int hit_dice
        bool wil_save
        bool fort_save
        bool ref_save
        float bab_progression
        string name
        string role
        string casting_ability
        string spell_tradition
    }
    BaseClasses |o--o{ BaseClasses:has
    BaseClassLevelAbility ||--o{ BaseClassAbilites : provies
    BaseClassLevelAbility {
        uuid class_id
        uuid ability_id
        int level
        string type
        string description
        string name
    }
    BaseSkill {
        uuid id
        string name
        string ability
    }
    BaseClassSkill  {
        uuid skill_id
        uuid base_class_id
    }
    %% BaseAttribute deliberately not implemented: ability scores are a
    %% fixed 6-value code (ST/GE/KO/IN/WE/CH) used as a plain string
    %% everywhere in the codebase, not a database-backed table.
    BaseRace {
        uuid id
        string code
        string name
        string short_description
    }
    BaseRaceAbility {
        uuid id
        string name
        string description
    }
    RaceAbilityGrant {
        uuid id
        uuid race_id
        uuid ability_id
        bool is_alternate
    }
    RaceAbilityReplacement {
        uuid id
        uuid base_race_id
        uuid ability_id
        uuid replaces_ability_id
    }
    BaseRace ||--o{ RaceAbilityGrant : grants
    BaseRaceAbility ||--o{ RaceAbilityGrant : "granted via"
    BaseRace ||--o{ RaceAbilityReplacement : "defines swaps for"
    BaseRaceAbility ||--o{ RaceAbilityReplacement : "as alternate"
    BaseRaceAbility ||--o{ RaceAbilityReplacement : "as replaced"
    BaseFeat {
        uuid id 
        string name
        string description
    }
    BaseRequirements {
        uuid requirement_id
    }
    BaseFeatRequirements{
        uuid requirement_id
        uuid feat_id
    }
    BaseRequiredFeat{
        uuid requirement_id
        uuid feat_id
    }
    BaseRequiredSkill{
        uuid requirement_id
        uuid skill_id
        int value
    }
    BaseRequiredClass{
        uuid requirement_id
        uuid class_id
        int value
    }
    User {
        uuid id
        string name
    }
    Character {
        uuid id
        uuid user_id
        uuid race_id
        uuid prefered_class
        int current_hit_points
        string name
    }
    Character ||--o{ BaseClasses : has
    Character ||--o{ BaseRace : has
    Character ||--o{ User:has
    CharacterAttribute {
        uuid attribute_id
        uuid character_level_id
        int value
    }
    Character ||--o{ Attribute :has
    CharacterLevel{
        uuid id
        int level
        uuid character_id
        uuid base_class_id
        int hit_points
    }
    CharacterSkillRank{
        uuid level_id
        uuid skill_id
        int ranks
    }
    CharacterFeat{
        uuid level_id
        uuid feat_id
    }
    CharacterItems{
        uuid id
        string name
        uuid character_id
        string type
    }
    BaseItemAbility{
        uuid id
        string name
    }
    CharacteritemAbility{
        uuid character_item_id
        uuid character_item_ability_id
    }
    BaseSpell {
        uuid id
        string name
        string school
        string description
    }
    BaseSpellComponents {
        uuid spell_id
        string tradition
        bool verbal
        bool somatic
        bool material
        string material_description
        bool focus
        string focus_description
    }
    BaseSpell ||--o{ BaseSpellComponents : "components per tradition"
    BaseClassSpell {
        uuid base_class_id
        uuid spell_id
        int grade
    }
    BaseClasses ||--o{ BaseClassSpell : offers
    BaseSpell ||--o{ BaseClassSpell : "at grade"
    BaseClassSpellsKnown {
        uuid base_class_id
        int level
        int grade
        int count
    }
    BaseClasses ||--o{ BaseClassSpellsKnown : "known/accessible per level"
    CharacterSpell {
        uuid level_id
        uuid base_class_id
        uuid spell_id
    }
    CharacterLevel ||--o{ CharacterSpell : knows

```

# Technologies
There are several technologies used throuout such a complex system. For this we will use:
- React for the frontend
- FastAPI as backend server
- PostgresSQL with Vector extension for the backend
- Docker / Podman as server container

# Running locally (current scaffold stage)
The `frontend/` and `backend/` directories hold the current React + FastAPI scaffold (character sheet, character-creation wizard, level-up wizard — all served from static JSON fixtures, no database yet).

Both together, via the root `dev.sh` script (starts backend + frontend, Ctrl+C stops both):
```bash
./dev.sh
```
It uses the project venv at `~/python/pathfinder_web` by default (override with `PATHFINDER_VENV`); run `pip install -r backend/requirements.txt` there first if you haven't. `npm install` in `frontend/` is still needed once, or after `package.json` changes.

Or start them separately:

**Backend** (FastAPI, port 8000):
```bash
cd backend
source ~/python/pathfinder_web/bin/activate   # project venv, see CLAUDE.md
pip install -r requirements.txt               # first time / after requirements.txt changes
uvicorn app.main:app --reload --port 8000
```

**Frontend** (React + Vite, port 5173):
```bash
cd frontend
npm install    # first time / after package.json changes
npm run dev
```

Then open `http://localhost:5173/` in a browser — that's the only port you need to visit. Vite proxies `/api/*` requests to the backend on `http://localhost:8000` (see `frontend/vite.config.ts`; overridable via a `VITE_API_URL` env var if you want the frontend to hit a different backend origin directly). Available routes: `/` (character sheet), `/create` (character creation), `/levelup/:characterId` (level-up).

# API Endpoints

All entity ids in path parameters (`character_id`, `user_id`, `item_id`, `effect_id`, `spell_id`, `slot_id`, etc.) are UUIDs, consistent with the `uuid id` fields in the ER diagram above. Tracked with implementation status in `todos.md`.

## Reference data

Mostly static-fixture GETs (`backend/app/main.py`, backed by JSON files in `backend/app/fixtures/`, not a database) — except races (real database tables as of roadmap slice 2, `backend/app/routers/races.py`/`backend/app/models/race.py`), classes (a real `BaseClass` table as of roadmap slice 3, `backend/app/models/base_class.py` — `name` (a FK target for `CharacterLevel.base_class_id`), `hit_dice`, and a self-referencing `arch_class_of` FK: null for a root class, or the parent's id for one archetype variant of it; skill points/spell type/archetype-and-option-group *definitions* still live in `classes.json`, joined by name), and skills (real `BaseSkill`/`BaseClassSkill` tables, also as of roadmap slice 3, `backend/app/models/skill.py` — identity only (name + governing ability code), pulled out of the old `skills.json` fixture so `classSkills` has a real FK target and skill names have a stable id a future translation layer can key off of; `/api/classes`' `classSkills` field is overwritten with real skill ids from `BaseClassSkill` at read time, replacing the old fixture-key strings):

| Method | Path | Backed by |
|---|---|---|
| GET | `/api/races` | database (`BaseRace`/`BaseRaceAbility`/`RaceAbilityGrant`/`RaceAbilityReplacement`) |
| GET | `/api/classes` | fixture, except `id`/`classSkills`/`optionGroups`/`bonusFeatLevels`/`castingAbility`/`spellTradition`/`spellsKnownByLevel`/`babProgression`/`fortSave`/`refSave`/`willSave` (database — `BaseClass`/`BaseClassSkill`/`BaseClassOptionGroup`/`BaseClassOptionChoice`/`BaseClassAbilityGrant`/`BaseClassSpellsKnown`) |
| GET | `/api/feats` | database (`BaseFeat`) |
| GET | `/api/traits` | database (`BaseTrait`) |
| GET | `/api/skills` | database (`BaseSkill`) |
| GET | `/api/abilities` | fixture |
| GET | `/api/spells` | database (`BaseSpell`) |
| GET | `/api/spells-by-class` | database (`BaseClassSpell`) |
| GET | `/api/point-buy-costs` | fixture |
| GET | `/api/items` | fixture |
| GET | `/api/effects` | fixture |
| GET | `/api/class-level-options` | fixture |
| GET | `/api/characters/{character_id}` | fixture for the two mock characters, database for real (slice 2) characters |
| GET | `/api/characters/{character_id}/progression` | fixture |

## User management (implemented — database-backed)

The first slice with a real table + write endpoints (`backend/app/models/user.py`,
`backend/app/routers/users.py`); `AppHeader`'s user picker and "+ Neuer Nutzer"
form call these instead of local state:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/users` | create a user |
| GET | `/api/users` | list users, for the user picker |
| GET | `/api/users/{user_id}/characters` | list a user's characters, for the header's character picker |
| PATCH | `/api/users/{user_id}` | rename a user (no frontend UI wired to this yet) |

## Character management (implemented — database-backed, roadmap slice 2)

`backend/app/models/character.py`, `backend/app/routers/characters.py`. Character row (name, user,
race, ability scores, nullable current_hit_points) plus per-level history: `CharacterLevel` (one row
per character level — `character_id`, `level`, `base_class_id`, nullable `hit_points`) rather than a
`class_name`/`level` pair on `characters`, so multiclassing needs no later schema change (roadmap
slice 3's class-selection item). `base_class_id` always points at a root `BaseClass` row — archetype
selection instead lives in `CharacterClass` (`character_classes`: character_id, base_class_id,
is_favored), one row per class-or-archetype the character has (roots and archetypes share the
`base_classes` catalog, so any number of archetypes per class is just more rows, no nested table);
`is_favored` only applies to root rows. `CharacterClassOption` (character_id, base_class_id,
group_key, choice) stores class option-group picks (domain, bloodline, mystery, school, favored
enemy/terrain, ...) — one row per chosen value, keyed by the root class's id.
`Character.level`/`Character.classes` are computed properties, not stored columns.
`POST /api/characters` takes `classes: [{class_name, level, archetypes, options}, ...]` — zero or
more archetypes per class-taken (see `resolve_root_class`/`resolve_archetype`/`_validate_options` in
`routers/characters.py`); whether two chosen archetypes actually conflict isn't validated (see
`todos.md`). Skills/feats/traits/computed AC are still a later "thick" pass. The creation wizard's
`SummaryStep` calls `POST /api/characters` for real instead of showing a mock confirmation banner;
the created character
now appears in the header's character picker (`GET /api/users/{user_id}/characters`,
`frontend/src/state/AppStateContext.tsx`'s `dbCharacterIds`), but selecting it on the main character
sheet shows a placeholder rather than a full sheet — the thin/computed shape has none of the
rich fixture fields (`abilities`, `gear`, `spellsKnown`, ...) yet (needs the thick pass).

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/characters` | finalize the character-creation wizard |
| GET | `/api/characters/{character_id}` | fetch a character (merged into the existing mock-fixture endpoint) |
| PATCH | `/api/characters/{character_id}` | rename a character |
| DELETE | `/api/characters/{character_id}` | delete a character |

## Not yet implemented

The frontend (`frontend/src/api/client.ts`) has `apiGet`/`apiPost`/`apiPatch`/`apiDelete`,
but only the user-management and character-management endpoints above are wired up so far —
every other user interaction below that changes data is presently local React state only
and is lost on reload.

**Character management**
| Method | Path | Purpose |
|---|---|---|
| PUT | `/api/characters/{character_id}/draft` | (optional) autosave the creation wizard mid-flight |

**Level-up**
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/characters/{character_id}/level-up` | finalize the level-up wizard: applies class/HP/feat/skill/spell changes |
| GET | `/api/characters/{character_id}/history` | level-up/change history (`requirements_v2.md` §2 requires this; no supporting data model exists yet) |

**Vitals/combat**
| Method | Path | Purpose |
|---|---|---|
| PATCH | `/api/characters/{character_id}/hp` | apply damage/heal to current HP |

AC, initiative, etc. should be backend-computed from equipped items + ability modifiers rather than written directly; today AC is static fixture data with no recompute logic anywhere.

**Effects, conditions, time**
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/characters/{character_id}/effects/{effect_id}/activate` | activate a catalog condition/effect on the character |
| DELETE | `/api/characters/{character_id}/effects/{active_effect_id}` | manually remove/dispel an active effect early |
| POST | `/api/characters/{character_id}/effects/custom` | add a free-form effect with a manually chosen duration |
| POST | `/api/characters/{character_id}/advance-time` | advance time by round/minute/hour, counting down active effect durations |
| POST | `/api/characters/{character_id}/rest` | day change / rest — reset spells and effects (kept separate from `advance-time` so a short rest and a full day change can eventually diverge) |

**Spells**
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/characters/{character_id}/spells/{spell_id}/cast` | mark a known/prepared spell as used for the day |
| POST | `/api/characters/{character_id}/spells/{spell_id}/prepare` | prepare a spell (server enforces `maxPrepared` per grade) |
| DELETE | `/api/characters/{character_id}/spells/{spell_id}/prepare` | unprepare a spell |
| POST | `/api/characters/{character_id}/spellbook` | add a spell to the spellbook during play (`requirements_v2.md` §2.2: managed like inventory, not just at creation/level-up) — arcane-prepared classes only, uncapped; spontaneous casters only learn new spells at level-up, divine-prepared casters already have the full list |
| DELETE | `/api/characters/{character_id}/spellbook/{spell_id}` | remove a spell from the spellbook |

**Equipment/inventory**
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/characters/{character_id}/gear` | add an inventory item |
| PATCH | `/api/characters/{character_id}/gear/{item_id}` | rename/change quantity, set enhancement bonus, toggle special properties |
| DELETE | `/api/characters/{character_id}/gear/{item_id}` | remove an inventory item |
| PUT | `/api/characters/{character_id}/slots/{slot_id}` | equip/unequip an item into an equipment slot (should validate the item is in inventory and trigger AC recompute) |

**Background/notes**
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/characters/{character_id}/background` | backstory, goals/motivations, NPC relationships |
| PUT | `/api/characters/{character_id}/background` | save backstory/goals/relationships (`requirements_v2.md` §2.4 — no frontend UI exists for this yet either) |

**Rules/reference**
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/compendium/search?q=` | full-text rule lookup across feats/spells/class features; today's in-sheet search only indexes the loaded character's own data, not a rules database |