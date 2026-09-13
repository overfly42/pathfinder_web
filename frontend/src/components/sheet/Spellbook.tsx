import { useRef, useState } from 'react';
import type { PreparableSpellGrade } from '../../types/character';
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
                  {grade.spells.map((spell) => (
                    <span key={spell.key} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      <span className={`chip${spell.preparedCount > 0 ? ' active' : ''}`}>
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
                      <button
                        type="button"
                        className="gear-del"
                        title="Aus Zauberbuch entfernen"
                        onClick={() => onRemoveSpell(grade.grade, spell.key)}
                      >
                        ✕
                      </button>
                    </span>
                  ))}
                </div>
                <AddSpellRow
                  grade={grade.grade}
                  baseClassId={grade.baseClassId ?? ''}
                  candidates={candidates}
                  onAdd={onAddSpell}
                />
              </>
            )}
          </div>
        );
      })}
    </>
  );
}
