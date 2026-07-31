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

export interface ClassOptionGroup {
  key: string;
  label: string;
  max: number;
  choices: string[];
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
  /** Which levels of this class grant a bonus feat slot (e.g. Krieger's 1st
   *  and every even level) — real data from `base_class_ability_grants`, not
   *  a hardcoded class name; see `featMax` in `creationCalculations.ts`. */
  bonusFeatLevels: number[];
  /** 2-letter ability code the class casts with (e.g. IN for Wizard), or
   *  `null` for non-casters. */
  castingAbility: AbilityKey | null;
  spellTradition: 'arcane' | 'divine' | null;
  /** level (stringified) -> grade (stringified) -> known-spell cap, or
   *  `null` for arcane-prepared classes (grade-*presence*, not count, is the
   *  gate there — see `rules/spells.py` on the backend). Mirrors
   *  `BaseClassSpellsKnown`; keep the frontend budget math in
   *  `creationCalculations.ts` in sync with the backend's `rules/spells.py`. */
  spellsKnownByLevel: Record<string, Record<string, number | null>>;
}

export interface SkillDef {
  id: string;
  name: string;
  ability: AbilityKey;
}

export interface FeatDef {
  id: string;
  name: string;
  description: string;
  type: string;
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
}
