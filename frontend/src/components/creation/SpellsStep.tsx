import type { Dispatch, SetStateAction } from 'react';
import type { AbilityKey } from '../../types/abilities';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import {
  abilityMod,
  arcanePreparedBudget,
  classDef,
  classTotalLevel,
  spellGradeBudgetAtLevel,
  spellcastingClasses,
  totalAbility,
} from '../../lib/creationCalculations';

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

  function toggleSpell(baseClassId: string, spellId: string, canAdd: (selected: string[]) => boolean) {
    setDraft((prev) => {
      const selected = prev.spellSelections[baseClassId] ?? [];
      let next: string[];
      if (selected.includes(spellId)) next = selected.filter((s) => s !== spellId);
      else if (canAdd(selected)) next = [...selected, spellId];
      else next = selected;
      return { ...prev, spellSelections: { ...prev.spellSelections, [baseClassId]: next } };
    });
  }

  return (
    <>
      {casters.map((className) => {
        const cls = classDef(options, className);
        if (!cls?.id) return null;
        const baseClassId = cls.id;
        const level = classTotalLevel(draft, className);
        const gradeBudget = spellGradeBudgetAtLevel(cls, level);
        const spells = options.spellsByClass[className] ?? [];
        const selected = draft.spellSelections[baseClassId] ?? [];

        if (cls.spellType === 'arcane-prepared') {
          const cantrips = spells.filter((s) => s.grade === 0);
          const nonCantrips = spells.filter((s) => s.grade !== 0 && String(s.grade) in gradeBudget);
          const mod = cls.castingAbility ? abilityMod(totalAbility(draft, options, cls.castingAbility as AbilityKey)) : 0;
          const budget = arcanePreparedBudget(level, mod);
          const nonCantripSelected = selected.filter((id) => cantrips.every((c) => c.id !== id));

          return (
            <div className="summary-block" style={{ marginBottom: 16 }} key={className}>
              <div className="sb-title">{className} — Zauberbuch (arkan, vorbereitend)</div>
              <div className="pick-counter" style={{ marginBottom: 6 }}>
                Grad-0-Zauber (automatisch): {cantrips.map((s) => s.name).join(', ') || '—'}
              </div>
              <div className="pick-counter" style={{ marginBottom: 10 }}>
                Ausgewählt: <b>{nonCantripSelected.length}</b> / <b>{budget}</b>
              </div>
              <div className="chip-row">
                {nonCantrips.map((spell) => {
                  const active = selected.includes(spell.id);
                  const disabled = !active && nonCantripSelected.length >= budget;
                  return (
                    <button
                      key={spell.id}
                      type="button"
                      className={`chip${active ? ' active' : ''}${disabled ? ' disabled' : ''}`}
                      onClick={
                        disabled
                          ? undefined
                          : () => toggleSpell(baseClassId, spell.id, (sel) => sel.length < budget)
                      }
                    >
                      Grad {spell.grade}: {spell.name}
                    </button>
                  );
                })}
              </div>
            </div>
          );
        }

        // spontaneous: separate cap per grade, straight from spellsKnownByLevel.
        const grades = Object.keys(gradeBudget)
          .map(Number)
          .sort((a, b) => a - b);
        return (
          <div className="summary-block" style={{ marginBottom: 16 }} key={className}>
            <div className="sb-title">{className} — Bekannte Zauber (spontan)</div>
            {grades.map((grade) => {
              const cap = gradeBudget[String(grade)] ?? 0;
              const gradeSpells = spells.filter((s) => s.grade === grade);
              const gradeSelected = selected.filter((id) => gradeSpells.some((s) => s.id === id));
              return (
                <div key={grade} style={{ marginBottom: 10 }}>
                  <div className="pick-counter" style={{ marginBottom: 6 }}>
                    Grad {grade}: <b>{gradeSelected.length}</b> / <b>{cap}</b>
                  </div>
                  <div className="chip-row">
                    {gradeSpells.map((spell) => {
                      const active = selected.includes(spell.id);
                      const disabled = !active && gradeSelected.length >= cap;
                      return (
                        <button
                          key={spell.id}
                          type="button"
                          className={`chip${active ? ' active' : ''}${disabled ? ' disabled' : ''}`}
                          onClick={
                            disabled
                              ? undefined
                              : () =>
                                  toggleSpell(
                                    baseClassId,
                                    spell.id,
                                    (sel) => sel.filter((id) => gradeSpells.some((s) => s.id === id)).length < cap,
                                  )
                          }
                        >
                          {spell.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        );
      })}
    </>
  );
}
