import type { AbilityKey } from './abilities';

export type SpellType = 'none' | 'divine-prepared' | 'arcane-prepared' | 'spontaneous';

export interface RaceTrait {
  name: string;
  desc: string;
}

export interface RaceAltTrait {
  name: string;
  desc: string;
  replaces: string[];
}

export interface RaceOption {
  id: string;
  name: string;
  short: string;
  flex: boolean;
  mods: Partial<Record<AbilityKey, number>>;
  traits: RaceTrait[];
  alt: RaceAltTrait[];
}

export interface ClassOptionChoice {
  name: string;
  /** Minimum level in this root class required to pick this specific named
   *  choice — e.g. a Hexe's Major/Grand Hexes need class level 10/18 (`null`
   *  for a choice with no threshold beyond the group's own occurrence gate).
   *  Backend-enforced (`_validate_options`'s own `min_level` check); the
   *  frontend uses it purely to avoid listing a choice the current row level
   *  can't legally take yet — see `ClassStep.tsx`'s `availableOptionGroups`. */
  minLevel: number | null;
}

export interface ClassOptionGroup {
  key: string;
  label: string;
  max: number;
  choices: ClassOptionChoice[];
  /** Levels (in this root class) at which one more occurrence of this group
   *  opens up, e.g. Kampfrauschkraft's `[2, 4, 6, ..., 20]` — empty for a
   *  one-time creation-time pick (domain/bloodline/school), which is always
   *  available. Backend-computed (`rules/class_options.py`'s
   *  `group_occurrence_levels`) and backend-enforced (`_validate_options`);
   *  the frontend only uses it to decide what to render — see `ClassStep.tsx`. */
  occurrenceLevels: number[];
}

export interface ClassDef {
  /** Root `BaseClass` id — `null` if this class name has no matching DB row
   *  (shouldn't happen for any class.json entry, but the backend allows it). */
  id: string | null;
  name: string;
  archetypes: string[];
  skillPointsBase: number;
  spellType: SpellType;
  classSkills: string[];
  optionGroups: ClassOptionGroup[];
  /** archetype name -> option group key -> occurrence levels that
   *  archetype's own class-feature replacements remove from that group
   *  (e.g. Ork's Narbiger Hexendoktor archetype removes Hexe's level-1
   *  `hexerei` occurrence, since its own Narbenschild ability replaces that
   *  grant) — sparse, only present where an archetype actually changes
   *  something. `ClassStep.tsx`'s `availableOptionGroups` applies this once
   *  an archetype is selected for a class row; `_validate_options` on the
   *  backend enforces the same thing server-side. */
  archetypeOptionOverrides: Record<string, Record<string, number[]>>;
  /** Which levels of this class grant a bonus feat slot (e.g. Kämpfer's 1st
   *  and every even level) — real data from `base_class_ability_grants`, not
   *  a hardcoded class name; see `featMax` in `creationCalculations.ts`. */
  bonusFeatLevels: number[];
  /** 2-letter ability code the class casts with (e.g. IN for Wizard), or
   *  `null` for non-casters. */
  castingAbility: AbilityKey | null;
  spellTradition: 'arcane' | 'divine' | null;
  /** archetype name -> casting ability, sparse (only present where an
   *  archetype actually overrides its parent's, e.g. Hexe's Narbiger
   *  Hexendoktor casts on KO instead of IN — see `BaseClass.
   *  effective_casting_ability` on the backend). Look this up first when a
   *  class row has that archetype selected, falling back to `castingAbility`
   *  otherwise — same "delta the frontend applies once selected" shape as
   *  `archetypeOptionOverrides`. */
  archetypeCastingAbility: Record<string, AbilityKey>;
  /** level (stringified) -> grade (stringified) -> known-spell cap, or
   *  `null` for arcane-prepared classes (grade-*presence*, not count, is the
   *  gate there — see `rules/spells.py` on the backend). Mirrors
   *  `BaseClassSpellsKnown`; keep the frontend budget math in
   *  `creationCalculations.ts` in sync with the backend's `rules/spells.py`. */
  spellsKnownByLevel: Record<string, Record<string, number | null>>;
  /** The class's hit die size (e.g. 10 for a d10) — used by the level-up
   *  wizard's HP-roll step to bound the input; creation never needed this
   *  since it only ever creates level-1 characters (always auto-maxed). */
  hitDice: number | null;
}

export interface SkillDef {
  id: string;
  name: string;
  ability: AbilityKey;
  /** Part of the "Hintergrundfertigkeiten" alternate rule's fixed list
   *  (http://prd.5footstep.de/Alternativregeln/Fertigkeiten/Hintergrundfertigkeiten)
   *  — only relevant when `useBackgroundSkills` is on. */
  isBackground: boolean;
}

export type FeatSubChoiceType = 'weapon' | 'skill' | 'spell_school' | null;

export interface FeatDef {
  id: string;
  name: string;
  description: string;
  type: string;
  /** Which kind of one-off sub-choice this feat needs beyond just taking it
   *  (e.g. Waffenfokus -> "weapon") — see `BaseFeat.sub_choice_type` on the
   *  backend. `null` for the common case of a feat with no further choice. */
  subChoiceType: FeatSubChoiceType;
}

export interface TraitDef {
  id: string;
  name: string;
  description: string;
  /** Plain categorization tag (e.g. "combat", "social", "campaign") — a
   *  character may take at most one trait per area, see `TraitsStep.tsx`. */
  area: string;
}

export interface AbilityDef {
  key: AbilityKey;
  name: string;
}

export type ItemCategory = 'weapon' | 'armor' | 'shield' | 'gear' | 'tool' | 'consumable';

export interface ItemCatalogEntry {
  id: string;
  name: string;
  /** Plain categorization tag (see `BaseItem.category` on the backend) — not
   *  evaluated by any rule logic yet, only used to group/filter the gear
   *  picker (`EquipmentStep.tsx`). */
  category: ItemCategory;
  price: number;
}

export interface SpellDef {
  id: string;
  name: string;
  grade: number;
}

export interface CreationOptions {
  races: RaceOption[];
  classes: ClassDef[];
  feats: FeatDef[];
  traits: TraitDef[];
  skills: SkillDef[];
  abilities: AbilityDef[];
  /** class name -> that class's spell list, sorted by grade then name.
   *  Only present for spontaneous/arcane-prepared classes (divine-prepared
   *  classes have no fixed known-spell list to pick from). */
  spellsByClass: Record<string, SpellDef[]>;
  pointBuyCosts: Record<number, number>;
  items: ItemCatalogEntry[];
  /** Distinct spell schools (`BaseSpell.school` values), sorted — feeds the
   *  picker for feats whose `subChoiceType` is "spell_school" (Zauberfokus,
   *  Mächtiger Zauberfokus). Not its own catalog table on the backend, see
   *  `GET /api/spell-schools`. */
  spellSchools: string[];
}
