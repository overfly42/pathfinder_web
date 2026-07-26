import { useState, type Dispatch, type SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import { createId } from '../../lib/id';
import { formatPrice, gearTotalValue, priceForItemName } from '../../lib/creationCalculations';

interface EquipmentStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

export function EquipmentStep({ draft, options, setDraft }: EquipmentStepProps) {
  const [addName, setAddName] = useState('');
  const [addPrice, setAddPrice] = useState(0);
  const [addQty, setAddQty] = useState(1);

  function onNameInput(value: string) {
    setAddName(value);
    const price = priceForItemName(options, value.trim());
    if (price !== null) setAddPrice(price);
  }

  function addItem() {
    const name = addName.trim();
    if (!name) return;
    setDraft((prev) => ({ ...prev, gear: [...prev.gear, { id: createId(), name, qty: addQty || 1, price: addPrice || 0 }] }));
    setAddName('');
    setAddPrice(0);
    setAddQty(1);
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
            <span className="eq-qty">{item.qty}×</span>
            <span className="eq-price">{formatPrice(item.price)} / Stk.</span>
            <span className="eq-total">{formatPrice(item.price * item.qty)}</span>
            <button type="button" className="gear-del" onClick={() => removeItem(item.id)} title="Gegenstand entfernen">✕</button>
          </div>
        ))}
      </div>
      <div className="field-label" style={{ marginTop: 2 }}>Gesamtwert: {formatPrice(totalValue)}</div>

      <div className="eq-add-row">
        <input
          type="text"
          className="text-input eq-name-input"
          placeholder="Bezeichnung eingeben oder auswählen …"
          list="gearItemOptions"
          autoComplete="off"
          value={addName}
          onChange={(e) => onNameInput(e.target.value)}
        />
        <input
          type="number"
          className="text-input eq-price-input"
          min={0}
          step={0.01}
          placeholder="Preis"
          title="Preis pro Stück (GM)"
          value={addPrice}
          onChange={(e) => setAddPrice(parseFloat(e.target.value) || 0)}
        />
        <input
          type="number"
          className="text-input eq-qty-input"
          min={1}
          title="Anzahl"
          value={addQty}
          onChange={(e) => setAddQty(parseInt(e.target.value, 10) || 1)}
        />
        <button type="button" className="btn-confirm" onClick={addItem}>Hinzufügen</button>
        <datalist id="gearItemOptions">
          {options.items.map((i) => (
            <option value={i.name} key={i.name} />
          ))}
        </datalist>
      </div>
      <div className="eq-cost-preview">Kosten: <b>{formatPrice(addPrice * addQty)}</b></div>
      <div className="field-label" style={{ marginTop: 14 }}>
        Zuordnung zu Ausrüstungsplätzen (Kopf, Ringe, …) erfolgt später im Charakterbogen.
      </div>
    </>
  );
}
