import { useEffect, type Dispatch, type SetStateAction } from 'react';
import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import type { AbilityKey } from '../../types/abilities';
import { abilityMod, formatMod } from '../../lib/creationCalculations';
import { abilityIncreaseGrantedThisLevel, getNewLevel } from '../../lib/levelUpCalculations';

interface AbilityIncreaseStepProps {
  progression: CharacterProgression;
  options: LevelUpOptions;
  draft: LevelUpDraft;
  setDraft: Dispatch<SetStateAction<LevelUpDraft>>;
}

export function AbilityIncreaseStep({ progression, options, draft, setDraft }: AbilityIncreaseStepProps) {
  const granted = abilityIncreaseGrantedThisLevel(getNewLevel(progression));

  useEffect(() => {
    if (!granted) setDraft((prev) => (prev.abilityIncrease === null ? prev : { ...prev, abilityIncrease: null }));
  }, [granted, setDraft]);

  if (!granted) {
    return <div className="warning-note">Auf dieser Stufe gibt es keine Attributssteigerung (nur alle 4 Stufen: 4, 8, 12, 16, 20).</div>;
  }

  function toggle(key: AbilityKey) {
    setDraft((prev) => ({ ...prev, abilityIncrease: prev.abilityIncrease === key ? null : key }));
  }

  return (
    <>
      <div className="field-label">Wähle ein Attribut für die Steigerung um +1.</div>
      <div className="chip-row" style={{ marginTop: 10 }}>
        {options.abilities.map((a) => {
          const cur = progression.abilityScores[a.key];
          const active = draft.abilityIncrease === a.key;
          return (
            <button key={a.key} type="button" className={`chip${active ? ' active' : ''}`} onClick={() => toggle(a.key)}>
              {a.name} {cur} → {cur + 1} ({formatMod(abilityMod(cur))} → {formatMod(abilityMod(cur + 1))})
            </button>
          );
        })}
      </div>
    </>
  );
}
