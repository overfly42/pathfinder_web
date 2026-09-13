import type { Dispatch, SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import type { AbilityKey } from '../../types/abilities';
import { abilityIncreaseLevels, abilityMod, formatMod, totalAbility } from '../../lib/creationCalculations';

interface AbilityIncreaseStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

/** Player-chosen ability score increase (+1 to one ability) for every 4th
 *  character level (4, 8, 12, ...) — PF1e grants one per milestone level,
 *  and creation submits the whole career at once, so a level-8+ character
 *  needs one answer per milestone here, same reasoning as the "Trefferpunkte"
 *  step's per-level HP rolls/favored-class bonus. Mirrors
 *  `levelup/AbilityIncreaseStep.tsx`, generalized to every milestone level
 *  in the range instead of just the one level-up might land on. */
export function AbilityIncreaseStep({ draft, options, setDraft }: AbilityIncreaseStepProps) {
  const levels = abilityIncreaseLevels(draft);

  function setIncrease(levelNum: number, key: AbilityKey) {
    setDraft((prev) => ({
      ...prev,
      abilityIncreases: {
        ...prev.abilityIncreases,
        [String(levelNum)]: prev.abilityIncreases[String(levelNum)] === key ? null : key,
      },
    }));
  }

  if (levels.length === 0) {
    return (
      <div className="field-label">
        Attributssteigerungen gibt es erst alle 4 Stufen (4, 8, 12, …) — für diesen Charakter noch nicht relevant.
      </div>
    );
  }

  return (
    <>
      {levels.map((lvl) => {
        const chosen = draft.abilityIncreases[String(lvl)] ?? null;
        return (
          <div key={lvl} style={{ marginTop: lvl === levels[0] ? 0 : 20 }}>
            <div className="field-label">Stufe {lvl}: wähle ein Attribut für die Steigerung um +1.</div>
            <div className="chip-row" style={{ marginTop: 10 }}>
              {options.abilities.map((a) => {
                const cur = totalAbility(draft, options, a.key as AbilityKey);
                const active = chosen === a.key;
                return (
                  <button
                    key={a.key}
                    type="button"
                    className={`chip${active ? ' active' : ''}`}
                    onClick={() => setIncrease(lvl, a.key as AbilityKey)}
                  >
                    {a.name} {cur} → {cur + 1} ({formatMod(abilityMod(cur))} → {formatMod(abilityMod(cur + 1))})
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </>
  );
}
