import type { Dispatch, SetStateAction } from 'react';
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
} from '../../lib/levelUpCalculations';

interface LevelSkillsStepProps {
  progression: CharacterProgression;
  options: LevelUpOptions;
  draft: LevelUpDraft;
  setDraft: Dispatch<SetStateAction<LevelUpDraft>>;
}

export function LevelSkillsStep({ progression, options, draft, setDraft }: LevelSkillsStepProps) {
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
  );
  const remaining = skillPointsRemainingForLevelUp(draft.skillIncreases, options.skills, budget, backgroundBudget);
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
        })}
      </div>
    </>
  );
}
