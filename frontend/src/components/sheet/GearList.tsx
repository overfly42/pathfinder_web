import { useMemo, useRef, useState } from 'react';
import type { GearItem } from '../../types/character';
import type { ItemCatalogEntry, ItemCategory } from '../../types/creationOptions';

const CATEGORY_LABELS: Record<ItemCategory, string> = {
  weapon: 'Waffen',
  armor: 'Rüstung',
  shield: 'Schilde',
  gear: 'Ausrüstung',
  tool: 'Werkzeug',
  consumable: 'Verbrauchsgüter',
};

interface GearItemRowProps {
  item: GearItem;
  onSave: (id: string, qty: number) => void;
  onRemove: (id: string) => void;
  onOpenDetail: (id: string) => void;
}

function GearItemRow({ item, onSave, onRemove, onOpenDetail }: GearItemRowProps) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [qty, setQty] = useState(item.qty);

  function handleSave() {
    onSave(item.id, qty);
    detailsRef.current?.removeAttribute('open');
  }

  return (
    <div className="gear-item" id={`gear-${item.id}`}>
      <details className="gear-edit" ref={detailsRef}>
        <summary className="gear-name">{item.name}</summary>
        <div className="hp-popover-body gear-form">
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

function GearAddRow({ catalog, onAdd }: { catalog: ItemCatalogEntry[]; onAdd: (itemId: string, qty: number) => void }) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [category, setCategory] = useState<ItemCategory | ''>('');
  const [selectedItemId, setSelectedItemId] = useState('');
  const [qty, setQty] = useState(1);

  const categories = useMemo(() => Array.from(new Set(catalog.map((i) => i.category))) as ItemCategory[], [catalog]);
  const filteredItems = useMemo(
    () => (category ? catalog.filter((i) => i.category === category) : catalog),
    [catalog, category],
  );
  const selectedItem = catalog.find((i) => i.id === selectedItemId) ?? filteredItems[0];

  function handleAdd() {
    if (!selectedItem) return;
    onAdd(selectedItem.id, qty || 1);
    setQty(1);
    detailsRef.current?.removeAttribute('open');
  }

  return (
    <details className="gear-add" ref={detailsRef}>
      <summary className="gear-add-btn">+ Gegenstand hinzufügen</summary>
      <div className="hp-popover-body gear-form">
        <select
          value={category}
          onChange={(e) => {
            setCategory(e.target.value as ItemCategory | '');
            setSelectedItemId('');
          }}
        >
          <option value="">Alle Kategorien</option>
          {categories.map((c) => (
            <option value={c} key={c}>{CATEGORY_LABELS[c] ?? c}</option>
          ))}
        </select>
        <select value={selectedItem?.id ?? ''} onChange={(e) => setSelectedItemId(e.target.value)}>
          {filteredItems.map((i) => (
            <option value={i.id} key={i.id}>{i.name}</option>
          ))}
        </select>
        <input
          type="number"
          min={1}
          value={qty}
          onChange={(e) => setQty(parseInt(e.target.value, 10) || 1)}
          placeholder="Anzahl"
        />
        <div className="hp-popover-actions">
          <button type="button" className="hp-btn confirm" onClick={handleAdd} disabled={!selectedItem}>Hinzufügen</button>
        </div>
      </div>
    </details>
  );
}

interface GearListProps {
  gear: GearItem[];
  catalog: ItemCatalogEntry[];
  onAdd: (itemId: string, qty: number) => void;
  onSave: (id: string, qty: number) => void;
  onRemove: (id: string) => void;
  onOpenDetail: (id: string) => void;
}

export function GearList({ gear, catalog, onAdd, onSave, onRemove, onOpenDetail }: GearListProps) {
  return (
    <>
      <div className="gear-list">
        {gear.map((item) => (
          <GearItemRow key={item.id} item={item} onSave={onSave} onRemove={onRemove} onOpenDetail={onOpenDetail} />
        ))}
      </div>
      <GearAddRow catalog={catalog} onAdd={onAdd} />
    </>
  );
}
