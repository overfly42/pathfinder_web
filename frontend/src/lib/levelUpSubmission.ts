import type { CharacterProgression } from '../types/characterProgression';
import type { LevelUpDraft } from '../types/levelUpDraft';
import type { LevelUpOptions } from '../types/levelUpOptions';
import { getReceivingClassName } from './levelUpCalculations';

interface FeatSelectionBody {
  feat_id: string;
  chosen_weapon_id: string | null;
  chosen_skill_id: string | null;
  chosen_spell_school: string | null;
}

function featSelection(
  name: string | null,
  options: LevelUpOptions,
  subChoices: Record<string, string>,
): FeatSelectionBody | null {
  if (!name) return null;
  const feat = options.feats.find((f) => f.name === name);
  if (!feat) return null;
  const subChoice = subChoices[name];
  return {
    feat_id: feat.id,
    chosen_weapon_id: feat.subChoiceType === 'weapon' ? subChoice ?? null : null,
    chosen_skill_id: feat.subChoiceType === 'skill' ? subChoice ?? null : null,
    chosen_spell_school: feat.subChoiceType === 'spell_school' ? subChoice ?? null : null,
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

  const feats = [
    featSelection(draft.newFeat, options, draft.featSubChoices),
    featSelection(draft.newBonusFeat, options, draft.featSubChoices),
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

  const spell = receivingClassName && draft.newSpell
    ? (options.spellsByClass[receivingClassName] ?? []).find((s) => s.name === draft.newSpell)
    : undefined;

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
    spell_id: spell?.id ?? null,
  };
}
