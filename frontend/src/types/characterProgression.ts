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

export interface SkillRankDetail {
  skillId: string;
  specializationId: string | null;
  customSpecialization: string | null;
  ranks: number;
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
  /** Full effective score (race/flex/equipped-gear/ability-damage), not the
   *  raw point-buy base — matches the character sheet's own displayed
   *  score and the backend's own budget-check math (backend `sheet.py`'s
   *  `build_character_progression`); see `effectiveAbilityTotal`. */
  abilityScores: Record<AbilityKey, number>;
  feats: string[];
  traits: string[];
  /** Alternate-trait names (not the flex ability-score pick) — needed to
   *  tell whether a race's skill-point-per-level bonus (e.g. Human's
   *  Geschult) was traded away; see `raceGrantsSkillBonusPerLevel`. */
  altTraits: string[];
  /** Whether this character uses the "Hintergrundfertigkeiten" alternate
   *  rule (+2 skill ranks per level, spendable only on background skills) —
   *  a one-time choice made at creation, never resubmitted at level-up (see
   *  `Character.use_background_skills`'s docstring). Absent for the two
   *  hardcoded mock fixtures, which predate this field — treat as `false`. */
  useBackgroundSkills?: boolean;
  skillRanks: Record<string, number>;
  /** Per-(skill, specialization) breakdown for Handwerk/Beruf/Auftreten —
   *  the granular sibling of `skillRanks` (which collapses every
   *  specialization of a skill into one number). Lets the level-up wizard
   *  pre-seed each existing specialization as its own addable-to row
   *  ("bereits N Ränge") instead of one merged total. Absent for the two
   *  hardcoded mock fixtures, which predate this field. */
  skillRankDetails?: SkillRankDetail[];
  spellsKnown: Record<string, string[]>;
  /** Values currently legal for a favored-class-bonus level-up pick —
   *  `"hp"`/`"skill"` plus this character's race+class-specific alternates
   *  (empty without a favored class). Absent for the two hardcoded mock
   *  fixtures (`progression_1`/`progression_2.json`), which predate this
   *  field. */
  favoredClassBonusOptions?: string[];
  /** `favoredClassBonusOptions` entry name -> its full rules text, for the
   *  race+class-specific alternates only ("hp"/"skill" excluded — the
   *  wizard already has fixed, friendly text for those two). Lets the
   *  summary step show what a picked alternate actually does, not just its
   *  bare name. Absent for the two hardcoded mock fixtures. */
  favoredClassBonusDescriptions?: Record<string, string>;
  /** `favoredClassBonusOptions` entry name -> a short, button-sized label
   *  (e.g. "+1 Rd. Kampfrausch/Tag") for the race+class-specific alternates
   *  only — the picker chips show this directly so a player doesn't need to
   *  hover to understand what a chip does. Absent for the two hardcoded
   *  mock fixtures. */
  favoredClassBonusShortLabels?: Record<string, string>;
  history: HistoryEntry[];
}
