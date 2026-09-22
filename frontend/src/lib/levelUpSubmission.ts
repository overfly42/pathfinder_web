import type { CharacterProgression } from '../types/characterProgression';
import type { FeatDef } from '../types/creationOptions';
import type { LevelUpDraft } from '../types/levelUpDraft';
import type { LevelUpOptions } from '../types/levelUpOptions';
import { getReceivingClassAndLevel, getReceivingClassName } from './levelUpCalculations';

interface FeatSelectionBody {
  feat_id: string;
  chosen_weapon_id: string | null;
  chosen_skill_id: string | null;
  chosen_skill_id_2: string | null;
  chosen_spell_school: string | null;
  chosen_manifestation: string | null;
}

function featSelection(
  name: string | null,
  candidates: FeatDef[],
  subChoices: Record<string, string>,
  subChoices2: Record<string, string>,
): FeatSelectionBody | null {
  if (!name) return null;
  const feat = candidates.find((f) => f.name === name);
  if (!feat) return null;
  const subChoice = subChoices[name];
  const isSkillKind = feat.subChoiceType === 'skill' || feat.subChoiceType === 'skill_pair';
  return {
    feat_id: feat.id,
    chosen_weapon_id: feat.subChoiceType === 'weapon' ? subChoice ?? null : null,
    chosen_skill_id: isSkillKind ? subChoice ?? null : null,
    chosen_skill_id_2: feat.subChoiceType === 'skill_pair' ? subChoices2[name] ?? null : null,
    chosen_spell_school: feat.subChoiceType === 'spell_school' ? subChoice ?? null : null,
    chosen_manifestation: feat.subChoiceType === 'manifestation' ? subChoice ?? null : null,
  };
}

/** Shapes a completed level-up wizard draft into `POST .../level-up`'s body
 *  (`schemas.character.LevelUp` on the backend) — mirrors
 *  `creationCalculations.ts`'s `featSelectionsForSubmission`, but resolves
 *  feats/spells from *names* (this wizard's reference data is name-keyed,
 *  unlike creation's id-keyed draft) rather than ids. `draft.hitPoints` must
 *  already be set (validated by the caller) — a level-up is never the
 *  character's first level, so it's never auto-maxed. */
export function levelUpRequestBody(progression: CharacterProgression, options: LevelUpOptions, draft: LevelUpDraft) {
  const target = draft.target;
  const receivingClassName = getReceivingClassName(progression, target);
  const receiving = getReceivingClassAndLevel(progression, target);
  // Closed-list bonus feats (e.g. Mönch's Bonustalent) may be entirely
  // absent from `options.feats` — that list is prereq-filtered, and a
  // closed list waives normal prerequisites for its own named feats — so
  // `newBonusFeat` must also resolve against that list's own FeatDef data,
  // same reasoning as `LevelFeatStep.tsx`'s own `featByName` merge.
  const bonusFeats = receiving
    ? options.classes.find((c) => c.name === receiving.className)?.bonusFeatOptionsByLevel[receiving.level]?.feats ?? []
    : [];

  const feats = [
    featSelection(draft.newFeat, options.feats, draft.featSubChoices, draft.featSubChoices2),
    featSelection(draft.newBonusFeat, [...options.feats, ...bonusFeats], draft.featSubChoices, draft.featSubChoices2),
  ].filter((selection): selection is FeatSelectionBody => selection !== null);

  const skill_ranks = [
    ...Object.entries(draft.skillIncreases)
      .filter(([, newRanks]) => newRanks > 0)
      .map(([skillId, ranks]) => ({ skill_id: skillId, ranks })),
    ...draft.skillSpecializationIncreases
      .filter((entry) => entry.newRanks > 0)
      .map((entry) => ({
        skill_id: entry.skillId,
        specialization_id: entry.specializationId,
        custom_specialization: entry.customSpecialization,
        ranks: entry.newRanks,
      })),
  ];

  const classSpells = receivingClassName ? options.spellsByClass[receivingClassName] ?? [] : [];
  const spell_ids = draft.newSpells
    .map((name) => classSpells.find((s) => s.name === name)?.id)
    .filter((id): id is string => id !== undefined);

  return {
    target:
      target.mode === 'existing'
        ? { mode: 'existing' as const, base_class_id: target.classId }
        : {
            mode: 'new' as const,
            class_name: target.className,
            archetypes: target.archetypes,
            options: target.options,
          },
    hit_points: draft.hitPoints,
    favored_class_bonus: draft.favoredClassBonus,
    existing_level_options: target.mode === 'existing' ? draft.existingLevelOptionSelections : {},
    ability_increase: draft.abilityIncrease,
    skill_ranks,
    feats,
    spell_ids,
  };
}
