import type { CreationOptions } from './creationOptions';
import type { ClassLevelOptions } from './classLevelOptions';

/** Only the reference data level-up needs — no races/pointBuyCosts
 *  (creation-only concepts). `items`/`spellSchools` are needed for the same
 *  feat sub-choice dropdowns (weapon/school) creation's `FeatsStep.tsx` uses. */
export type LevelUpOptions = Pick<
  CreationOptions,
  'classes' | 'feats' | 'skills' | 'abilities' | 'spellsByClass' | 'items' | 'spellSchools'
> & {
  classLevelOptions: ClassLevelOptions;
};
