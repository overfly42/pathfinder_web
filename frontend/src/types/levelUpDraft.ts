import type { AbilityKey } from './abilities';

export type LevelUpTarget =
  | { mode: 'existing'; classId: string }
  | { mode: 'new'; className: string; archetypes: string[]; options: Record<string, string[]> };

export interface LevelUpDraft {
  target: LevelUpTarget;
  /** Recurring per-class level-gated choices (CLASS_LEVEL_OPTIONS), keyed by group key. */
  existingLevelOptionSelections: Record<string, string[]>;
  abilityIncrease: AbilityKey | null;
  /** Skill key -> whether it received its +1 rank this level. */
  skillIncreases: Record<string, boolean>;
  newFeat: string | null;
  /** Fighter-only bonus combat feat granted on even levels, independent of newFeat. */
  newBonusFeat: string | null;
  newSpell: string | null;
}
