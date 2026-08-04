import type { AbilityKey } from './abilities';

export interface ClassProgressionEntry {
  id: string;
  className: string;
  level: number;
  /** Zero or more non-conflicting archetypes applied to this class (Requirement 2.1). */
  archetypes: string[];
  options: Record<string, string[]>;
  /** Whether this is the character's favored class — leveling up in it
   *  grants a choice of +1 HP or +1 skill rank (Fertigkeiten erwerben,
   *  http://prd.5footstep.de/Grundregelwerk/Fertigkeiten-erwerben). */
  isFavored: boolean;
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
  /** Alternate-trait names (not the flex ability-score pick) — needed to
   *  tell whether a race's skill-point-per-level bonus (e.g. Human's
   *  Geschult) was traded away; see `raceGrantsSkillBonusPerLevel`. */
  altTraits: string[];
  skillRanks: Record<string, number>;
  spellsKnown: Record<string, string[]>;
  history: HistoryEntry[];
}
