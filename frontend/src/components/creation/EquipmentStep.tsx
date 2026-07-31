import { useMemo, useState, type Dispatch, type SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions, ItemCategory } from '../../types/creationOptions';
import { createId } from '../../lib/id';
import { formatPrice, gearTotalValue } from '../../lib/creationCalculations';

interface EquipmentStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

const CATEGORY_LABELS: Record<ItemCategory, string> = {
  weapon: 'Waffen',
  armor: 'Rüstung',
  shield: 'Schilde',
  gear: 'Ausrüstung',
  tool: 'Werkzeug',
  consumable: 'Verbrauchsgüter',
};

export function EquipmentStep({ draft, options, setDraft }: EquipmentStepProps) {
  const [category, setCategory] = useState<ItemCategory | ''>('');
  const [selectedItemId, setSelectedItemId] = useState('');
  const [addQty, setAddQty] = useState(1);

  const categories = useMemo(
    () => Array.from(new Set(options.items.map((i) => i.category))) as ItemCategory[],
    [options.items]
  );
  const filteredItems = useMemo(
    () => (category ? options.items.filter((i) => i.category === category) : options.items),
    [options.items, category]
  );
  const selectedItem = options.items.find((i) => i.id === selectedItemId) ?? filteredItems[0];

  function addItem() {
    if (!selectedItem) return;
    const qty = addQty || 1;
    setDraft((prev) => {
      const existing = prev.gear.find((g) => g.itemId === selectedItem.id);
      if (existing) {
        return {
          ...prev,
          gear: prev.gear.map((g) => (g.itemId === selectedItem.id ? { ...g, qty: g.qty + qty } : g)),
        };
      }
      return {
        ...prev,
        gear: [...prev.gear, { id: createId(), itemId: selectedItem.id, name: selectedItem.name, qty, price: selectedItem.price }],
      };
    });
    setAddQty(1);
  }

  function setQty(id: string, qty: number) {
    setDraft((prev) => ({
      ...prev,
      gear: prev.gear.map((g) => (g.id === id ? { ...g, qty: Math.max(1, qty) } : g)),
    }));
  }

  function removeItem(id: string) {
    setDraft((prev) => ({ ...prev, gear: prev.gear.filter((g) => g.id !== id) }));
  }

  const totalValue = gearTotalValue(draft.gear);

  return (
    <>
      <div className="field-row" style={{ maxWidth: 220 }}>
        <div className="field-label">Startgold (GM)</div>
        <input
          type="number"
          className="text-input"
          min={0}
          value={draft.gold}
          onChange={(e) => setDraft((prev) => ({ ...prev, gold: parseInt(e.target.value, 10) || 0 }))}
        />
      </div>

      <div className="section-label">Inventar</div>
      <div>
        {draft.gear.map((item) => (
          <div className="eq-item" key={item.id}>
            <span className="eq-name">{item.name}</span>
            <input
              type="number"
              className="text-input eq-qty-input"
              min={1}
              value={item.qty}
              onChange={(e) => setQty(item.id, parseInt(e.target.value, 10) || 1)}
            />
            <span className="eq-price">{formatPrice(item.price)} / Stk.</span>
            <span className="eq-total">{formatPrice(item.price * item.qty)}</span>
            <button type="button" className="gear-del" onClick={() => removeItem(item.id)} title="Gegenstand entfernen">✕</button>
          </div>
        ))}
      </div>
      <div className="field-label" style={{ marginTop: 2 }}>Gesamtwert: {formatPrice(totalValue)}</div>

      <div className="section-label" style={{ marginTop: 14 }}>Aus der Ausrüstungsliste wählen</div>
      <div className="eq-add-row">
        <select
          className="text-input eq-category-select"
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
        <select
          className="text-input eq-name-input"
          value={selectedItem?.id ?? ''}
          onChange={(e) => setSelectedItemId(e.target.value)}
        >
          {filteredItems.map((i) => (
            <option value={i.id} key={i.id}>{i.name} — {formatPrice(i.price)}</option>
          ))}
        </select>
        <input
          type="number"
          className="text-input eq-qty-input"
          min={1}
          title="Anzahl"
          value={addQty}
          onChange={(e) => setAddQty(parseInt(e.target.value, 10) || 1)}
        />
        <button type="button" className="btn-confirm" onClick={addItem} disabled={!selectedItem}>Hinzufügen</button>
      </div>
      <div className="field-label" style={{ marginTop: 14 }}>
        Zuordnung zu Ausrüstungsplätzen (Kopf, Ringe, …) erfolgt später im Charakterbogen.
      </div>
    </>
  );
}
