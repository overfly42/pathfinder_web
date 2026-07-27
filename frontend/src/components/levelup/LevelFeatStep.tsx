import { useEffect, type Dispatch, type SetStateAction } from 'react';
import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import {
  featGrantedThisLevel,
  fighterBonusFeatGrantedThisLevel,
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
  const receivingClassName = getReceivingClassAndLevel(progression, draft.target)?.className ?? null;
  const bonusGranted = fighterBonusFeatGrantedThisLevel(receivingClassName, newLevel);

  useEffect(() => {
    if (!granted) setDraft((prev) => (prev.newFeat === null ? prev : { ...prev, newFeat: null }));
  }, [granted, setDraft]);

  useEffect(() => {
    if (!bonusGranted) setDraft((prev) => (prev.newBonusFeat === null ? prev : { ...prev, newBonusFeat: null }));
  }, [bonusGranted, setDraft]);

  if (!granted && !bonusGranted) {
    return <div className="warning-note">Auf dieser Stufe gibt es kein neues Talent (nur auf Stufe 1 und ungeraden Stufen).</div>;
  }

  const available = options.feats.filter((f) => !progression.feats.includes(f));

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
            Bonus-Kampftalent (Krieger, gerade Stufe)
          </div>
          {/* feats.json has no combat-feat category yet, so this offers the full feat list rather
              than a hardcoded combat-feat name list — narrow it once feat metadata exists. */}
          <SingleChipPicker
            items={available}
            selected={draft.newBonusFeat}
            onSelect={selectBonus}
            searchPlaceholder="Bonus-Kampftalente durchsuchen …"
          />
        </>
      )}
    </>
  );
}
