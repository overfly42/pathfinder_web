import { createId } from './id';
import type { CreationDraft } from '../types/creationDraft';

export function createInitialDraft(): CreationDraft {
  return {
    name: '',
    gender: '',
    raceId: null,
    flexAbility: null,
    altTraits: [],
    classRows: [
      { id: createId(), className: 'Waldläufer', level: 1, archetypes: [], options: {} },
    ],
    favoredClassBonus: null,
    abilityScores: { ST: 10, GE: 10, KO: 10, IN: 10, WE: 10, CH: 10 },
    pointBudget: 20,
    useBackgroundSkills: false,
    skillRanks: {},
    feats: [],
    featSubChoices: {},
    traits: [],
    spellSelections: {},
    gold: 0,
    gear: [],
  };
}
