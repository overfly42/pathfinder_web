import { useRef, useState } from 'react';
import type { PreparableSpellGrade } from '../../types/character';

interface SpellbookProps {
  grades: PreparableSpellGrade[];
  onPrepareSpell: (grade: number, spellKey: string, baseClassId: string) => void;
  onUnprepareSpell: (grade: number, spellKey: string, baseClassId: string) => void;
  onAddSpell: (grade: number, name: string) => void;
  onRemoveSpell: (grade: number, spellKey: string) => void;
}

function AddSpellRow({ grade, onAdd }: { grade: number; onAdd: (grade: number, name: string) => void }) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [name, setName] = useState('');

  function handleAdd() {
    const trimmed = name.trim();
    if (!trimmed) return;
    onAdd(grade, trimmed);
    setName('');
    detailsRef.current?.removeAttribute('open');
  }

  return (
    <details className="gear-add" ref={detailsRef}>
      <summary className="gear-add-btn">+ Zauber hinzufügen</summary>
      <div className="hp-popover-body gear-form">
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Zaubername" />
        <div className="hp-popover-actions">
          <button type="button" className="hp-btn confirm" onClick={handleAdd}>Hinzufügen</button>
        </div>
      </div>
    </details>
  );
}

export function Spellbook({ grades, onPrepareSpell, onUnprepareSpell, onAddSpell, onRemoveSpell }: SpellbookProps) {
  return (
    <>
      <div className="spell-hint">
        Zauberbuch · Zauber für den Tag vorbereiten (mehrfach möglich, bis zum Limit pro Grad). Zurückgesetzt bei +1 Tag.
      </div>
      {grades.map((grade) => {
        const preparedTotal = grade.spells.reduce((sum, s) => sum + s.preparedCount, 0);
        const atCap = grade.perDay != null && preparedTotal >= grade.perDay;
        return (
          <div className="spell-tab-block" key={grade.grade}>
            <div className={`spell-table-row${grade.locked ? ' locked' : ''}`}>
              <span className="grade">Grad {grade.grade}</span>
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
                <AddSpellRow grade={grade.grade} onAdd={onAddSpell} />
              </>
            )}
          </div>
        );
      })}
    </>
  );
}
