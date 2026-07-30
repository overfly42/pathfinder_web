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

export interface ItemCatalogEntry {
  name: string;
  price: number;
}

export interface CreationOptions {
  races: RaceOption[];
  classes: ClassDef[];
  feats: FeatDef[];
  traits: TraitDef[];
  skills: SkillDef[];
  abilities: AbilityDef[];
  spellsByClass: Record<string, string[]>;
  pointBuyCosts: Record<number, number>;
  items: ItemCatalogEntry[];
}
