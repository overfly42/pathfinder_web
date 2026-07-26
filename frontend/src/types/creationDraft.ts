import type { AbilityKey } from './abilities';

export type Gender = '' | 'maennlich' | 'weiblich';

export type PointBudget = 10 | 15 | 20 | 25;

export interface ClassRow {
  id: string;
  className: string;
  level: number;
  archetype: string;
  /** classOptionSelections: option group key -> chosen values (e.g. domain -> ['Sonne','Tod']) */
  options: Record<string, string[]>;
}

export interface DraftGearItem {
  id: string;
  name: string;
  qty: number;
  price: number;
}

export interface CreationDraft {
  name: string;
  gender: Gender;
  raceId: string | null;
  flexAbility: AbilityKey | null;
  altTraits: string[];
  classRows: ClassRow[];
  abilityScores: Record<AbilityKey, number>;
  pointBudget: PointBudget;
  skillRanks: Record<string, number>;
  feats: string[];
  traits: string[];
  /** spellSelections: class name -> chosen spell names */
  spellSelections: Record<string, string[]>;
  gold: number;
  gear: DraftGearItem[];
}
