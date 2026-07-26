import { useMemo, useState } from 'react';
import type { Character } from '../../types/character';
import { buildSearchIndex } from '../../search/buildSearchIndex';
import { matchesQuery } from '../../search/matchesQuery';
import type { SearchEntry } from '../../search/types';
import { useClickOutside } from '../../hooks/useClickOutside';

interface GlobalSearchProps {
  character: Character;
  onJump: (entry: SearchEntry) => void;
}

export function GlobalSearch({ character, onJump }: GlobalSearchProps) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const index = useMemo(() => buildSearchIndex(character), [character]);
  const containerRef = useClickOutside<HTMLDivElement>(() => setOpen(false));

  const q = query.trim().toLowerCase();
  const matches: SearchEntry[] = q ? index.filter((entry) => matchesQuery(entry, q)).slice(0, 8) : [];

  function handleChange(value: string) {
    setQuery(value);
    setOpen(value.trim().length > 0);
  }

  function handleJump(entry: SearchEntry) {
    onJump(entry);
    setOpen(false);
    setQuery('');
  }

  return (
    <div className="global-search" ref={containerRef}>
      <span className="search-icon">🔍</span>
      <input
        type="text"
        placeholder="Suche: GAB, Wahrnehmung, Talente …"
        autoComplete="off"
        value={query}
        onChange={(e) => handleChange(e.target.value)}
        onFocus={() => setOpen(query.trim().length > 0)}
      />
      <div className={`search-results${open ? ' open' : ''}`}>
        {open && matches.length === 0 && <div className="search-empty">Keine Treffer</div>}
        {open &&
          matches.map((match) => (
            <div className="search-result-item" key={match.id} onClick={() => handleJump(match)}>
              <span className="sr-label">{match.label}</span>
              {match.value && <span className="sr-value">{match.value}</span>}
              <span className="sr-cat">{match.category}</span>
            </div>
          ))}
      </div>
    </div>
  );
}
