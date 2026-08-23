import type { CreationOptions } from './creationOptions';
import type { ClassLevelOptions } from './classLevelOptions';

/** Only the reference data level-up needs — no pointBuyCosts (creation-only
 *  concept). `items`/`spellSchools` are needed for the same feat sub-choice
 *  dropdowns (weapon/school) creation's `FeatsStep.tsx` uses; `races` is
 *  needed to check whether the character's race grants a skill-point-per-
 *  level bonus (Human's Geschult) — see `raceGrantsSkillBonusPerLevel`. */
export type LevelUpOptions = Pick<
  CreationOptions,
  'classes' | 'feats' | 'skills' | 'skillSpecializations' | 'abilities' | 'spellsByClass' | 'items' | 'spellSchools' | 'races'
> & {
  classLevelOptions: ClassLevelOptions;
};
