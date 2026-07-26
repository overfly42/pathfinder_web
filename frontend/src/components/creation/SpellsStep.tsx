import type { Dispatch, SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import { classDef, spellPickMax, spellcastingClasses, totalLevel } from '../../lib/creationCalculations';

interface SpellsStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

export function SpellsStep({ draft, options, setDraft }: SpellsStepProps) {
  const casters = spellcastingClasses(draft, options);

  if (casters.length === 0) {
    return (
      <div className="selected-empty">
        Kein zauberkundiger Charakter mit fester, begrenzter Zauberliste. Vorbereitende göttliche Zauberwirker (z. B.
        Kleriker, Druide, Waldläufer) wählen ihre Vorbereitung im Spiel frei aus der vollen Klassen-Zauberliste — hier
        ist keine Auswahl nötig.
      </div>
    );
  }

  const max = spellPickMax(totalLevel(draft));

  function toggleSpell(className: string, name: string) {
    setDraft((prev) => {
      const sel = prev.spellSelections[className] ?? [];
      const idx = sel.indexOf(name);
      let next: string[];
      if (idx !== -1) next = sel.filter((s) => s !== name);
      else if (sel.length < max) next = [...sel, name];
      else next = sel;
      return { ...prev, spellSelections: { ...prev.spellSelections, [className]: next } };
    });
  }

  return (
    <>
      {casters.map((className) => {
        const cls = classDef(options, className);
        const typeLabel = cls?.spellType === 'arcane-prepared' ? 'Zauberbuch (arkan, vorbereitend)' : 'Bekannte Zauber (spontan)';
        const known = options.spellsByClass[className] ?? [];
        const selected = draft.spellSelections[className] ?? [];
        return (
          <div className="summary-block" style={{ marginBottom: 16 }} key={className}>
            <div className="sb-title">{className} — {typeLabel}</div>
            <div className="pick-counter" style={{ marginBottom: 10 }}>
              Ausgewählt: <b>{selected.length}</b> / <b>{max}</b>
            </div>
            <div className="chip-row">
              {known.map((name) => {
                const active = selected.includes(name);
                const disabled = !active && selected.length >= max;
                return (
                  <button
                    key={name}
                    type="button"
                    className={`chip${active ? ' active' : ''}${disabled ? ' disabled' : ''}`}
                    onClick={disabled ? undefined : () => toggleSpell(className, name)}
                  >
                    {name}
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
