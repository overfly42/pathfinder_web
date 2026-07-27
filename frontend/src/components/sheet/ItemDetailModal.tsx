import { useEffect, useState } from 'react';
import type { GearItem } from '../../types/character';

const ENHANCEMENT_OPTIONS = ['+0', '+1', '+2', '+3', '+4', '+5'];
const WEAPON_PROPERTIES = [
  'Flammend',
  'Eisig',
  'Stoßend',
  'Scharf',
  'Geschwindigkeit',
  'Wachsam',
  'Tödliche Präzision',
  'Geisterberührung',
];

interface ItemDetailModalProps {
  item: GearItem | null;
  onClose: () => void;
  onSave: (id: string, enhancement: string, properties: string[]) => void;
}

export function ItemDetailModal({ item, onClose, onSave }: ItemDetailModalProps) {
  const [enhancement, setEnhancement] = useState('+0');
  const [properties, setProperties] = useState<string[]>([]);

  // Re-seed the edit state from the actual item's stored values every time a (different) item
  // is opened, instead of keeping whatever the previous item left behind.
  useEffect(() => {
    if (!item) return;
    setEnhancement(item.enhancement ?? '+0');
    setProperties(item.properties ?? []);
  }, [item]);

  function toggleProperty(property: string) {
    setProperties((prev) =>
      prev.includes(property) ? prev.filter((p) => p !== property) : [...prev, property],
    );
  }

  function handleDone() {
    if (item) onSave(item.id, enhancement, properties);
    onClose();
  }

  return (
    <div
      className={`modal-overlay${item ? ' open' : ''}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{item?.name ?? 'Gegenstand'}</h2>
          <button type="button" className="modal-close" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">
          <div className="detail-group">
            <div className="detail-label">Verstärkung</div>
            <div className="chip-row single">
              {ENHANCEMENT_OPTIONS.map((value) => (
                <button
                  key={value}
                  type="button"
                  className={`chip${enhancement === value ? ' active' : ''}`}
                  onClick={() => setEnhancement(value)}
                >
                  {value}
                </button>
              ))}
            </div>
          </div>

          <div className="detail-group">
            <div className="detail-label">Waffeneigenschaften</div>
            <div className="chip-row multi">
              {WEAPON_PROPERTIES.map((property) => (
                <button
                  key={property}
                  type="button"
                  className={`chip${properties.includes(property) ? ' active' : ''}`}
                  onClick={() => toggleProperty(property)}
                >
                  {property}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="modal-foot">
          <button type="button" className="hp-btn confirm" onClick={handleDone}>Fertig</button>
        </div>
      </div>
    </div>
  );
}
