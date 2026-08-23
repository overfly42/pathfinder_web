import { useState, type Dispatch, type SetStateAction } from 'react';
import { createId } from '../../lib/id';
import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import { abilityMod, formatMod } from '../../lib/creationCalculations';
import {
  backgroundSkillPointsForThisLevel,
  classSkillSetForLevelUp,
  effectiveAbilityTotal,
  getNewLevel,
  getReceivingClassName,
  raceGrantsSkillBonusPerLevel,
  skillIncreasesByCategory,
  skillPointsForThisLevel,
  skillPointsRemainingForLevelUp,
  skillSpecializationBonusForLevelUp,
} from '../../lib/levelUpCalculations';
import { SuggestPicker } from '../primitives/SuggestPicker';

interface LevelSkillsStepProps {
  progression: CharacterProgression;
  options: LevelUpOptions;
  draft: LevelUpDraft;
  setDraft: Dispatch<SetStateAction<LevelUpDraft>>;
}

export function LevelSkillsStep({ progression, options, draft, setDraft }: LevelSkillsStepProps) {
  const [addingSpecializationFor, setAddingSpecializationFor] = useState<string | null>(null);
  const receivingClassName = getReceivingClassName(progression, draft.target);
  const effectiveIntMod = abilityMod(effectiveAbilityTotal(progression, 'IN', draft.abilityIncrease));
  const raceBonus = raceGrantsSkillBonusPerLevel(progression, options.races) ? 1 : 0;
  const favoredBonus = draft.favoredClassBonus === 'skill' ? 1 : 0;
  const budget = skillPointsForThisLevel(receivingClassName, options.classes, effectiveIntMod) + raceBonus + favoredBonus;
  const useBackgroundSkills = progression.useBackgroundSkills ?? false;
  const backgroundBudget = useBackgroundSkills ? backgroundSkillPointsForThisLevel() : 0;
  const { background: backgroundSpent, regular: regularSpentOnly } = skillIncreasesByCategory(
    draft.skillIncreases,
    options.skills,
    draft.skillSpecializationIncreases,
  );
  const remaining = skillPointsRemainingForLevelUp(
    draft.skillIncreases,
    options.skills,
    budget,
    backgroundBudget,
    draft.skillSpecializationIncreases,
  );
  const backgroundRemaining = backgroundBudget - backgroundSpent;
  const classSkills = classSkillSetForLevelUp(progression, draft.target, options.classes);
  const backgroundIds = new Set(options.skills.filter((s) => s.isBackground).map((s) => s.id));
  const newLevel = getNewLevel(progression);

  // Mirrors the backend's `_skill_ranks_exceed_budget` (routers/characters.py):
  // a background-skill rank draws from `backgroundBudget` first, only the
  // overflow beyond it competes with regular-skill ranks for `budget`.
  function canIncrease(skillId: string, existingRanks: number, picked: number): boolean {
    if (existingRanks + picked >= newLevel) return false;
    const isBackground = useBackgroundSkills && backgroundIds.has(skillId);
    const nextBackgroundSpent = backgroundSpent + (isBackground ? 1 : 0);
    const nextRegularSpentOnly = regularSpentOnly + (isBackground ? 0 : 1);
    const overflow = Math.max(0, nextBackgroundSpent - backgroundBudget);
    return nextRegularSpentOnly + overflow <= budget;
  }

  function adjustSpecialization(localId: string, skillId: string, dir: 1 | -1) {
    const entry = draft.skillSpecializationIncreases.find((e) => e.localId === localId);
    const existingRanks = entry
      ? progression.skillRankDetails?.find(
          (d) =>
            d.skillId === entry.skillId &&
            d.specializationId === entry.specializationId &&
            d.customSpecialization === entry.customSpecialization,
        )?.ranks ?? 0
      : 0;
    const cur = entry?.newRanks ?? 0;
    if (dir > 0) {
      if (!canIncrease(skillId, existingRanks, cur)) return;
      setDraft((prev) => ({
        ...prev,
        skillSpecializationIncreases: prev.skillSpecializationIncreases.map((e) =>
          e.localId === localId ? { ...e, newRanks: e.newRanks + 1 } : e,
        ),
      }));
    } else {
      if (cur <= 0) return;
      setDraft((prev) => ({
        ...prev,
        skillSpecializationIncreases: prev.skillSpecializationIncreases.map((e) =>
          e.localId === localId ? { ...e, newRanks: e.newRanks - 1 } : e,
        ),
      }));
    }
  }

  function addSpecialization(skillId: string, specializationId: string | null, customText: string) {
    const localId = createId();
    setDraft((prev) => ({
      ...prev,
      skillSpecializationIncreases: [
        ...prev.skillSpecializationIncreases,
        { localId, skillId, specializationId, customSpecialization: customText || null, newRanks: 0 },
      ],
    }));
    setAddingSpecializationFor(null);
  }

  function removeSpecialization(localId: string) {
    setDraft((prev) => ({
      ...prev,
      skillSpecializationIncreases: prev.skillSpecializationIncreases.filter((e) => e.localId !== localId),
    }));
  }

  // Per PF1e (http://prd.5footstep.de/Grundregelwerk/Fertigkeiten-erwerben),
  // the only cap on a single skill is total ranks <= character level - a
  // skill with 0 prior ranks can take more than 1 new rank this level, so
  // this is a +/- stepper (mirrors creation's SkillsStep.tsx), not a
  // one-shot toggle.
  function adjust(skillId: string, dir: 1 | -1) {
    setDraft((prev) => {
      const cur = prev.skillIncreases[skillId] || 0;
      const existingRanks = progression.skillRanks[skillId] || 0;
      if (dir > 0) {
        if (!canIncrease(skillId, existingRanks, cur)) return prev;
        return { ...prev, skillIncreases: { ...prev.skillIncreases, [skillId]: cur + 1 } };
      }
      if (cur <= 0) return prev;
      const nextIncreases = { ...prev.skillIncreases, [skillId]: cur - 1 };
      if (nextIncreases[skillId] === 0) delete nextIncreases[skillId];
      return { ...prev, skillIncreases: nextIncreases };
    });
  }

  return (
    <>
      <div className="pick-counter" style={{ marginBottom: 14 }}>
        Neue Fertigkeitspunkte diese Stufe: <b>{remaining} / {budget}</b>
      </div>
      {useBackgroundSkills && (
        <div className="pick-counter" style={{ marginBottom: 14 }}>
          Neue Hintergrundfertigkeitspunkte diese Stufe: <b>{backgroundRemaining} / {backgroundBudget}</b>
        </div>
      )}
      <div>
        {options.skills.map((skill) => {
          if (!skill.hasSpecialization) {
            const existingRanks = progression.skillRanks[skill.id] || 0;
            const picked = draft.skillIncreases[skill.id] || 0;
            const isClassSkill = classSkills.has(skill.id);
            const totalRanks = existingRanks + picked;
            const abMod = abilityMod(effectiveAbilityTotal(progression, skill.ability, draft.abilityIncrease));
            const bonus = totalRanks + abMod + (isClassSkill && totalRanks > 0 ? 3 : 0);
            const canInc = canIncrease(skill.id, existingRanks, picked);
            return (
              <div className={`skill-row-pick${picked > 0 ? ' active' : ''}`} key={skill.id}>
                <div className="sr-name">
                  {skill.name} <span className="sr-ability">({skill.ability.toUpperCase()})</span>
                  {isClassSkill && <span className="tag class-skill"> Klasse</span>}
                  {useBackgroundSkills && skill.isBackground && <span className="tag"> Hintergrund</span>}
                </div>
                <div className="sr-existing">bereits {existingRanks}</div>
                <div className="sr-pick-ctrl">
                  <button type="button" className="stepper-btn" disabled={picked <= 0} onClick={() => adjust(skill.id, -1)}>−</button>
                  <span className="sr-pick">+{picked}</span>
                  <button type="button" className="stepper-btn" disabled={!canInc} onClick={() => adjust(skill.id, 1)}>+</button>
                </div>
                <div className="sr-total">{formatMod(bonus)}</div>
              </div>
            );
          }

          const entries = draft.skillSpecializationIncreases.filter((e) => e.skillId === skill.id);
          const isClassSkill = classSkills.has(skill.id);
          const abMod = abilityMod(effectiveAbilityTotal(progression, skill.ability, draft.abilityIncrease));
          const suggestions = options.skillSpecializations
            .filter((s) => s.skillId === skill.id)
            .map((s) => ({ id: s.id, label: s.name }));
          return (
            <div key={skill.id} style={{ marginBottom: 14 }}>
            <div className="field-label">
              {skill.name} <span className="sr-ability">({skill.ability.toUpperCase()})</span>
              {isClassSkill && <span className="tag class-skill"> Klasse</span>}
              {useBackgroundSkills && skill.isBackground && <span className="tag"> Hintergrund</span>}
            </div>
            {entries.map((entry) => {
              const existingRanks =
                progression.skillRankDetails?.find(
                  (d) =>
                    d.skillId === entry.skillId &&
                    d.specializationId === entry.specializationId &&
                    d.customSpecialization === entry.customSpecialization,
                )?.ranks ?? 0;
              const bonus = skillSpecializationBonusForLevelUp(existingRanks, entry, abMod, isClassSkill);
              const canInc = canIncrease(skill.id, existingRanks, entry.newRanks);
              const label = entry.specializationId
                ? suggestions.find((s) => s.id === entry.specializationId)?.label ?? '?'
                : entry.customSpecialization || '…';
              return (
                <div className={`skill-row-pick has-remove${entry.newRanks > 0 ? ' active' : ''}`} key={entry.localId}>
                  <div className="sr-name">
                    {skill.name} ({label})
                  </div>
                  <div className="sr-existing">bereits {existingRanks}</div>
                  <div className="sr-pick-ctrl">
                    <button
                      type="button"
                      className="stepper-btn"
                      disabled={entry.newRanks <= 0}
                      onClick={() => adjustSpecialization(entry.localId, skill.id, -1)}
                    >
                      −
                    </button>
                    <span className="sr-pick">+{entry.newRanks}</span>
                    <button
                      type="button"
                      className="stepper-btn"
                      disabled={!canInc}
                      onClick={() => adjustSpecialization(entry.localId, skill.id, 1)}
                    >
                      +
                    </button>
                  </div>
                  <div className="sr-total">{formatMod(bonus)}</div>
                  <button type="button" className="gear-del" onClick={() => removeSpecialization(entry.localId)} title="Entfernen">
                    ✕
                  </button>
                </div>
              );
            })}
            {addingSpecializationFor === skill.id ? (
              <div className="detail-group">
                <SuggestPicker
                  suggestions={suggestions}
                  pickedSuggestionId={null}
                  customText=""
                  onPickSuggestion={(id) => addSpecialization(skill.id, id, '')}
                  onChangeCustomText={(text) => {
                    if (text) addSpecialization(skill.id, null, text);
                  }}
                  searchPlaceholder={`${skill.name} durchsuchen`}
                  customPlaceholder="Eigene Spezialisierung eintragen"
                />
                <button type="button" className="hp-btn" onClick={() => setAddingSpecializationFor(null)}>
                  Abbrechen
                </button>
              </div>
            ) : (
              <button type="button" className="hp-btn" onClick={() => setAddingSpecializationFor(skill.id)}>
                + Spezialisierung hinzufügen
              </button>
            )}
          </div>
          );
        })}
      </div>
    </>
  );
}
