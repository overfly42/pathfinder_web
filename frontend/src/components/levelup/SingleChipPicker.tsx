import { useState } from 'react';

interface SingleChipPickerProps {
  items: string[];
  selected: string | null;
  onSelect: (name: string) => void;
  searchPlaceholder?: string;
}

/** Counter + chip-row for a "pick exactly one (or none)" choice — no selected-list
 *  section, unlike creation's multi-pick PickList (the mock has none here either). */
export function SingleChipPicker({ items, selected, onSelect, searchPlaceholder }: SingleChipPickerProps) {
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
        Ausgewählt: <b>{selected ? 1 : 0}</b> / <b>1</b>
      </div>
      <div className="chip-row">
        {filtered.map((name) => (
          <button
            key={name}
            type="button"
            className={`chip${selected === name ? ' active' : ''}`}
            onClick={() => onSelect(name)}
          >
            {name}
          </button>
        ))}
      </div>
    </>
  );
}
