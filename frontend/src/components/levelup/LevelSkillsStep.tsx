import type { Dispatch, SetStateAction } from 'react';
import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import { abilityMod, formatMod } from '../../lib/creationCalculations';
import {
  classSkillSetForLevelUp,
  effectiveAbilityTotal,
  getReceivingClassName,
  skillPointsForThisLevel,
} from '../../lib/levelUpCalculations';

interface LevelSkillsStepProps {
  progression: CharacterProgression;
  options: LevelUpOptions;
  draft: LevelUpDraft;
  setDraft: Dispatch<SetStateAction<LevelUpDraft>>;
}

export function LevelSkillsStep({ progression, options, draft, setDraft }: LevelSkillsStepProps) {
  const receivingClassName = getReceivingClassName(progression, draft.target);
  const effectiveIntMod = abilityMod(effectiveAbilityTotal(progression, 'int', draft.abilityIncrease));
  const budget = skillPointsForThisLevel(receivingClassName, options.classes, effectiveIntMod);
  const spent = Object.values(draft.skillIncreases).filter(Boolean).length;
  const remaining = budget - spent;
  const classSkills = classSkillSetForLevelUp(progression, draft.target, options.classes);

  function toggle(key: string) {
    setDraft((prev) => {
      const picked = !!prev.skillIncreases[key];
      if (!picked && remaining <= 0) return prev;
      return { ...prev, skillIncreases: { ...prev.skillIncreases, [key]: !picked } };
    });
  }

  return (
    <>
      <div className="pick-counter" style={{ marginBottom: 14 }}>
        Neue Fertigkeitspunkte diese Stufe: <b>{remaining} / {budget}</b>
      </div>
      <div>
        {options.skills.map((skill) => {
          const existingRanks = progression.skillRanks[skill.key] || 0;
          const picked = !!draft.skillIncreases[skill.key];
          const isClassSkill = classSkills.has(skill.key);
          const totalRanks = existingRanks + (picked ? 1 : 0);
          const abMod = abilityMod(effectiveAbilityTotal(progression, skill.ability, draft.abilityIncrease));
          const bonus = totalRanks + abMod + (isClassSkill && totalRanks > 0 ? 3 : 0);
          const disabled = !picked && remaining <= 0;
          return (
            <div
              key={skill.key}
              className={`skill-row-pick${picked ? ' active' : ''}${disabled ? ' disabled' : ''}`}
              onClick={disabled ? undefined : () => toggle(skill.key)}
            >
              <div className="sr-name">
                {skill.name} <span className="sr-ability">({skill.ability.toUpperCase()})</span>
                {isClassSkill && <span className="tag class-skill"> Klasse</span>}
              </div>
              <div className="sr-existing">bereits {existingRanks}</div>
              <div className="sr-pick">{picked ? '+1 ✓' : '+1 Rang'}</div>
              <div className="sr-total">{formatMod(bonus)}</div>
            </div>
          );
        })}
      </div>
    </>
  );
}
