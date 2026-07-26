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
}

export interface SkillDef {
  key: string;
  name: string;
  ability: AbilityKey;
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
  feats: string[];
  traits: string[];
  skills: SkillDef[];
  abilities: AbilityDef[];
  spellsByClass: Record<string, string[]>;
  pointBuyCosts: Record<number, number>;
  items: ItemCatalogEntry[];
}
