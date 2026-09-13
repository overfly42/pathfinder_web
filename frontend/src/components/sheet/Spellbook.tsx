import { useRef, useState } from 'react';
import type { PreparableSpellGrade, PreparedSpellRef } from '../../types/character';
import type { SpellDef } from '../../types/creationOptions';

interface SpellbookProps {
  grades: PreparableSpellGrade[];
  classes?: { id: string; className: string }[];
  spellsByClass: Record<string, SpellDef[]> | null;
  onPrepareSpell: (grade: number, spellKey: string, baseClassId: string) => void;
  onUnprepareSpell: (grade: number, spellKey: string, baseClassId: string) => void;
  onAddSpell: (grade: number, baseClassId: string, spellId: string, name: string) => void;
  onRemoveSpell: (grade: number, spellKey: string) => void;
}

function AddSpellRow({
  grade,
  baseClassId,
  candidates,
  onAdd,
}: {
  grade: number;
  baseClassId: string;
  candidates: SpellDef[];
  onAdd: (grade: number, baseClassId: string, spellId: string, name: string) => void;
}) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [spellId, setSpellId] = useState('');

  function handleAdd() {
    const spell = candidates.find((c) => c.id === spellId);
    if (!spell) return;
    onAdd(grade, baseClassId, spell.id, spell.name);
    setSpellId('');
    detailsRef.current?.removeAttribute('open');
  }

  if (candidates.length === 0) return null;

  return (
    <details className="gear-add" ref={detailsRef}>
      <summary className="gear-add-btn">+ Zauber hinzufügen</summary>
      <div className="hp-popover-body gear-form">
        <select value={spellId} onChange={(e) => setSpellId(e.target.value)}>
          <option value="" disabled>
            Zauber wählen …
          </option>
          {candidates.map((spell) => (
            <option key={spell.id} value={spell.id}>
              {spell.name}
            </option>
          ))}
        </select>
        <div className="hp-popover-actions">
          <button type="button" className="hp-btn confirm" disabled={!spellId} onClick={handleAdd}>
            Hinzufügen
          </button>
        </div>
      </div>
    </details>
  );
}

/** "Zauber in einem höheren Slot vorbereiten" (roadmap.md) — prepares an already-known
 *  lower-grade spell into *this* row's slot instead of its own. Candidates come straight from
 *  the character's own already-known spellbook/known-spell rows (no catalog fetch needed), so
 *  this only ever offers spells the character could legally add here. */
function BorrowSpellRow({
  grade,
  baseClassId,
  candidates,
  atCap,
  onPrepare,
}: {
  grade: number;
  baseClassId: string;
  candidates: PreparedSpellRef[];
  atCap: boolean;
  onPrepare: (grade: number, spellKey: string, baseClassId: string) => void;
}) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [spellKey, setSpellKey] = useState('');

  function handleConfirm() {
    if (!spellKey) return;
    onPrepare(grade, spellKey, baseClassId);
    setSpellKey('');
    detailsRef.current?.removeAttribute('open');
  }

  if (candidates.length === 0) return null;

  return (
    <details className="gear-add" ref={detailsRef}>
      <summary className="gear-add-btn">+ Zauber aus niedrigerem Grad vorbereiten</summary>
      <div className="hp-popover-body gear-form">
        <select value={spellKey} onChange={(e) => setSpellKey(e.target.value)}>
          <option value="" disabled>
            Zauber wählen …
          </option>
          {candidates.map((spell) => (
            <option key={spell.key} value={spell.key}>
              Grad {spell.grade}: {spell.name}
            </option>
          ))}
        </select>
        <div className="hp-popover-actions">
          <button type="button" className="hp-btn confirm" disabled={!spellKey || atCap} onClick={handleConfirm}>
            Vorbereiten
          </button>
        </div>
      </div>
    </details>
  );
}

