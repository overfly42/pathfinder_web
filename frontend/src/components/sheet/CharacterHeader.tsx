import type { Character } from '../../types/character';

export function CharacterHeader({ character }: { character: Character }) {
  return (
    <div className="char-top">
      <div className="portrait" />
      <div>
        <p className="char-name">{character.name}</p>
        <p className="char-sub">
          {character.race} · {character.className} ({character.archetype}) · Stufe {character.level}
        </p>
      </div>
    </div>
  );
}
