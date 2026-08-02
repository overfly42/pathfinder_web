import type { AbilityKey } from './abilities';

export type Gender = '' | 'maennlich' | 'weiblich';

export type PointBudget = 10 | 15 | 20 | 25;

export interface ClassRow {
  id: string;
  className: string;
  level: number;
  /** Zero or more non-conflicting archetypes applied to this class (Requirement 2.1). */
  archetypes: string[];
  /** classOptionSelections: option group key -> chosen values (e.g. domain -> ['Domäne der Sonne','Domäne des Todes']) */
  options: Record<string, string[]>;
}

export interface DraftGearItem {
  id: string;
  /** `BaseItem.id` this entry was picked from — what's actually submitted to
   *  the backend (`CharacterCreate.gear`). `name`/`price` are copied in at
   *  pick time purely so the summary/inventory list can render without
   *  re-looking them up in the catalog. */
  itemId: string;
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
  /** Chosen feat ids (BaseFeat.id), not names. */
  feats: string[];
  traits: string[];
  /** spellSelections: base_class_id -> chosen spell ids (grade-0 spells for
   *  arcane-prepared classes are mandatory-but-implicit, not stored here —
   *  see `spellIdsForSubmission` in creationCalculations.ts). */
  spellSelections: Record<string, string[]>;
  gold: number;
  gear: DraftGearItem[];
}
