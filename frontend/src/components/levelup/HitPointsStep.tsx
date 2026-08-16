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
 *  favored-class bonus (+1 HP, +1 skill rank, or a race+class-specific
 *  Advanced Race Guide alternate) when this level is in the favored class —
 *  http://prd.5footstep.de/Grundregelwerk/Fertigkeiten-erwerben. */
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

  function setFavoredClassBonus(value: string) {
    setDraft((prev) => ({ ...prev, favoredClassBonus: prev.favoredClassBonus === value ? null : value }));
  }

  // "hp"/"skill" always come first with their own fixed German labels (they
  // aren't real catalog entries, see `routers/characters.py`'s
  // `level_up_character`); anything else in `favoredClassBonusOptions` is a
  // real race+class-specific alternate. The chip shows its short label
  // (`favoredClassBonusShortLabels`, e.g. "+1 Rd. Kampfrausch/Tag") rather
  // than the bare catalog name — short enough to read directly on the
  // button, no hover needed (2026-08-16; the full rules text still shows on
  // the summary step, where there's room for it).
  const alternateFavoredClassBonuses = (progression.favoredClassBonusOptions ?? []).filter(
    (name) => name !== 'hp' && name !== 'skill',
  );

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
            {alternateFavoredClassBonuses.map((name) => (
              <button
                key={name}
                type="button"
                className={`chip${draft.favoredClassBonus === name ? ' active' : ''}`}
                onClick={() => setFavoredClassBonus(name)}
              >
                {progression.favoredClassBonusShortLabels?.[name] ?? name}
              </button>
            ))}
          </div>
        </>
      )}
    </>
  );
}
