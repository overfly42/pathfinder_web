import { createId } from './id';
import type { CharacterProgression } from '../types/characterProgression';
import type { LevelUpDraft } from '../types/levelUpDraft';
import {
  getNewLevel,
  getOldTotalLevel,
  getReceivingClassAndLevel,
} from './levelUpCalculations';

/** Applies a completed level-up wizard draft to a progression, producing the next progression
 *  plus a human-readable history line. Kept in the frontend only as session-local bookkeeping —
 *  once the backend owns character progression this becomes a `POST .../level-up` call instead. */
export function applyLevelUp(progression: CharacterProgression, draft: LevelUpDraft): CharacterProgression {
  const oldLevel = getOldTotalLevel(progression);
  const newLevel = getNewLevel(progression);
  const receiving = getReceivingClassAndLevel(progression, draft.target);
  const target = draft.target;

  let classes = progression.classes;
  if (target.mode === 'existing') {
    classes = progression.classes.map((c) => {
      if (c.id !== target.classId) return c;
      const classOptions: Record<string, string[]> = { ...c.options };
      for (const [key, values] of Object.entries(draft.existingLevelOptionSelections)) {
        if (!values.length) continue;
        const existing = classOptions[key] ?? [];
        classOptions[key] = [...existing, ...values.filter((v) => !existing.includes(v))];
      }
      return { ...c, level: c.level + 1, options: classOptions };
    });
  } else if (target.className) {
    classes = [
      ...progression.classes,
      { id: createId(), className: target.className, level: 1, archetypes: target.archetypes, options: target.options },
    ];
  }

  const abilityScores = draft.abilityIncrease
    ? { ...progression.abilityScores, [draft.abilityIncrease]: progression.abilityScores[draft.abilityIncrease] + 1 }
    : progression.abilityScores;

  const feats = [...progression.feats];
  if (draft.newFeat && !feats.includes(draft.newFeat)) feats.push(draft.newFeat);
  if (draft.newBonusFeat && !feats.includes(draft.newBonusFeat)) feats.push(draft.newBonusFeat);

  const skillRanks = { ...progression.skillRanks };
  for (const [key, granted] of Object.entries(draft.skillIncreases)) {
    if (granted) skillRanks[key] = (skillRanks[key] ?? 0) + 1;
  }

  let spellsKnown = progression.spellsKnown;
  if (draft.newSpell && receiving) {
    const existing = spellsKnown[receiving.className] ?? [];
    spellsKnown = { ...spellsKnown, [receiving.className]: [...existing, draft.newSpell] };
  }

  const descriptionParts = [`${receiving?.className ?? 'Klasse'} Stufe ${receiving?.level ?? newLevel}`];
  if (draft.newFeat) descriptionParts.push(`Talent: ${draft.newFeat}`);
  if (draft.newBonusFeat) descriptionParts.push(`Bonustalent: ${draft.newBonusFeat}`);
  if (draft.abilityIncrease) descriptionParts.push(`Attribut +1: ${draft.abilityIncrease.toUpperCase()}`);
  if (draft.newSpell) descriptionParts.push(`Neuer Zauber: ${draft.newSpell}`);

  const historyEntry = {
    id: createId(),
    date: new Date().toISOString().slice(0, 10),
    description: `Stufe ${oldLevel} → ${newLevel}: ${descriptionParts.join(' · ')}`,
  };

  return {
    ...progression,
    classes,
    abilityScores,
    feats,
    skillRanks,
    spellsKnown,
    history: [...progression.history, historyEntry],
  };
}
