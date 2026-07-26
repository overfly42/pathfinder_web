import type { Dispatch, SetStateAction } from 'react';
import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import { getReceivingClassName } from '../../lib/levelUpCalculations';
import { SingleChipPicker } from './SingleChipPicker';

interface LevelSpellStepProps {
  progression: CharacterProgression;
  options: LevelUpOptions;
  draft: LevelUpDraft;
  setDraft: Dispatch<SetStateAction<LevelUpDraft>>;
}

export function LevelSpellStep({ progression, options, draft, setDraft }: LevelSpellStepProps) {
  const className = getReceivingClassName(progression, draft.target);
  const classDef = className ? options.classes.find((c) => c.name === className) : undefined;
  const type = classDef?.spellType ?? 'none';

  if (type !== 'arcane-prepared' && type !== 'spontaneous') {
    const note =
      type === 'divine-prepared'
        ? 'Diese Klasse bereitet Zauber frei aus der vollen Klassen-Zauberliste vor — hier ist keine Auswahl nötig.'
        : 'Diese Klasse hat keine Zauberfähigkeit.';
    return <div className="selected-empty">{note}</div>;
  }

  const alreadyKnown = (className && progression.spellsKnown[className]) || [];
  const known = ((className && options.spellsByClass[className]) || []).filter((n) => !alreadyKnown.includes(n));
  const typeLabel = type === 'arcane-prepared' ? 'Zauberbuch (arkan, vorbereitend)' : 'Bekannte Zauber (spontan)';

  function select(name: string) {
    setDraft((prev) => ({ ...prev, newSpell: prev.newSpell === name ? null : name }));
  }

  return (
    <div className="summary-block">
      <div className="sb-title">{className} — {typeLabel} — neuer Zauber diese Stufe</div>
      <SingleChipPicker items={known} selected={draft.newSpell} onSelect={select} />
    </div>
  );
}
