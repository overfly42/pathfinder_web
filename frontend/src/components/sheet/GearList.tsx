import { useRef, useState } from 'react';
import type { GearItem } from '../../types/character';

interface GearItemRowProps {
  item: GearItem;
  onSave: (id: string, name: string, qty: number) => void;
  onRemove: (id: string) => void;
  onOpenDetail: (id: string) => void;
}

function GearItemRow({ item, onSave, onRemove, onOpenDetail }: GearItemRowProps) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [name, setName] = useState(item.name);
  const [qty, setQty] = useState(item.qty);

  function handleSave() {
    const trimmed = name.trim();
    if (!trimmed) return;
    onSave(item.id, trimmed, qty);
    detailsRef.current?.removeAttribute('open');
  }

  return (
    <div className="gear-item" id={`gear-${item.id}`}>
      <details className="gear-edit" ref={detailsRef}>
        <summary className="gear-name">{item.name}</summary>
        <div className="hp-popover-body gear-form">
          <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Bezeichnung" />
          <input
            type="number"
            min={1}
            value={qty}
            onChange={(e) => setQty(parseInt(e.target.value, 10) || 1)}
            placeholder="Anzahl"
          />
          <div className="hp-popover-actions">
            <button type="button" className="hp-btn ghost" onClick={() => onOpenDetail(item.id)}>Eigenschaften</button>
            <button type="button" className="hp-btn confirm" onClick={handleSave}>Speichern</button>
          </div>
        </div>
      </details>
      <span className="qty">{item.qty}×</span>
      <button type="button" className="gear-del" onClick={() => onRemove(item.id)} title="Gegenstand entfernen">✕</button>
    </div>
  );
}

function GearAddRow({ onAdd }: { onAdd: (name: string, qty: number) => void }) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [name, setName] = useState('');
  const [qty, setQty] = useState(1);

  function handleAdd() {
    const trimmed = name.trim();
    if (!trimmed) return;
    onAdd(trimmed, qty || 1);
    setName('');
    setQty(1);
    detailsRef.current?.removeAttribute('open');
  }

  return (
    <details className="gear-add" ref={detailsRef}>
      <summary className="gear-add-btn">+ Gegenstand hinzufügen</summary>
      <div className="hp-popover-body gear-form">
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Bezeichnung" />
        <input
          type="number"
          min={1}
          value={qty}
          onChange={(e) => setQty(parseInt(e.target.value, 10) || 1)}
          placeholder="Anzahl"
        />
        <div className="hp-popover-actions">
          <button type="button" className="hp-btn confirm" onClick={handleAdd}>Hinzufügen</button>
        </div>
      </div>
    </details>
  );
}

interface GearListProps {
  gear: GearItem[];
  onAdd: (name: string, qty: number) => void;
  onSave: (id: string, name: string, qty: number) => void;
  onRemove: (id: string) => void;
  onOpenDetail: (id: string) => void;
}

export function GearList({ gear, onAdd, onSave, onRemove, onOpenDetail }: GearListProps) {
  return (
    <>
      <div className="gear-list">
        {gear.map((item) => (
          <GearItemRow key={item.id} item={item} onSave={onSave} onRemove={onRemove} onOpenDetail={onOpenDetail} />
        ))}
      </div>
      <GearAddRow onAdd={onAdd} />
    </>
  );
}
