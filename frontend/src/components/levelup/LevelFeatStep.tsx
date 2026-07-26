import { useEffect, type Dispatch, type SetStateAction } from 'react';
import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import { featGrantedThisLevel, getNewLevel } from '../../lib/levelUpCalculations';
import { SingleChipPicker } from './SingleChipPicker';

interface LevelFeatStepProps {
  progression: CharacterProgression;
  options: LevelUpOptions;
  draft: LevelUpDraft;
  setDraft: Dispatch<SetStateAction<LevelUpDraft>>;
}

export function LevelFeatStep({ progression, options, draft, setDraft }: LevelFeatStepProps) {
  const granted = featGrantedThisLevel(getNewLevel(progression));

  useEffect(() => {
    if (!granted) setDraft((prev) => (prev.newFeat === null ? prev : { ...prev, newFeat: null }));
  }, [granted, setDraft]);

  if (!granted) {
    return <div className="warning-note">Auf dieser Stufe gibt es kein neues Talent (nur auf Stufe 1 und ungeraden Stufen).</div>;
  }

  const available = options.feats.filter((f) => !progression.feats.includes(f));

  function select(name: string) {
    setDraft((prev) => ({ ...prev, newFeat: prev.newFeat === name ? null : name }));
  }

  return (
    <SingleChipPicker items={available} selected={draft.newFeat} onSelect={select} searchPlaceholder="Talente durchsuchen …" />
  );
}
