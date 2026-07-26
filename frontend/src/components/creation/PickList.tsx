import { useState } from 'react';

interface PickListProps {
  items: string[];
  selected: string[];
  max: number;
  onToggle: (name: string) => void;
  selectedListLabel: string;
  emptyText: string;
  searchPlaceholder?: string;
}

export function PickList({ items, selected, max, onToggle, selectedListLabel, emptyText, searchPlaceholder }: PickListProps) {
  const [query, setQuery] = useState('');
  const filtered = searchPlaceholder ? items.filter((i) => i.toLowerCase().includes(query.toLowerCase())) : items;

  return (
    <>
      {searchPlaceholder && (
        <div className="wizard-search">
          <input type="text" placeholder={searchPlaceholder} value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
      )}
      <div className="pick-counter" style={{ marginBottom: 10 }}>
        Ausgewählt: <b>{selected.length}</b> / <b>{max}</b>
      </div>
      <div className="chip-row">
        {filtered.map((name) => {
          const active = selected.includes(name);
          const disabled = !active && selected.length >= max;
          return (
            <button
              key={name}
              type="button"
              className={`chip${active ? ' active' : ''}${disabled ? ' disabled' : ''}`}
              onClick={disabled ? undefined : () => onToggle(name)}
            >
              {name}
            </button>
          );
        })}
      </div>
      <div className="selected-list">
        <div className="field-label">{selectedListLabel}</div>
        {selected.length === 0 ? (
          <div className="selected-empty">{emptyText}</div>
        ) : (
          <div className="chip-row">
            {selected.map((name) => (
              <span className="chip active" key={name}>{name}</span>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
