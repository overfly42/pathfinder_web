import type { Dispatch, SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import { favoredLevels, hitDiceForLevel, totalLevel } from '../../lib/creationCalculations';
import { useFavoredClassBonusOptions } from '../../hooks/useFavoredClassBonusOptions';

interface HitPointsStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

/** Player-entered HP roll for every character level past the 1st (always
 *  maxed automatically, see `create_character`), plus the favored-class
 *  bonus choice ("hp" | "skill" | a race+class-specific alternate) for
 *  every level that falls in the favored class (`classRows[0]`'s class) —
 *  PF1e grants that choice per level, not once at creation, so a
 *  multi-level favored class needs one answer per level here, same as the
 *  HP rolls. Mirrors `levelup/HitPointsStep.tsx`, generalized to a whole
 *  level range instead of just the one level a level-up adds. */
export function HitPointsStep({ draft, options, setDraft }: HitPointsStepProps) {
  const level = totalLevel(draft);
  const hpLevels = Array.from({ length: Math.max(0, level - 1) }, (_, i) => i + 2);
  const favLevels = favoredLevels(draft);
  const favoredClassName = draft.classRows[0]?.className ?? null;
  const favoredClassBonusOptions = useFavoredClassBonusOptions(draft.raceId, favoredClassName);
  const alternateFavoredClassBonuses = (favoredClassBonusOptions?.options ?? []).filter(
    (name) => name !== 'hp' && name !== 'skill',
  );

  function setHitPoints(levelNum: number, value: string) {
    const parsed = value === '' ? null : Number(value);
    setDraft((prev) => ({
      ...prev,
      hitPoints: {
        ...prev.hitPoints,
        [String(levelNum)]: parsed !== null && Number.isFinite(parsed) ? parsed : null,
      },
    }));
  }

  function setFavoredClassBonus(levelNum: number, value: string) {
    setDraft((prev) => ({
      ...prev,
      favoredClassBonus: {
        ...prev.favoredClassBonus,
        [String(levelNum)]: prev.favoredClassBonus[String(levelNum)] === value ? null : value,
      },
    }));
  }

  if (hpLevels.length === 0 && favLevels.length === 0) {
    return (
      <div className="field-label">
        Für einen Charakter der 1. Stufe außerhalb der bevorzugten Klasse ist hier nichts einzutragen.
      </div>
    );
  }

  return (
    <>
      {favLevels.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div className="field-label">
            Bevorzugte Klasse ({favoredClassName}): pro Stufe 1 zusätzlicher Bonus (1 Trefferpunkt, 1
            Fertigkeitsrang, oder ein rassenspezifischer Alternativbonus).
          </div>
          {favoredClassBonusOptions ? (
            favLevels.map((lvl) => {
              const value = draft.favoredClassBonus[String(lvl)] ?? null;
              return (
                <div key={lvl} style={{ marginTop: 14 }}>
                  <div className="field-label">Stufe {lvl}</div>
                  <div className="chip-row" style={{ marginTop: 6 }}>
                    <button
                      type="button"
                      className={`chip${value === 'hp' ? ' active' : ''}`}
                      onClick={() => setFavoredClassBonus(lvl, 'hp')}
                    >
                      +1 Trefferpunkt
                    </button>
                    <button
                      type="button"
                      className={`chip${value === 'skill' ? ' active' : ''}`}
                      onClick={() => setFavoredClassBonus(lvl, 'skill')}
                    >
                      +1 Fertigkeitsrang
                    </button>
                    {alternateFavoredClassBonuses.map((name) => (
                      <button
                        key={name}
                        type="button"
                        className={`chip${value === name ? ' active' : ''}`}
                        onClick={() => setFavoredClassBonus(lvl, name)}
                      >
                        {favoredClassBonusOptions.shortLabels[name] ?? name}
                      </button>
                    ))}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="warning-note" style={{ marginTop: 10 }}>Lade Optionen …</div>
          )}
        </div>
      )}

      {hpLevels.length > 0 && (
        <div>
          <div className="field-label">
            Trefferwürfel-Wurf für jede Stufe ab der 2. (die 1. Stufe ist immer maximal).
          </div>
          {hpLevels.map((lvl) => {
            const hitDice = hitDiceForLevel(draft, options, lvl);
            const value = draft.hitPoints[String(lvl)] ?? null;
            const outOfRange = value !== null && hitDice !== null && (value < 1 || value > hitDice);
            return (
              <div
                key={lvl}
                className="field-row"
                style={{ maxWidth: 280, marginTop: 10, display: 'flex', alignItems: 'center', gap: 10 }}
              >
                <label style={{ minWidth: 100 }}>
                  Stufe {lvl} (d{hitDice ?? '?'})
                </label>
                <input
                  type="number"
                  className="text-input"
                  min={1}
                  max={hitDice ?? undefined}
                  value={value ?? ''}
                  onChange={(e) => setHitPoints(lvl, e.target.value)}
                />
                {outOfRange && <span className="warning-note">1 – {hitDice}</span>}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}
