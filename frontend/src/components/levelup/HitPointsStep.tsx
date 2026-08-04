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
 *  this is the first place the wizard asks for one. */
export function HitPointsStep({ progression, options, draft, setDraft }: HitPointsStepProps) {
  const className = getReceivingClassName(progression, draft.target);
  const hitDice = (className && options.classes.find((c) => c.name === className)?.hitDice) || null;

  if (!className || hitDice === null) {
    return <div className="warning-note">Bitte zuerst in Schritt 1 festlegen, welche Klasse diese Stufe erhält.</div>;
  }

  function setHitPoints(value: string) {
    const parsed = value === '' ? null : Number(value);
    setDraft((prev) => ({ ...prev, hitPoints: parsed !== null && Number.isFinite(parsed) ? parsed : null }));
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
    </>
  );
}
