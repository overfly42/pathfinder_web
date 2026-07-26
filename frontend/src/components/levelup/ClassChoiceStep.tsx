import type { Dispatch, SetStateAction } from 'react';
import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import { getReceivingClassAndLevel } from '../../lib/levelUpCalculations';
import { OptionGroupPicker } from '../primitives/OptionGroupPicker';

interface ClassChoiceStepProps {
  progression: CharacterProgression;
  options: LevelUpOptions;
  draft: LevelUpDraft;
  setDraft: Dispatch<SetStateAction<LevelUpDraft>>;
}

export function ClassChoiceStep({ progression, options, draft, setDraft }: ClassChoiceStepProps) {
  const info = getReceivingClassAndLevel(progression, draft.target);

  if (!info) {
    return <div className="warning-note">Bitte zuerst in Schritt 1 festlegen, welche Klasse diese Stufe erhält.</div>;
  }

  const groups = (options.classLevelOptions[info.className] ?? []).filter((g) => g.levels.includes(info.level));

  if (groups.length === 0) {
    return (
      <div className="warning-note">
        Auf dieser Stufe ({info.className} {info.level}) gibt es keine zusätzliche Klassenwahl.
      </div>
    );
  }

  function toggle(groupKey: string, choice: string, max: number) {
    setDraft((prev) => {
      const chosen = prev.existingLevelOptionSelections[groupKey] ?? [];
      const idx = chosen.indexOf(choice);
      let next: string[];
      if (idx !== -1) next = chosen.filter((c) => c !== choice);
      else if (chosen.length < max) next = [...chosen, choice];
      else next = chosen;
      return { ...prev, existingLevelOptionSelections: { ...prev.existingLevelOptionSelections, [groupKey]: next } };
    });
  }

  return (
    <>
      <div className="og-heading">{info.className} — neue Wahlmöglichkeit auf Stufe {info.level}</div>
      {groups.map((g) => (
        <OptionGroupPicker
          key={g.key}
          label={g.label}
          max={g.max}
          choices={g.choices}
          selected={draft.existingLevelOptionSelections[g.key] ?? []}
          onToggle={(choice) => toggle(g.key, choice, g.max)}
        />
      ))}
    </>
  );
}
