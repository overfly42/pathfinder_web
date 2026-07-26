import { useState } from 'react';

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
  itemName: string | null;
  onClose: () => void;
}

export function ItemDetailModal({ itemName, onClose }: ItemDetailModalProps) {
  const [enhancement, setEnhancement] = useState('+1');
  const [properties, setProperties] = useState<string[]>([]);

  function toggleProperty(property: string) {
    setProperties((prev) =>
      prev.includes(property) ? prev.filter((p) => p !== property) : [...prev, property],
    );
  }

  return (
    <div
      className={`modal-overlay${itemName ? ' open' : ''}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{itemName ?? 'Gegenstand'}</h2>
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
          <button type="button" className="hp-btn confirm" onClick={onClose}>Fertig</button>
        </div>
      </div>
    </div>
  );
}
