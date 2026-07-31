import { useEffect, type Dispatch, type SetStateAction } from 'react';
import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import {
  classBonusFeatGrantedThisLevel,
  featGrantedThisLevel,
  getNewLevel,
  getReceivingClassAndLevel,
} from '../../lib/levelUpCalculations';
import { SingleChipPicker } from './SingleChipPicker';

interface LevelFeatStepProps {
  progression: CharacterProgression;
  options: LevelUpOptions;
  draft: LevelUpDraft;
  setDraft: Dispatch<SetStateAction<LevelUpDraft>>;
}

export function LevelFeatStep({ progression, options, draft, setDraft }: LevelFeatStepProps) {
  const newLevel = getNewLevel(progression);
  const granted = featGrantedThisLevel(newLevel);
  const receiving = getReceivingClassAndLevel(progression, draft.target);
  const bonusGranted = classBonusFeatGrantedThisLevel(receiving?.className ?? null, receiving?.level ?? null, options.classes);

  useEffect(() => {
    if (!granted) setDraft((prev) => (prev.newFeat === null ? prev : { ...prev, newFeat: null }));
  }, [granted, setDraft]);

  useEffect(() => {
    if (!bonusGranted) setDraft((prev) => (prev.newBonusFeat === null ? prev : { ...prev, newBonusFeat: null }));
  }, [bonusGranted, setDraft]);

  if (!granted && !bonusGranted) {
    return <div className="warning-note">Auf dieser Stufe gibt es kein neues Talent (nur auf Stufe 1 und ungeraden Stufen).</div>;
  }

  const notYetTaken = options.feats.filter((f) => !progression.feats.includes(f.name));
  const available = notYetTaken.map((f) => f.name);
  const combatAvailable = notYetTaken.filter((f) => f.type === 'combat').map((f) => f.name);

  function select(name: string) {
    setDraft((prev) => ({ ...prev, newFeat: prev.newFeat === name ? null : name }));
  }

  function selectBonus(name: string) {
    setDraft((prev) => ({ ...prev, newBonusFeat: prev.newBonusFeat === name ? null : name }));
  }

  return (
    <>
      {granted && (
        <SingleChipPicker items={available} selected={draft.newFeat} onSelect={select} searchPlaceholder="Talente durchsuchen …" />
      )}
      {bonusGranted && (
        <>
          <div className="og-heading" style={{ marginTop: granted ? 16 : 0 }}>
            Bonus-Kampftalent ({receiving?.className}, Stufe {receiving?.level})
          </div>
          <SingleChipPicker
            items={combatAvailable}
            selected={draft.newBonusFeat}
            onSelect={selectBonus}
            searchPlaceholder="Bonus-Kampftalente durchsuchen …"
          />
        </>
      )}
    </>
  );
}
