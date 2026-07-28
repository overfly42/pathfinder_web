import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Character, EffectsView } from '../../types/character';
import type { SearchEntry } from '../../search/types';
import { useAppState } from '../../state/AppStateContext';
import { useCharacterNames } from '../../hooks/useCharacterNames';
import { useClickOutside } from '../../hooks/useClickOutside';
import { GlobalSearch } from './GlobalSearch';

interface AppHeaderProps {
  /** Null when the current user owns no characters yet (e.g. right after being created). */
  character: Character | null;
  effects: EffectsView | null;
  onJump: (entry: SearchEntry) => void;
}

function UserPicker() {
  const { users, currentUserId, setCurrentUserId } = useAppState();
  const [open, setOpen] = useState(false);
  const containerRef = useClickOutside<HTMLDivElement>(() => setOpen(false));
  const current = users.find((u) => u.id === currentUserId);

  return (
    <div className="picker" style={{ position: 'relative' }} ref={containerRef}>
      <label>Nutzer</label>
      <button type="button" className="picker-control" onClick={() => setOpen((v) => !v)}>
        <div className="avatar" />
        <div className="label">{current?.name ?? '—'}</div>
        <div className="chev">▾</div>
      </button>
      <div className={`search-results${open ? ' open' : ''}`}>
        {users.map((user) => (
          <div
            className="search-result-item"
            key={user.id}
            onClick={() => {
              setCurrentUserId(user.id);
              setOpen(false);
            }}
          >
            <span className="sr-label">{user.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function CharacterPicker({ currentCharacterName }: { currentCharacterName: string }) {
  const {
    visibleCharacterIds,
    currentCharacterId,
    setCurrentCharacterId,
    nameOverrides,
    renameCharacter,
    removeCharacter,
  } = useAppState();
  const [open, setOpen] = useState(false);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const containerRef = useClickOutside<HTMLDivElement>(() => setOpen(false));
  const names = useCharacterNames(visibleCharacterIds);

  function displayName(id: string) {
    return nameOverrides[id] ?? names[id] ?? id;
  }

  function startRename(id: string) {
    setRenamingId(id);
    setRenameValue(displayName(id));
  }

  function confirmRename() {
    if (renamingId) renameCharacter(renamingId, renameValue);
    setRenamingId(null);
  }

  return (
    <div className="picker" style={{ position: 'relative' }} ref={containerRef}>
      <label>Charakter</label>
      <button type="button" className="picker-control" onClick={() => setOpen((v) => !v)}>
        <div className="avatar" />
        <div className="label">{currentCharacterName}</div>
        <div className="chev">▾</div>
      </button>
      <div className={`search-results${open ? ' open' : ''}`}>
        {visibleCharacterIds.length === 0 && (
          <div className="search-empty">Diesem Nutzer sind noch keine Charaktere zugeordnet.</div>
        )}
        {visibleCharacterIds.map((id) => (
          <div className="search-result-item" key={id} style={{ justifyContent: 'space-between' }}>
            {renamingId === id ? (
              <>
                <input
                  type="text"
                  value={renameValue}
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && confirmRename()}
                  style={{ flex: 1, marginRight: 8 }}
                />
                <button type="button" className="hp-btn confirm" onClick={confirmRename}>✓</button>
              </>
            ) : (
              <>
                <span
                  className="sr-label"
                  style={{ flex: 1, fontWeight: id === currentCharacterId ? 700 : 400 }}
                  onClick={() => {
                    setCurrentCharacterId(id);
                    setOpen(false);
                  }}
                >
                  {displayName(id)}
                </span>
                <button
                  type="button"
                  className="hp-btn ghost"
                  title="Umbenennen"
                  onClick={(e) => {
                    e.stopPropagation();
                    startRename(id);
                  }}
                >
                  ✎
                </button>
                <button
                  type="button"
                  className="gear-del"
                  title="Charakter löschen"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeCharacter(id);
                  }}
                >
                  ✕
                </button>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function AddUserButton() {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [name, setName] = useState('');
  const { addUser } = useAppState();

  async function handleAdd() {
    const trimmed = name.trim();
    if (!trimmed) return;
    try {
      await addUser(trimmed);
      setName('');
      detailsRef.current?.removeAttribute('open');
    } catch (err) {
      console.error('Failed to create user', err);
    }
  }

  return (
    <details className="gear-add" ref={detailsRef}>
      <summary className="btn-outline">
        <span className="plus">+</span>
        Neuer Nutzer
      </summary>
      <div className="hp-popover-body gear-form">
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Nutzername" />
        <div className="hp-popover-actions">
          <button type="button" className="hp-btn confirm" onClick={handleAdd}>Hinzufügen</button>
        </div>
      </div>
    </details>
  );
}

export function AppHeader({ character, effects, onJump }: AppHeaderProps) {
  return (
    <header>
      <div className="brand">
        <div className="sigil">P</div>
        <div>
          <div className="title">GEFÄHRTENBUCH</div>
          <span className="subtitle">Pathfinder · Kompendium &amp; Spieltisch</span>
        </div>
      </div>

      <UserPicker />
      <CharacterPicker currentCharacterName={character?.name ?? '— kein Charakter —'} />

      {character && effects && <GlobalSearch character={character} effects={effects} onJump={onJump} />}

      <div className="spacer" />

      <div className="header-actions">
        <AddUserButton />
        <Link className="btn-outline" to="/create">
          <span className="plus">+</span>
          Neuer Charakter
        </Link>
        {character && (
          <Link className="btn-levelup" to={`/levelup/${character.id}`}>
            <span className="star">✦</span>
            Stufenaufstieg
          </Link>
        )}
        <select
          className="lang-select"
          title="Sprache"
          aria-label="Sprache"
          defaultValue="de"
          onChange={(e) => {
            document.documentElement.lang = e.target.value;
          }}
        >
          <option value="de">DE</option>
          <option value="en">EN</option>
        </select>
      </div>
    </header>
  );
}
