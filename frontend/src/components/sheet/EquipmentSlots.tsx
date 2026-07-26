import type { EquipmentSlot } from '../../types/character';

interface EquipmentSlotsProps {
  slots: EquipmentSlot[];
  onChange: (key: string, value: string) => void;
}

function SlotSelect({ slot, onChange }: { slot: EquipmentSlot; onChange: (key: string, value: string) => void }) {
  return (
    <div
      className={`slot ${slot.side}${slot.selected ? ' filled' : ''}`}
      style={{ gridRow: slot.row }}
      id={`slot-${slot.key}`}
    >
      <label>{slot.label}</label>
      <select value={slot.selected} onChange={(e) => onChange(slot.key, e.target.value)}>
        <option value="">— leer —</option>
        {slot.options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </div>
  );
}

export function EquipmentSlots({ slots, onChange }: EquipmentSlotsProps) {
  const left = slots.filter((slot) => slot.side === 'left');
  const right = slots.filter((slot) => slot.side === 'right');

  return (
    <div className="paperdoll">
      <div className="paperdoll-figure">
        <svg viewBox="0 0 140 320" xmlns="http://www.w3.org/2000/svg">
          <line x1="58" y1="152" x2="50" y2="292" stroke="var(--parchment-2)" strokeWidth="22" strokeLinecap="round" />
          <line x1="82" y1="152" x2="90" y2="292" stroke="var(--parchment-2)" strokeWidth="22" strokeLinecap="round" />
          <ellipse cx="46" cy="300" rx="16" ry="8" fill="var(--brass-dark)" />
          <ellipse cx="94" cy="300" rx="16" ry="8" fill="var(--brass-dark)" />
          <line x1="38" y1="78" x2="20" y2="176" stroke="var(--parchment-2)" strokeWidth="18" strokeLinecap="round" />
          <line x1="102" y1="78" x2="120" y2="176" stroke="var(--parchment-2)" strokeWidth="18" strokeLinecap="round" />
          <circle cx="18" cy="182" r="11" fill="var(--parchment-2)" stroke="var(--ink-soft)" strokeWidth="1.5" />
          <circle cx="122" cy="182" r="11" fill="var(--parchment-2)" stroke="var(--ink-soft)" strokeWidth="1.5" />
          <path d="M35,72 Q70,58 105,72 L112,152 Q70,166 28,152 Z" fill="var(--parchment-2)" stroke="var(--ink-soft)" strokeWidth="2" />
          <rect x="32" y="140" width="76" height="13" rx="3" fill="var(--brass)" stroke="var(--brass-dark)" strokeWidth="1.5" />
          <rect x="60" y="52" width="20" height="18" fill="var(--parchment-2)" stroke="var(--ink-soft)" strokeWidth="2" />
          <circle cx="70" cy="32" r="24" fill="var(--parchment-2)" stroke="var(--ink-soft)" strokeWidth="2" />
          <rect x="47" y="24" width="46" height="7" rx="3" fill="var(--brass)" opacity="0.85" />
          <circle cx="18" cy="182" r="4" fill="var(--brass-light)" />
          <circle cx="122" cy="182" r="4" fill="var(--brass-light)" />
        </svg>
      </div>

      {left.map((slot) => (
        <SlotSelect key={slot.key} slot={slot} onChange={onChange} />
      ))}
      {right.map((slot) => (
        <SlotSelect key={slot.key} slot={slot} onChange={onChange} />
      ))}
    </div>
  );
}