export function Spellbook({
  grades,
  classes,
  spellsByClass,
  onPrepareSpell,
  onUnprepareSpell,
  onAddSpell,
  onRemoveSpell,
}: SpellbookProps) {
  return (
    <>
      <div className="spell-hint">
        Zauberbuch · Zauber für den Tag vorbereiten (mehrfach möglich, bis zum Limit pro Grad). Zurückgesetzt bei +1 Tag.
      </div>
      {grades.map((grade) => {
        const preparedTotal = grade.spells.reduce((sum, s) => sum + s.preparedCount, 0);
        const atCap = grade.perDay != null && preparedTotal >= grade.perDay;
        // Only arcane-prepared classes manage their spellbook by hand — divine-prepared casters
        // already have their whole class list available, spontaneous casters only learn spells at
        // level-up (`sheet.py`'s `spellType`, matches what `POST .../spellbook` accepts).
        const className = classes?.find((c) => c.id === grade.baseClassId)?.className;
        const knownIds = new Set(grade.spells.map((s) => s.key));
        const candidates =
          grade.spellType === 'arcane-prepared' && className
            ? (spellsByClass?.[className] ?? []).filter((s) => s.grade === grade.grade && !knownIds.has(s.id))
            : [];

        // Already-known spells of a strictly lower, unlocked grade of the same class, not
        // already prepared into this exact slot — "Zauber in einem höheren Slot vorbereiten"
        // (roadmap.md). Deduped by key: the same spell can appear in more than one lower row
        // (its own natural grade, plus any grade it's already been borrowed into below this one).
        const borrowCandidatesByKey = new Map<string, PreparedSpellRef>();
        if (grade.grade >= 1) {
          for (const other of grades) {
            if (other.locked || other.baseClassId !== grade.baseClassId || other.grade >= grade.grade) continue;
            for (const spell of other.spells) {
              if (!knownIds.has(spell.key)) borrowCandidatesByKey.set(spell.key, spell);
            }
          }
        }
        const borrowCandidates = [...borrowCandidatesByKey.values()].sort(
          (a, b) => (a.grade ?? 0) - (b.grade ?? 0) || a.name.localeCompare(b.name),
        );

        return (
          <div className="spell-tab-block" key={grade.grade}>
            <div className={`spell-table-row${grade.locked ? ' locked' : ''}`}>
              <span className="grade">Grad {grade.grade}{grade.dc != null ? ` (SG ${grade.dc})` : ''}</span>
              {grade.locked ? (
                <>
                  <div className="stat"><span className="stat-label">Pro Tag</span><span className="stat-val">—</span></div>
                  <div className="stat"><span className="stat-label">Verfügbar ab</span><span className="stat-val">Stufe {grade.availableAtLevel}</span></div>
                  <div className="stat" />
                </>
              ) : (
                <>
                  <div className="stat"><span className="stat-label">Pro Tag</span><span className="stat-val">{grade.perDay}</span></div>
                  <div className="stat"><span className="stat-label">Vorbereitet</span><span className="stat-val">{preparedTotal} / {grade.perDay}</span></div>
                  <div className="stat" />
                </>
              )}
            </div>
            {!grade.locked && (
              <>
                <div className="chip-row spellprep">
                  {grade.spells.map((spell) => {
                    // A spell shown here whose own grade differs from this row's grade is a
                    // borrowed-slot copy ("Zauber in einem höheren Slot vorbereiten") — its own
                    // natural-grade row (elsewhere in this list) is the one "Aus Zauberbuch
                    // entfernen" should act on, not this one.
                    const isNatural = spell.grade == null || spell.grade === grade.grade;
                    return (
                      <span key={spell.key} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                        <span className={`chip${spell.preparedCount > 0 ? ' active' : ''}`}>
                          {!isNatural && <span style={{ opacity: 0.7 }}>Grad {spell.grade}: </span>}
                          {spell.name} ({spell.preparedCount})
                        </span>
                        <button
                          type="button"
                          className="gear-del"
                          title="Vorbereitung entfernen"
                          disabled={spell.preparedCount <= spell.usedCount}
                          onClick={() => onUnprepareSpell(grade.grade, spell.key, spell.baseClassId)}
                        >
                          −
                        </button>
                        <button
                          type="button"
                          className="gear-del"
                          title="Vorbereiten"
                          disabled={atCap}
                          onClick={() => onPrepareSpell(grade.grade, spell.key, spell.baseClassId)}
                        >
                          +
                        </button>
                        {isNatural && (
                          <button
                            type="button"
                            className="gear-del"
                            title="Aus Zauberbuch entfernen"
                            onClick={() => onRemoveSpell(grade.grade, spell.key)}
                          >
                            ✕
                          </button>
                        )}
                      </span>
                    );
                  })}
                </div>
                <AddSpellRow
                  grade={grade.grade}
                  baseClassId={grade.baseClassId ?? ''}
                  candidates={candidates}
                  onAdd={onAddSpell}
                />
                <BorrowSpellRow
                  grade={grade.grade}
                  baseClassId={grade.baseClassId ?? ''}
                  candidates={borrowCandidates}
                  atCap={atCap}
                  onPrepare={onPrepareSpell}
                />
              </>
            )}
          </div>
        );
      })}
    </>
  );
}
