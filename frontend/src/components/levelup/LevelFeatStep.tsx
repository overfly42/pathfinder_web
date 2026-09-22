import { useEffect, type Dispatch, type SetStateAction } from 'react';
import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import {
  classBonusFeatGrantedThisLevel,
  featGrantedThisLevel,
  getNewLevel,
  getReceivingClassAndLevel,
  receivingArchetypeNames,
  secondaryClassFeatureGrantedThisLevel,
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
  // The Sekundärklasse rule spends this level's normal talent on one of its
  // own features instead (see this function's own docstring) — the step
  // still shows (matches `granted`), but as an info note instead of a picker.
  const secondaryFeatureGranted = secondaryClassFeatureGrantedThisLevel(newLevel, progression);
  const baseFeatPickable = granted && !secondaryFeatureGranted;
  const receiving = getReceivingClassAndLevel(progression, draft.target);
  const bonusGranted = classBonusFeatGrantedThisLevel(receiving?.className ?? null, receiving?.level ?? null, options.classes);
  const receivingClass = options.classes.find((c) => c.name === receiving?.className);
  // An archetype whose own class ability replaces the base class's
  // bonus-feat grants (e.g. Meister aller Kampfstile swapping Mönch's
  // closed Bonustalent list for an open `kampfkunst`-type pick) overrides
  // the options at the same levels rather than adding a new slot — so look
  // up the receiving row's selected archetype(s) first and fall back to the
  // base class's own `bonusFeatOptionsByLevel` only if none of them has an
  // override at this level (see `ClassDef.archetypeBonusFeatOptionsByLevel`
  // on the backend for why the replaced levels themselves never change).
  const receivingArchetypes = receivingArchetypeNames(progression, draft.target);
  const archetypeBonusOptions = receiving
    ? receivingArchetypes
        .map((name) => receivingClass?.archetypeBonusFeatOptionsByLevel[name]?.[receiving.level])
        .find((options) => options !== undefined)
    : undefined;
  const bonusOptions = archetypeBonusOptions ?? (receiving ? receivingClass?.bonusFeatOptionsByLevel[receiving.level] : undefined);

  useEffect(() => {
    if (!baseFeatPickable) setDraft((prev) => (prev.newFeat === null ? prev : { ...prev, newFeat: null }));
  }, [baseFeatPickable, setDraft]);

  useEffect(() => {
    if (!bonusGranted) setDraft((prev) => (prev.newBonusFeat === null ? prev : { ...prev, newBonusFeat: null }));
  }, [bonusGranted, setDraft]);

  if (!granted && !bonusGranted) {
    return <div className="warning-note">Auf dieser Stufe gibt es kein neues Talent (nur auf Stufe 1 und ungeraden Stufen).</div>;
  }

  const featByName = new Map(options.feats.map((f) => [f.name, f]));
  // Closed-list bonus feats (e.g. Mönch's Bonustalent) may be entirely
  // absent from `options.feats` — that list is prereq-filtered, and a
  // closed list waives normal prerequisites for its own named feats (see
  // `bonusFeatOptionsByLevel`'s own doc comment) — so it carries its own
  // FeatDef data and must be merged in here too for `needingSubChoice` to
  // resolve them.
  for (const feat of bonusOptions?.feats ?? []) featByName.set(feat.name, feat);
  const notYetTaken = options.feats.filter((f) => !progression.feats.includes(f.name));
  const available = notYetTaken.map((f) => f.name);
  const bonusTypeAvailable = notYetTaken
    .filter((f) => bonusOptions?.types.includes(f.type))
    .map((f) => f.name);
  const bonusClosedListAvailable = (bonusOptions?.feats ?? [])
    .filter((f) => !progression.feats.includes(f.name))
    .map((f) => f.name);
  const bonusAvailable = [...new Set([...bonusTypeAvailable, ...bonusClosedListAvailable])];
  const weapons = options.items.filter((i) => i.category === 'weapon');

  function select(name: string) {
    setDraft((prev) => {
      if (prev.newFeat === name) {
        const nextSubChoices = { ...prev.featSubChoices };
        const nextSubChoices2 = { ...prev.featSubChoices2 };
        delete nextSubChoices[name];
        delete nextSubChoices2[name];
        return { ...prev, newFeat: null, featSubChoices: nextSubChoices, featSubChoices2: nextSubChoices2 };
      }
      return { ...prev, newFeat: name };
    });
  }

  function selectBonus(name: string) {
    setDraft((prev) => {
      if (prev.newBonusFeat === name) {
        const nextSubChoices = { ...prev.featSubChoices };
        const nextSubChoices2 = { ...prev.featSubChoices2 };
        delete nextSubChoices[name];
        delete nextSubChoices2[name];
        return { ...prev, newBonusFeat: null, featSubChoices: nextSubChoices, featSubChoices2: nextSubChoices2 };
      }
      return { ...prev, newBonusFeat: name };
    });
  }

  function setSubChoice(name: string, value: string) {
    setDraft((prev) => ({ ...prev, featSubChoices: { ...prev.featSubChoices, [name]: value } }));
  }

  function setSubChoice2(name: string, value: string) {
    setDraft((prev) => ({ ...prev, featSubChoices2: { ...prev.featSubChoices2, [name]: value } }));
  }

  const needingSubChoice = [draft.newFeat, draft.newBonusFeat]
    .map((name) => (name ? featByName.get(name) : undefined))
    .filter((feat): feat is NonNullable<typeof feat> => feat !== undefined && feat.subChoiceType !== null);

  return (
    <>
      {granted && secondaryFeatureGranted && (
        <div className="info-note">
          Auf dieser Stufe ersetzt die Sekundärklasse ({progression.secondaryClass?.name}) das übliche Talent durch
          ein eigenes Feature. Der genaue Inhalt ist in der App noch nicht hinterlegt — bitte im Regelwerk
          nachschlagen.
        </div>
      )}
      {baseFeatPickable && (
        <SingleChipPicker items={available} selected={draft.newFeat} onSelect={select} searchPlaceholder="Talente durchsuchen …" />
      )}
      {bonusGranted && (
        <>
          <div className="og-heading" style={{ marginTop: granted ? 16 : 0 }}>
            Bonustalent ({receiving?.className}, Stufe {receiving?.level})
          </div>
          <SingleChipPicker
            items={bonusAvailable}
            selected={draft.newBonusFeat}
            onSelect={selectBonus}
            searchPlaceholder="Bonustalente durchsuchen …"
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
              {feat.subChoiceType === 'skill_pair' && (
                <>
                  {/* Kosmopolit: "wähle zwei intelligenz-, weisheits- oder
                      charismabasierte Fertigkeiten" — the mental-ability
                      filter below is this feat's own restriction, not a
                      general property of "skill_pair" (see rules/feats.py). */}
                  <select
                    value={draft.featSubChoices[feat.name] ?? ''}
                    onChange={(e) => setSubChoice(feat.name, e.target.value)}
                  >
                    <option value="">– Erste Fertigkeit wählen –</option>
                    {options.skills
                      .filter((s) => s.ability === 'IN' || s.ability === 'WE' || s.ability === 'CH')
                      .map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                  </select>
                  <select
                    value={draft.featSubChoices2[feat.name] ?? ''}
                    onChange={(e) => setSubChoice2(feat.name, e.target.value)}
                    style={{ marginTop: 6 }}
                  >
                    <option value="">– Zweite Fertigkeit wählen –</option>
                    {options.skills
                      .filter(
                        (s) =>
                          (s.ability === 'IN' || s.ability === 'WE' || s.ability === 'CH') &&
                          s.id !== draft.featSubChoices[feat.name],
                      )
                      .map((s) => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                  </select>
                </>
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
              {feat.subChoiceType === 'manifestation' && (
                <select
                  value={draft.featSubChoices[feat.name] ?? ''}
                  onChange={(e) => setSubChoice(feat.name, e.target.value)}
                >
                  <option value="">– Manifestation wählen –</option>
                  {(feat.manifestationOptions ?? []).map((option) => (
                    <option key={option} value={option}>{option}</option>
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
