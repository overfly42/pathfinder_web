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

  const featByName = new Map(options.feats.map((f) => [f.name, f]));
  const notYetTaken = options.feats.filter((f) => !progression.feats.includes(f.name));
  const available = notYetTaken.map((f) => f.name);
  const combatAvailable = notYetTaken.filter((f) => f.type === 'combat').map((f) => f.name);
  const weapons = options.items.filter((i) => i.category === 'weapon');

  function select(name: string) {
    setDraft((prev) => {
      if (prev.newFeat === name) {
        const nextSubChoices = { ...prev.featSubChoices };
        delete nextSubChoices[name];
        return { ...prev, newFeat: null, featSubChoices: nextSubChoices };
      }
      return { ...prev, newFeat: name };
    });
  }

  function selectBonus(name: string) {
    setDraft((prev) => {
      if (prev.newBonusFeat === name) {
        const nextSubChoices = { ...prev.featSubChoices };
        delete nextSubChoices[name];
        return { ...prev, newBonusFeat: null, featSubChoices: nextSubChoices };
      }
      return { ...prev, newBonusFeat: name };
    });
  }

  function setSubChoice(name: string, value: string) {
    setDraft((prev) => ({ ...prev, featSubChoices: { ...prev.featSubChoices, [name]: value } }));
  }

  const needingSubChoice = [draft.newFeat, draft.newBonusFeat]
    .map((name) => (name ? featByName.get(name) : undefined))
    .filter((feat): feat is NonNullable<typeof feat> => feat !== undefined && feat.subChoiceType !== null);

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
      {needingSubChoice.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="field-label">Talent-Details</div>
          {needingSubChoice.map((feat) => (
            <div className="field-row" key={feat.id} style={{ maxWidth: 320 }}>
              <div className="field-label">{feat.name}</div>
              {feat.subChoiceType === 'weapon' && (
                <select
                  value={draft.featSubChoices[feat.name] ?? ''}
                  onChange={(e) => setSubChoice(feat.name, e.target.value)}
                >
                  <option value="">– Waffe wählen –</option>
                  {weapons.map((w) => (
                    <option key={w.id} value={w.id}>{w.name}</option>
                  ))}
                </select>
              )}
              {feat.subChoiceType === 'skill' && (
                <select
                  value={draft.featSubChoices[feat.name] ?? ''}
                  onChange={(e) => setSubChoice(feat.name, e.target.value)}
                >
                  <option value="">– Fertigkeit wählen –</option>
                  {options.skills.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              )}
              {feat.subChoiceType === 'spell_school' && (
                <select
                  value={draft.featSubChoices[feat.name] ?? ''}
                  onChange={(e) => setSubChoice(feat.name, e.target.value)}
                >
                  <option value="">– Zauberschule wählen –</option>
                  {options.spellSchools.map((school) => (
                    <option key={school} value={school}>{school}</option>
                  ))}
                </select>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
