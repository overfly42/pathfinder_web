import type { Dispatch, SetStateAction } from 'react';
import type { CreationDraft, PointBudget } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import type { AbilityKey } from '../../types/abilities';
import { abilityMod, formatMod, raceMod, selectedRace, spentPoints } from '../../lib/creationCalculations';

interface AbilitiesStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

export function AbilitiesStep({ draft, options, setDraft }: AbilitiesStepProps) {
  const race = selectedRace(draft, options);
  const spent = spentPoints(draft, options);
  const remaining = draft.pointBudget - spent;

  function adjustAbility(key: AbilityKey, dir: 1 | -1) {
    const newScore = draft.abilityScores[key] + dir;
    if (newScore < 7 || newScore > 18) return;
    if (dir > 0) {
      const projected = spent - (options.pointBuyCosts[draft.abilityScores[key]] ?? 0) + (options.pointBuyCosts[newScore] ?? 0);
      if (projected > draft.pointBudget) return;
    }
    setDraft((prev) => ({ ...prev, abilityScores: { ...prev.abilityScores, [key]: newScore } }));
  }

  return (
    <>
      <div className="budget-bar">
        <div>
          <span className="k">Punktekauf&nbsp;</span>
          <select
            value={draft.pointBudget}
            onChange={(e) => setDraft((prev) => ({ ...prev, pointBudget: parseInt(e.target.value, 10) as PointBudget }))}
          >
            <option value={10}>10 Punkte</option>
            <option value={15}>15 Punkte</option>
            <option value={20}>20 Punkte</option>
            <option value={25}>25 Punkte</option>
          </select>
        </div>
        <div>
          <span className="k">Verbleibend&nbsp;</span>
          <span className={`v${remaining < 0 ? ' over' : ''}`}>{remaining}</span>
        </div>
      </div>

      {race?.flex && !draft.flexAbility && (
        <div className="warning-note">Bitte wähle in Schritt 1 (Grunddaten) ein Attribut für den freien Rassenbonus.</div>
      )}

      <div className="ability-edit-grid">
        {options.abilities.map((a) => {
          const score = draft.abilityScores[a.key];
          const mod = raceMod(draft, options, a.key);
          const total = score + mod;
          const totalMod = abilityMod(total);
          return (
            <div className="ability-edit" key={a.key}>
              <div className="name">{a.name}</div>
              <div className="ctrl">
                <button type="button" className="stepper-btn" disabled={score <= 7} onClick={() => adjustAbility(a.key, -1)}>−</button>
                <span className="score">{score}</span>
                <button type="button" className="stepper-btn" disabled={score >= 18} onClick={() => adjustAbility(a.key, 1)}>+</button>
              </div>
              <div className="meta">
                <span className="mod">{formatMod(abilityMod(score))}</span>
                <span className="cost">{options.pointBuyCosts[score] ?? 0} Pkt.</span>
              </div>
              {mod !== 0 && (
                <div className="race-mod-line">
                  Rasse {formatMod(mod)} → <b>{total}</b> ({formatMod(totalMod)})
                </div>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}
