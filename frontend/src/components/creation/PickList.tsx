import { useState } from 'react';

export interface PickListItem {
  id: string;
  label: string;
}

interface PickListProps {
  items: PickListItem[];
  selected: string[];
  max: number;
  onToggle: (id: string) => void;
  selectedListLabel: string;
  emptyText: string;
  searchPlaceholder?: string;
  /** Extra ids to render disabled beyond the max-based ones (e.g. traits
   *  that would conflict with an already-chosen trait's area). */
  disabledIds?: string[];
}

export function PickList({ items, selected, max, onToggle, selectedListLabel, emptyText, searchPlaceholder, disabledIds }: PickListProps) {
  const [query, setQuery] = useState('');
  const filtered = searchPlaceholder ? items.filter((i) => i.label.toLowerCase().includes(query.toLowerCase())) : items;
  const labelById = new Map(items.map((i) => [i.id, i.label]));
  const extraDisabledIds = new Set(disabledIds ?? []);

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
        {filtered.map((item) => {
          const active = selected.includes(item.id);
          const disabled = !active && (selected.length >= max || extraDisabledIds.has(item.id));
          return (
            <button
              key={item.id}
              type="button"
              className={`chip${active ? ' active' : ''}${disabled ? ' disabled' : ''}`}
              onClick={disabled ? undefined : () => onToggle(item.id)}
            >
              {item.label}
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
            {selected.map((id) => (
              <span className="chip active" key={id}>{labelById.get(id) ?? id}</span>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
