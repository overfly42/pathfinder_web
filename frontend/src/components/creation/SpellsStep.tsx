import type { Dispatch, SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import {
  abilityMod,
  arcanePreparedBudget,
  archetypesForClass,
  bonusCapGrade,
  bonusKnownSpellSlot,
  classDef,
  classTotalLevel,
  effectiveCastingAbility,
  grantedSpellIdsForClass,
  grantedSpellsForClass,
  spellGradeBudgetAtLevel,
  spellcastingClasses,
  spontaneousBonusOverflowUsed,
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
        // The 1st-level favored-class bonus only ever targets classRows[0]
        // (creation only supports picking it for level 1, see
        // CreationDraft.favoredClassBonus's own docstring) — matches at
        // most one className (Mystiker's/Hexe's choice names are their
        // own), 0 for every other class.
        const bonusAvailable = bonusKnownSpellSlot(className, draft.favoredClassBonus) ? 1 : 0;
        const capGrade = bonusCapGrade(gradeBudget);

        if (cls.spellType === 'arcane-prepared') {
          const cantrips = spells.filter((s) => s.grade === 0);
          const nonCantrips = spells.filter((s) => s.grade !== 0 && String(s.grade) in gradeBudget);
          const castingAbility = effectiveCastingAbility(cls, archetypesForClass(draft, className));
          const mod = castingAbility ? abilityMod(totalAbility(draft, options, castingAbility)) : 0;
          const normalBudget = arcanePreparedBudget(level, mod);
          const budget = normalBudget + bonusAvailable;
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
              {bonusAvailable > 0 && (
                <div className="pick-counter" style={{ marginBottom: 10 }}>
                  + Bevorzugte-Klasse-Bonus: 1 zusätzlicher Zauber, Grad ≤ {capGrade}
                </div>
              )}
              <div className="chip-row">
                {nonCantrips.map((spell) => {
                  const active = selected.includes(spell.id);
                  const wouldUseBonus = !active && nonCantripSelected.length >= normalBudget;
                  const disabled =
                    !active && (nonCantripSelected.length >= budget || (wouldUseBonus && spell.grade > capGrade));
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

        // Spells a one-time option choice already made for this class grants
        // for free (Mystiker's heilfokus Kurieren/Verletzen, Hexenmeister's
        // Blutlinie) — shown separately, never counted against the per-grade
        // budget or offered as a manual pick, same treatment as arcane-
        // prepared's grade-0 cantrips above.
        const granted = grantedSpellsForClass(draft, options, className);
        const grantedIds = grantedSpellIdsForClass(draft, options, className);

        // At creation nothing is "already known" yet — a favored-class-bonus
        // pick (Mystiker's/Hexe's "Zusätzlicher ... Zauber") is a shared pool
        // any grade at or below capGrade can draw on, same shape as
        // LevelSpellStep.tsx's level-up version.
        const pickedByGrade: Record<number, number> = {};
        for (const grade of grades) {
          const gradeSpellIds = new Set(spells.filter((s) => s.grade === grade && !grantedIds.has(s.id)).map((s) => s.id));
          pickedByGrade[grade] = selected.filter((id) => gradeSpellIds.has(id)).length;
        }
        const bonusUsed = spontaneousBonusOverflowUsed(gradeBudget, {}, pickedByGrade, capGrade);
        const bonusRemaining = Math.max(0, bonusAvailable - bonusUsed);

        return (
          <div className="summary-block" style={{ marginBottom: 16 }} key={className}>
            <div className="sb-title">{className} — Bekannte Zauber (spontan)</div>
            {granted.length > 0 && (
              <div className="pick-counter" style={{ marginBottom: 10 }}>
                Automatisch bekannt: {granted.map((s) => s.name).join(', ')}
              </div>
            )}
            {bonusAvailable > 0 && (
              <div className="pick-counter" style={{ marginBottom: 10 }}>
                + Bevorzugte-Klasse-Bonus: {bonusRemaining > 0 ? '1 zusätzlicher Zauber verfügbar' : 'bereits verwendet'}, Grad ≤ {capGrade}
              </div>
            )}
            {grades.map((grade) => {
              const normalCap = gradeBudget[String(grade)] ?? 0;
              const overflowHere = grade <= capGrade ? Math.max(0, pickedByGrade[grade] - normalCap) : 0;
              const cap = normalCap + (grade <= capGrade ? overflowHere + bonusRemaining : 0);
              const gradeSpells = spells.filter((s) => s.grade === grade && !grantedIds.has(s.id));
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
