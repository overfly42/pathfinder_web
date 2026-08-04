import type { AbilityKey } from './abilities';

export type LevelUpTarget =
  | { mode: 'existing'; classId: string }
  | { mode: 'new'; className: string; archetypes: string[]; options: Record<string, string[]> };

export interface LevelUpDraft {
  target: LevelUpTarget;
  /** Player-entered HP roll for this new level — never auto-maxed (a level-up
   *  is by definition not the character's very first level). */
  hitPoints: number | null;
  /** Recurring per-class level-gated choices (CLASS_LEVEL_OPTIONS), keyed by group key. */
  existingLevelOptionSelections: Record<string, string[]>;
  abilityIncrease: AbilityKey | null;
  /** Skill key -> whether it received its +1 rank this level. */
  skillIncreases: Record<string, boolean>;
  newFeat: string | null;
  /** Fighter-only bonus combat feat granted on even levels, independent of newFeat. */
  newBonusFeat: string | null;
  /** feat *name* (newFeat/newBonusFeat) -> chosen weapon/skill id or spell
   *  school, for a feat whose `subChoiceType` requires one — same shape as
   *  `CreationDraft.featSubChoices`, but keyed by name since newFeat/
   *  newBonusFeat are names here, not ids. */
  featSubChoices: Record<string, string>;
  newSpell: string | null;
}
