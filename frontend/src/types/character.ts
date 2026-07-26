export interface AbilityScore {
  key: string;
  label: string;
  score: number;
  mod: string;
}

export interface StatEntry {
  key: string;
  label: string;
  value: string;
}

export interface SkillEntry {
  key: string;
  label: string;
  value: string;
}

export interface DescribedEntry {
  key: string;
  name: string;
  description: string;
}

export interface SpellRef {
  key: string;
  name: string;
}

export interface CastableSpellGrade {
  grade: number;
  locked: boolean;
  availableAtLevel?: number;
  prepared?: number;
  spells: (SpellRef & { used: boolean })[];
}

export interface PreparableSpellGrade {
  grade: number;
  locked: boolean;
  availableAtLevel?: number;
  perDay?: number;
  maxPrepared?: number;
  spells: (SpellRef & { prepared: boolean })[];
}

export interface GearItem {
  id: string;
  name: string;
  qty: number;
}

export interface EquipmentSlotOption {
  value: string;
  label: string;
}

export interface EquipmentSlot {
  key: string;
  label: string;
  side: 'left' | 'right';
  row: number;
  options: EquipmentSlotOption[];
  selected: string;
}

export type ActionTag = 'standard' | 'reaction' | 'move' | 'full';

export interface ActionOption {
  id: string;
  icon: string;
  name: string;
  tag: ActionTag;
  description: string;
}

export type EffectVariant = 'buff' | 'debuff' | 'neutral';

export interface Effect {
  id: string;
  icon: string;
  amount: string;
  name: string;
  detail: string;
  variant: EffectVariant;
  active: boolean;
  /** Rounds remaining, or null for "until rest" / "while active" effects that only clear on rest/day-advance. */
  durationRounds: number | null;
  durationLabel: string;
}

export interface Character {
  id: string;
  name: string;
  race: string;
  className: string;
  archetype: string;
  level: number;
  hp: { current: number; max: number };
  armorClass: number;
  initiative: string;
  speed: string;
  roundLabel: string;
  abilities: AbilityScore[];
  saves: StatEntry[];
  combat: StatEntry[];
  skills: SkillEntry[];
  feats: DescribedEntry[];
  traits: DescribedEntry[];
  classFeatures: DescribedEntry[];
  raceAbilities: DescribedEntry[];
  spellsKnown: CastableSpellGrade[];
  gear: GearItem[];
  equipmentSlots: EquipmentSlot[];
  spellbook: PreparableSpellGrade[];
  actions: ActionOption[];
  effectsActive: Effect[];
  effectsAvailable: Effect[];
}
