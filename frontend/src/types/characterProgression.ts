import type { AbilityKey } from './abilities';

export interface ClassProgressionEntry {
  id: string;
  className: string;
  level: number;
  /** Zero or more non-conflicting archetypes applied to this class (Requirement 2.1). */
  archetypes: string[];
  options: Record<string, string[]>;
}

export interface HistoryEntry {
  id: string;
  date: string;
  description: string;
}

export interface CharacterProgression {
  name: string;
  race: string;
  classes: ClassProgressionEntry[];
  abilityScores: Record<AbilityKey, number>;
  feats: string[];
  traits: string[];
  skillRanks: Record<string, number>;
  spellsKnown: Record<string, string[]>;
  history: HistoryEntry[];
}
