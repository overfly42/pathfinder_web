import { Link } from 'react-router-dom';
import type { Character } from '../../types/character';
import type { SearchEntry } from '../../search/types';
import { GlobalSearch } from './GlobalSearch';

interface AppHeaderProps {
  character: Character;
  onJump: (entry: SearchEntry) => void;
}

export function AppHeader({ character, onJump }: AppHeaderProps) {
  return (
    <header>
      <div className="brand">
        <div className="sigil">P</div>
        <div>
          <div className="title">GEFÄHRTENBUCH</div>
          <span className="subtitle">Pathfinder · Kompendium &amp; Spieltisch</span>
        </div>
      </div>

      <div className="picker">
        <label>Nutzer</label>
        <div className="picker-control">
          <div className="avatar" />
          <div className="label">Anna</div>
          <div className="chev">▾</div>
        </div>
      </div>

      <div className="picker">
        <label>Charakter</label>
        <div className="picker-control">
          <div className="avatar" />
          <div className="label">{character.name}</div>
          <div className="chev">▾</div>
        </div>
      </div>

      <GlobalSearch character={character} onJump={onJump} />

      <div className="spacer" />

      <div className="header-actions">
        <div className="btn-outline">
          <span className="plus">+</span>
          Neuer Nutzer
        </div>
        <div className="btn-outline">
          <span className="plus">+</span>
          Neuer Charakter
        </div>
        <Link className="btn-levelup" to={`/levelup/${character.id}`}>
          <span className="star">✦</span>
          Stufenaufstieg
        </Link>
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
