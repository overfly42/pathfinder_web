import { useEffect, type Dispatch, type SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import { classSkillSet, formatMod, skillBonus, skillPointsSpent, skillPointsTotal, totalLevel } from '../../lib/creationCalculations';

interface SkillsStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

export function SkillsStep({ draft, options, setDraft }: SkillsStepProps) {
  const level = totalLevel(draft);

  // Skill ranks can never exceed total character level; clamp down whenever level drops.
  useEffect(() => {
    setDraft((prev) => {
      let changed = false;
      const nextRanks = { ...prev.skillRanks };
      for (const key of Object.keys(nextRanks)) {
        if ((nextRanks[key] || 0) > level) {
          nextRanks[key] = level;
          changed = true;
        }
      }
      return changed ? { ...prev, skillRanks: nextRanks } : prev;
    });
  }, [level, setDraft]);

  const total = skillPointsTotal(draft, options);
  const spent = skillPointsSpent(draft);
  const remaining = total - spent;
  const classSkills = classSkillSet(draft, options);

  function adjustSkill(key: string, dir: 1 | -1) {
    const cur = draft.skillRanks[key] || 0;
    if (dir > 0) {
      if (cur >= level || remaining - 1 < 0) return;
      setDraft((prev) => ({ ...prev, skillRanks: { ...prev.skillRanks, [key]: cur + 1 } }));
    } else {
      if (cur <= 0) return;
      setDraft((prev) => ({ ...prev, skillRanks: { ...prev.skillRanks, [key]: cur - 1 } }));
    }
  }

  return (
    <>
      <div className="budget-bar">
        <span className="k">Fertigkeitspunkte verbleibend</span>
        <span className={`v${remaining < 0 ? ' over' : ''}`}>{remaining} / {total}</span>
      </div>

      <div>
        {options.skills.map((skill) => {
          const ranks = draft.skillRanks[skill.key] || 0;
          const isClassSkill = classSkills.has(skill.key);
          const bonus = skillBonus(draft, options, skill.key, skill.ability);
          const canInc = ranks < level && remaining - 1 >= 0;
          return (
            <div className="skill-row-edit" key={skill.key}>
              <div className="sr-name">
                {skill.name} <span className="sr-ability">({skill.ability.toUpperCase()})</span>
                {isClassSkill && <span className="tag class-skill"> Klasse</span>}
              </div>
              <div className="sr-ctrl">
                <button type="button" className="stepper-btn" disabled={ranks <= 0} onClick={() => adjustSkill(skill.key, -1)}>−</button>
                <span className="sr-rank">{ranks}</span>
                <button type="button" className="stepper-btn" disabled={!canInc} onClick={() => adjustSkill(skill.key, 1)}>+</button>
              </div>
              <div className="sr-total">{formatMod(bonus)}</div>
            </div>
          );
        })}
      </div>
    </>
  );
}
