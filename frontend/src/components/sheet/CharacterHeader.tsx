import type { Character } from '../../types/character';
import { ALIGNMENTS, alignmentLabel } from '../../lib/alignment';

interface CharacterHeaderProps {
  character: Character;
  /** Only for a real (DB-backed) character — the backend checks the new alignment against the
   *  character's classes (`PATCH .../alignment`). Without it the alignment is shown read-only. */
  onChangeAlignment?: (alignment: string | null) => void;
}

export function CharacterHeader({ character, onChangeAlignment }: CharacterHeaderProps) {
  return (
    <div className="char-top">
      <div className="portrait" />
      <div>
        <p className="char-name">{character.name}</p>
        <p className="char-sub">
          {character.companion
            ? `${character.race} · ${character.companion.trackLabel} · ${
                character.companion.track === 'familiar' ? `Stufe ${character.level} (Meister)` : `${character.level} TW`
              }`
            : `${character.race} · ${character.className} (${character.archetype}) · Stufe ${character.level}`}
          {!onChangeAlignment && character.alignment && <> · {alignmentLabel(character.alignment)}</>}
        </p>
        {onChangeAlignment && (
          <p className="char-sub">
            <select
              className="char-alignment"
              aria-label="Gesinnung"
              value={character.alignment ?? ''}
              onChange={(e) => onChangeAlignment(e.target.value || null)}
            >
              <option value="">— Gesinnung festlegen —</option>
              {ALIGNMENTS.map((a) => (
                <option value={a.code} key={a.code}>{a.label}</option>
              ))}
            </select>
          </p>
        )}
      </div>
    </div>
  );
}
