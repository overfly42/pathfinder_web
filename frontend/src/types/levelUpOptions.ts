import type { CreationOptions } from './creationOptions';
import type { ClassLevelOptions } from './classLevelOptions';

/** Only the reference data level-up needs — no races/items/pointBuyCosts (creation-only concepts). */
export type LevelUpOptions = Pick<CreationOptions, 'classes' | 'feats' | 'skills' | 'abilities' | 'spellsByClass'> & {
  classLevelOptions: ClassLevelOptions;
};
