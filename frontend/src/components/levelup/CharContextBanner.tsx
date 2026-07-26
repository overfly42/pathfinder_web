import type { CharacterProgression } from '../../types/characterProgression';
import { getNewLevel, getOldTotalLevel } from '../../lib/levelUpCalculations';

export function CharContextBanner({ progression }: { progression: CharacterProgression }) {
  const primary = progression.classes[0];
  const subtitle = primary ? `${progression.race} · ${primary.className} (${primary.archetype})` : progression.race;

  return (
    <div className="char-context-banner">
      <div className="who">
        {progression.name}
        <span className="sub">{subtitle}</span>
      </div>
      <div className="transition">
        Stufe {getOldTotalLevel(progression)}
        <span className="arrow">→</span>
        {getNewLevel(progression)}
      </div>
    </div>
  );
}
