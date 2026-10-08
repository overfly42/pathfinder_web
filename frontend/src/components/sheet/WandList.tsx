import { useRef, useState } from 'react';
import type { Wand } from '../../types/character';
import type { SpellDef } from '../../types/creationOptions';

interface WandListProps {
  wands: Wand[];
  spellCatalog: SpellDef[];
  onAdd: (spellId: string) => void;
  onUse: (id: string) => void;
  onRemove: (id: string) => void;
}

export function WandList({ wands, spellCatalog, onAdd, onUse, onRemove }: WandListProps) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [spellId, setSpellId] = useState('');
  const selectedId = spellId || spellCatalog[0]?.id || '';

  function handleAdd() {
    if (!selectedId) return;
    onAdd(selectedId);
    setSpellId('');
    detailsRef.current?.removeAttribute('open');
  }

  return (
    <>
      <div className="section-label">Zauberstäbe</div>
      <div className="gear-list">
        {wands.map((wand) => (
          <div className="gear-item" key={wand.id}>
            <span className="gear-name">
              Zauberstab: {wand.spellName} <small>(ZS {wand.casterLevel})</small>
            </span>
            <span className="qty">{wand.chargesRemaining}/{wand.maxCharges}</span>
            <button
              type="button"
              className="hp-btn confirm"
              onClick={() => onUse(wand.id)}
              disabled={wand.chargesRemaining <= 0}
              title="Eine Ladung verbrauchen"
            >
              Benutzen
            </button>
            <button type="button" className="gear-del" onClick={() => onRemove(wand.id)} title="Zauberstab entfernen">✕</button>
          </div>
        ))}
      </div>
      <details className="gear-add" ref={detailsRef}>
        <summary className="gear-add-btn">+ Zauberstab hinzufügen</summary>
        <div className="hp-popover-body gear-form">
          <select value={selectedId} onChange={(e) => setSpellId(e.target.value)}>
            {spellCatalog.map((s) => (
              <option value={s.id} key={s.id}>{s.name} (Grad {s.grade})</option>
            ))}
          </select>
          <div className="hp-popover-actions">
            <button type="button" className="hp-btn confirm" onClick={handleAdd} disabled={!selectedId}>Hinzufügen</button>
          </div>
        </div>
      </details>
    </>
  );
}
