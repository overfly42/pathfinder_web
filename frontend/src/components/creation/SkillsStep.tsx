import { useEffect, type Dispatch, type SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import {
  backgroundSkillPointsTotal,
  classSkillSet,
  formatMod,
  skillBonus,
  skillPointsRemaining,
  skillPointsSpentByCategory,
  skillPointsTotal,
  totalLevel,
} from '../../lib/creationCalculations';

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

  const favoredBonus = draft.favoredClassBonus === 'skill' ? 1 : 0;
  const regularTotal = skillPointsTotal(draft, options) + favoredBonus;
  const backgroundTotal = draft.useBackgroundSkills ? backgroundSkillPointsTotal(draft) : 0;
  const { background: backgroundSpent, regular: regularSpentOnly } = skillPointsSpentByCategory(draft, options);
  const regularRemaining = skillPointsRemaining(draft, options, regularTotal, backgroundTotal);
  const backgroundRemaining = backgroundTotal - backgroundSpent;
  const classSkills = classSkillSet(draft, options);
  const backgroundIds = new Set(options.skills.filter((s) => s.isBackground).map((s) => s.id));

  // Mirrors the backend's `_skill_ranks_exceed_budget` (routers/characters.py):
  // a background-skill rank draws from `backgroundTotal` first, only the
  // overflow beyond it competes with regular-skill ranks for `regularTotal`.
  function canIncrease(skillId: string, currentRanks: number): boolean {
    if (currentRanks >= level) return false;
    const isBackground = draft.useBackgroundSkills && backgroundIds.has(skillId);
    const nextBackgroundSpent = backgroundSpent + (isBackground ? 1 : 0);
    const nextRegularSpentOnly = regularSpentOnly + (isBackground ? 0 : 1);
    const overflow = Math.max(0, nextBackgroundSpent - backgroundTotal);
    return nextRegularSpentOnly + overflow <= regularTotal;
  }

  function adjustSkill(key: string, dir: 1 | -1) {
    const cur = draft.skillRanks[key] || 0;
    if (dir > 0) {
      if (!canIncrease(key, cur)) return;
      setDraft((prev) => ({ ...prev, skillRanks: { ...prev.skillRanks, [key]: cur + 1 } }));
    } else {
      if (cur <= 0) return;
      setDraft((prev) => ({ ...prev, skillRanks: { ...prev.skillRanks, [key]: cur - 1 } }));
    }
  }

  return (
    <>
      <label className="option-toggle" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        <input
          type="checkbox"
          checked={draft.useBackgroundSkills}
          onChange={() => setDraft((prev) => ({ ...prev, useBackgroundSkills: !prev.useBackgroundSkills }))}
        />
        Hintergrundfertigkeiten (Alternativregel): +2 Fertigkeitsränge pro Stufe, nur für markierte Fertigkeiten
      </label>

      <div className="budget-bar">
        <span className="k">Fertigkeitspunkte verbleibend</span>
        <span className={`v${regularRemaining < 0 ? ' over' : ''}`}>{regularRemaining} / {regularTotal}</span>
      </div>
      {draft.useBackgroundSkills && (
        <div className="budget-bar">
          <span className="k">Hintergrundfertigkeitspunkte verbleibend</span>
          <span className={`v${backgroundRemaining < 0 ? ' over' : ''}`}>{backgroundRemaining} / {backgroundTotal}</span>
        </div>
      )}

      <div>
        {options.skills.map((skill) => {
          const ranks = draft.skillRanks[skill.id] || 0;
          const isClassSkill = classSkills.has(skill.id);
          const bonus = skillBonus(draft, options, skill.id, skill.ability);
          const canInc = canIncrease(skill.id, ranks);
          return (
            <div className="skill-row-edit" key={skill.id}>
              <div className="sr-name">
                {skill.name} <span className="sr-ability">({skill.ability.toUpperCase()})</span>
                {isClassSkill && <span className="tag class-skill"> Klasse</span>}
                {draft.useBackgroundSkills && skill.isBackground && <span className="tag"> Hintergrund</span>}
              </div>
              <div className="sr-ctrl">
                <button type="button" className="stepper-btn" disabled={ranks <= 0} onClick={() => adjustSkill(skill.id, -1)}>−</button>
                <span className="sr-rank">{ranks}</span>
                <button type="button" className="stepper-btn" disabled={!canInc} onClick={() => adjustSkill(skill.id, 1)}>+</button>
              </div>
              <div className="sr-total">{formatMod(bonus)}</div>
            </div>
          );
        })}
      </div>
    </>
  );
}
