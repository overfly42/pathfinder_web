export interface AbilityScore {
  key: string;
  label: string;
  score: number;
  mod: string;
  /** Ability damage/drain/burn already subtracted from `score` — shown as an annotation so the
   *  penalty stays visible even though nothing removes it when its source effect is cured (see
   *  roadmap.md §5's open item; always 0 today, no handler writes to it yet). */
  damage: number;
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
  /** Situational note that doesn't apply to `value` itself (e.g. Akrobatik's
   * jump-only speed bonus) — shown as an info affordance, not folded into
   * the displayed skill total. */
  note?: string;
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

/** Only set for the small set of flat on-hit energy abilities (Aufflammen/Blitz/Eis/Säure and their
 *  crit-only siblings) — `rules/weapon_abilities.py`'s one exception to "no computed effect".
 *  `requiresActive` is always true today (they're all command-word-toggled), kept explicit rather
 *  than assumed in case a future non-toggled flat-damage ability is added. */
export interface GearSpecialAbilityBonusDamage {
  dice: string;
  type: string;
  requiresActive: boolean;
}

export interface GearSpecialAbility {
  name: string;
  description: string | null;
  bonusDamage?: GearSpecialAbilityBonusDamage | null;
}

/** Computed attack-bonus/damage-dice readout for one equipped weapon slot (backend `sheet.py`'s
 *  `_build_weapon_attacks`) — a static display number, not a dice roll (this app never rolls for
 *  the player, see `rules/weapon_abilities.py`'s module docstring). */
export interface WeaponAttack {
  key: string;
  hand: string;
  name: string;
  attackBonus: string;
  damage: string;
}

export interface GearItem {
  id: string;
  name: string;
  qty: number;
  /** Weapon/armor enhancement bonus, e.g. "+1". Only meaningful for magic gear. */
  enhancement?: string;
  /** Freetext properties not (yet) in the BaseWeaponSpecialAbility catalog. */
  properties?: string[];
  /** Named catalog abilities (e.g. "Flammend") resolved from BaseWeaponSpecialAbility. */
  specialAbilities?: GearSpecialAbility[];
  /** "permanent" | "activatable" — only set for wondrous/ring/wand items. */
  activation?: string;
  /** Wand-style depleting charge counter; never resets. Present only when the item has BaseItem.maxCharges. */
  chargesRemaining?: number | null;
  maxCharges?: number;
  /** "N-mal pro Tag" counter; reset by POST .../rest. Present only when the item has BaseItem.usesPerDay. */
  usesRemainingToday?: number | null;
  usesPerDay?: number;
  /** On/off state for unlimited-use "activatable" items whose effect is toggled, not consumed. */
  isActive?: boolean;
  /** Spell stored in a wand instance (PATCH .../gear/{item_id} with stored_spell_id). */
  storedSpell?: string;
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
  /** `null` when no real action-cost data exists for this entry's source (backend `sheet.py`'s
   *  `_build_actions`, roadmap slice 6 thin cut) — no field for it exists anywhere in the schema yet,
   *  so this stays unset rather than guessed. */
  tag: ActionTag | null;
  description: string;
  /** Absent on the older mock fixture characters' hardcoded action cards (never meant to be
   *  interactive) — present for every real, DB-backed entry. */
  sourceType?: 'spell' | 'class_ability' | 'gear';
  sourceId?: string;
  /** Only meaningful when `sourceType` is `'gear'` — which endpoint a click should call. */
  gearActionKind?: 'use' | 'toggle';
  /** Only meaningful when `sourceType` is `'gear'` — the item's current `CharacterGear.is_active`.
   *  Purely a display flag on this card (a toggle never creates a `CharacterEffect` row, so it
   *  never shows up in "Aktive Effekte" — this is the only place its on/off state is visible). */
  isActive?: boolean;
}

export type EffectVariant = 'buff' | 'debuff' | 'neutral';

/** A condition/effect definition from the shared catalog (`/api/effects`) — the same for every
 *  character, same as a feat or trait definition. Not character state. */
export interface EffectDef {
  id: string;
  icon: string;
  amount: string;
  name: string;
  detail: string;
  /** Instructional label for the catalog entry, e.g. "Aktivieren" / "Wirken". */
  durationLabel: string;
}

/** An effect currently applied to a specific character — character state, part of the
 *  character resource just like feats or gear. */
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

/** Combined view the effects panel/search renders: this character's active effects plus the
 *  full catalog of effects not currently active on them. Assembled client-side, not fetched
 *  as one resource, since the two halves come from different endpoints with different scope. */
export interface EffectsView {
  effectsActive: Effect[];
  effectsAvailable: EffectDef[];
}

export type EffectSourceType = 'spell' | 'class_ability' | 'condition';
export type ConditionType = 'condition' | 'poison' | 'disease';

/** One row from the shared condition/poison/disease catalog (`/api/conditions`) — same for every
 *  character, same as a feat or trait definition. Not character state. Distinct from the older
 *  `EffectDef`/`/api/effects` mock catalog (icon/amount/variant), which predates this backend model. */
export interface ConditionCatalogEntry {
  id: string;
  name: string;
  description: string;
  type: ConditionType;
  /** Fixed-number defaults parsed out of `description` at seed time (rounds-normalized) —
   *  `null` where the source text was dice-based, unstated, or in an unsupported unit (e.g.
   *  weeks). Used to pre-fill the activation form; the player can still override them. */
  defaultIncubationRounds: number | null;
  defaultDurationRounds: number | null;
  defaultFrequencyRounds: number | null;
  defaultSuccessesRequired: number | null;
}

/** A persistent-effect spell or class ability this character actually knows/has, minimal shape
 *  since the picker just needs something to activate by id. `description`, when set, is only ever
 *  a daily-limited ability's remaining-today count (e.g. Kampfrausch's rounds/day) — most entries
 *  have none. */
export interface ActivatableRef {
  key: string;
  name: string;
  description?: string | null;
}

/** One applied `CharacterEffect` instance (backend roadmap slice 5) — real character state, distinct
 *  from the older mock `Effect`/`effectsActive` seal system. `null` fields are simply not tracked for
 *  this instance (e.g. a plain buff has no frequency/successes, a poison has no plain duration). */
export interface ActiveEffect {
  id: string;
  sourceType: EffectSourceType;
  sourceId: string;
  /** Only set when `sourceType` is `'condition'` — spells/class abilities have no equivalent
   *  subcategory. Used to pick the right icon without a second lookup into the catalog. */
  conditionType: ConditionType | null;
  name: string;
  level: number | null;
  incubationRemaining: number | null;
  durationRemaining: number | null;
  frequencyRounds: number | null;
  nextCheckIn: number | null;
  successesCurrent: number;
  successesRequired: number | null;
  /** Set only for an ability registered in the backend's `DAILY_LIMITS` (e.g. Kampfrausch) — its
   *  rounds/uses remaining today out of the computed daily total. `null` for everything else,
   *  including this same ability once its own pool is exhausted and it's no longer active. */
  dailyLimitRemaining: number | null;
  dailyLimitTotal: number | null;
}

export interface Character {
  id: string;
  name: string;
  race: string;
  className: string;
  archetype: string;
  level: number;
  hp: { current: number; max: number; temporary: number };
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
  weaponAttacks: WeaponAttack[];
  equipmentSlots: EquipmentSlot[];
  spellbook: PreparableSpellGrade[];
  actions: ActionOption[];
  effectsActive: Effect[];
  activeEffects: ActiveEffect[];
  activatableSpells: ActivatableRef[];
  activatableClassAbilities: ActivatableRef[];
  /** Persistent-effect class abilities with `activation_scope` `'external'`/`'both'` (backend
   *  `BaseClassAbility`) — effects this character can receive from someone else's ability (e.g. a
   *  Barde's Lied des Mutes) even if they don't have it granted themselves. Not gated by ownership,
   *  same as `conditionsCatalog`. */
  externalClassAbilities: ActivatableRef[];
}
