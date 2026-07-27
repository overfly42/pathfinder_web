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
    abilityScores: { sta: 10, ges: 10, kon: 10, int: 10, wei: 10, cha: 10 },
    pointBudget: 20,
    skillRanks: {},
    feats: [],
    traits: [],
    spellSelections: {},
    gold: 0,
    gear: [
      { id: createId(), name: 'Abenteurerausrüstung', qty: 1, price: 9 },
      { id: createId(), name: 'Reisekleidung', qty: 1, price: 1 },
    ],
  };
}
