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

export interface SkillSpecializationEntry {
  /** Local-only id (React keys/stepper callbacks) — not sent to the backend;
   *  the backend identifies a row by skillId + specializationId/
   *  customSpecialization instead (see `SkillRankSelection`). */
  localId: string;
  skillId: string;
  /** Set when picked from `CreationOptions.skillSpecializations`; mutually
   *  exclusive with `customSpecialization`. */
  specializationId: string | null;
  /** Set when the player typed a specialization not in the catalog;
   *  mutually exclusive with `specializationId`. */
  customSpecialization: string | null;
  ranks: number;
}

export interface CreationDraft {
  name: string;
  gender: Gender;
  raceId: string | null;
  flexAbility: AbilityKey | null;
  altTraits: string[];
  classRows: ClassRow[];
  /** 1st-level favored-class bonus ("hp" | "skill" | a race+class-specific
   *  Advanced Race Guide alternate choice name) for `classRows[0]` — the
   *  favored class, per `create_character`'s "the root of the first
   *  submitted class is favored by default" rule. `null` until chosen;
   *  reset whenever that row's class or the character's race changes,
   *  since a race-scoped alternate choice may no longer be legal. */
  favoredClassBonus: string | null;
  abilityScores: Record<AbilityKey, number>;
  pointBudget: PointBudget;
  /** Opt-in to the "Hintergrundfertigkeiten" alternate rule (+2 skill ranks
   *  per level, spendable only on background skills, see `SkillDef.isBackground`)
   *  — a one-time creation-time choice, persisted server-side and never
   *  resubmitted at level-up (`CharacterProgression.useBackgroundSkills`). */
  useBackgroundSkills: boolean;
  /** Ranks for every skill except Handwerk/Beruf/Auftreten (`SkillDef.
   *  hasSpecialization`) — those live in `skillSpecializations` instead,
   *  since the same skill can appear more than once. */
  skillRanks: Record<string, number>;
  /** One entry per specialization the player has added for a
   *  `hasSpecialization` skill — see `SkillsStep.tsx`. */
  skillSpecializations: SkillSpecializationEntry[];
  /** Chosen feat ids (BaseFeat.id), not names. */
  feats: string[];
  /** feat_id -> the chosen weapon/skill id or spell school string, for feats
   *  whose `FeatDef.subChoiceType` isn't null (Waffenfokus -> a weapon id,
   *  Fertigkeitsfokus -> a skill id, Zauberfokus -> a spell school string) —
   *  see `FeatsStep.tsx`. Only ever holds entries for feats currently in
   *  `feats` that need one. */
  featSubChoices: Record<string, string>;
  traits: string[];
  /** trait_id -> chosen skill id, for traits whose `TraitDef.skillChoiceAbility`
   *  isn't null (Gewitztes Wortspiel -> a CH-based skill id) — see
   *  `TraitsStep.tsx`. Only ever holds entries for traits currently in
   *  `traits` that need one, same convention as `featSubChoices`. */
  traitSkillChoices: Record<string, string>;
  /** spellSelections: base_class_id -> chosen spell ids (grade-0 spells for
   *  arcane-prepared classes are mandatory-but-implicit, not stored here —
   *  see `spellIdsForSubmission` in creationCalculations.ts). */
  spellSelections: Record<string, string[]>;
  gold: number;
  gear: DraftGearItem[];
}
