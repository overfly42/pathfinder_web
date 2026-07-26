import type { AbilityScore } from '../../types/character';

export function AbilityScores({ abilities }: { abilities: AbilityScore[] }) {
  return (
    <div className="abilities">
      {abilities.map((ability) => (
        <div className="ability" key={ability.key}>
          <div className="name">{ability.label}</div>
          <div className="score">{ability.score}</div>
          <div className="mod">{ability.mod}</div>
        </div>
      ))}
    </div>
  );
}
