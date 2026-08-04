import type { Dispatch, SetStateAction } from 'react';
import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import { getReceivingClassName } from '../../lib/levelUpCalculations';

interface HitPointsStepProps {
  progression: CharacterProgression;
  options: LevelUpOptions;
  draft: LevelUpDraft;
  setDraft: Dispatch<SetStateAction<LevelUpDraft>>;
}

/** Player-entered HP roll for the new level — creation never needed this
 *  step (it only ever creates level-1 characters, always auto-maxed), so
 *  this is the first place the wizard asks for one. Also asks for the
 *  favored-class bonus (+1 HP or +1 skill rank) when this level is in the
 *  favored class — http://prd.5footstep.de/Grundregelwerk/Fertigkeiten-erwerben. */
export function HitPointsStep({ progression, options, draft, setDraft }: HitPointsStepProps) {
  const target = draft.target;
  const className = getReceivingClassName(progression, target);
  const hitDice = (className && options.classes.find((c) => c.name === className)?.hitDice) || null;
  const isFavored =
    target.mode === 'existing' && (progression.classes.find((c) => c.id === target.classId)?.isFavored ?? false);

  if (!className || hitDice === null) {
    return <div className="warning-note">Bitte zuerst in Schritt 1 festlegen, welche Klasse diese Stufe erhält.</div>;
  }

  function setHitPoints(value: string) {
    const parsed = value === '' ? null : Number(value);
    setDraft((prev) => ({ ...prev, hitPoints: parsed !== null && Number.isFinite(parsed) ? parsed : null }));
  }

  function setFavoredClassBonus(value: 'hp' | 'skill') {
    setDraft((prev) => ({ ...prev, favoredClassBonus: prev.favoredClassBonus === value ? null : value }));
  }

  const outOfRange = draft.hitPoints !== null && (draft.hitPoints < 1 || draft.hitPoints > hitDice);

  return (
    <>
      <div className="field-label">
        Trefferwürfel für {className} (d{hitDice}, Wert 1 – {hitDice}).
      </div>
      <div className="field-row" style={{ maxWidth: 200, marginTop: 10 }}>
        <input
          type="number"
          className="text-input"
          min={1}
          max={hitDice}
          value={draft.hitPoints ?? ''}
          onChange={(e) => setHitPoints(e.target.value)}
        />
      </div>
      {outOfRange && (
        <div className="warning-note" style={{ marginTop: 10 }}>
          Wert muss zwischen 1 und {hitDice} liegen.
        </div>
      )}
      {isFavored && (
        <>
          <div className="field-label" style={{ marginTop: 18 }}>
            Bevorzugte Klasse: zusätzlicher Bonus (1 Trefferpunkt oder 1 Fertigkeitsrang).
          </div>
          <div className="chip-row" style={{ marginTop: 10 }}>
            <button
              type="button"
              className={`chip${draft.favoredClassBonus === 'hp' ? ' active' : ''}`}
              onClick={() => setFavoredClassBonus('hp')}
            >
              +1 Trefferpunkt
            </button>
            <button
              type="button"
              className={`chip${draft.favoredClassBonus === 'skill' ? ' active' : ''}`}
              onClick={() => setFavoredClassBonus('skill')}
            >
              +1 Fertigkeitsrang
            </button>
          </div>
        </>
      )}
    </>
  );
}
