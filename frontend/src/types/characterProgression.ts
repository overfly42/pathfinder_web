import type { AbilityKey } from './abilities';

export interface ClassProgressionEntry {
  id: string;
  className: string;
  level: number;
  archetype: string;
  options: Record<string, string[]>;
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
}
