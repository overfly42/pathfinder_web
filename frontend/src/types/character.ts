export interface AbilityScore {
  key: string;
  label: string;
  score: number;
  mod: string;
  /** Ability damage/drain/burn already subtracted from `score` — shown as an annotation so the
   *  penalty stays visible even though nothing removes it when its source effect is cured (see
   *  roadmap.md §5's open item; always 0 today, no handler writes to it yet). */
  damage: number;
  /** What moved `score` away from its race/gear/ability-damage baseline — a feat/trait/active-
   *  effect bonus or penalty (e.g. Erschöpft's -2 ST/GE). Absent when nothing did; the baseline
   *  itself isn't itemized further (race/flex/gear/damage collapse into one "Basis" line), same
   *  "only what's worth showing" scope `SkillEntry.breakdown` already keeps. */
  breakdown?: BreakdownEntry[];
}

export interface StatEntry {
  key: string;
  label: string;
  value: string;
}

/** One line item in a value-origin breakdown (e.g. "Klassenfertigkeit: +3") —
 * `label`s sum to the stat's own displayed total. */
export interface BreakdownEntry {
  label: string;
  value: number;
}

export interface SkillEntry {
  key: string;
  label: string;
  value: string;
  /** Situational note that doesn't apply to `value` itself (e.g. Akrobatik's
   * jump-only speed bonus) — shown as an info affordance, not folded into
   * the displayed skill total. */
  note?: string;
  /** What `value` is made of (ranks, ability mod, class skill bonus, every
   * contributing feat/race/... bonus) — absent when there's nothing to show
   * (e.g. an untrained skill with a 0 total). Deliberately excludes `note`'s
   * situational bonus, which was never folded into `value` in the first
   * place. */
  breakdown?: BreakdownEntry[];
}

export interface DescribedEntry {
  key: string;
  name: string;
  description: string;
  /** Whether the backend's `HANDLERS` registry actually computes this
   *  entry's mechanical effect, vs. it only ever being name/description
   *  text with no effect applied anywhere on the sheet. */
  hasHandler: boolean;
}

/** One race-scoped favored-class-bonus choice the character has picked at
 *  least once, with its accumulated pick count and (if the bonus is a
 *  single accumulating number) the current whole-number value derived from
 *  it — `null` when a pick doesn't reduce to one number (e.g. a choice that
 *  grants two different effects per pick, or adds a known spell instead of
 *  a numeric bonus); read the full `description` instead in that case. */
export interface FavoredClassBonusEntry extends DescribedEntry {
  pickCount: number;
  currentBonus: number | null;
}

export interface SpellRef {
  key: string;
  name: string;
}

/** One spell's real prepared/cast state for the day (roadmap slice 6) —
 *  `preparedCount` copies prepared, `usedCount` of those already cast; the
 *  remaining castable copies are always `preparedCount - usedCount`. Shared
 *  shape between `CastableSpellGrade` (cast bar) and `PreparableSpellGrade`
 *  (spellbook prepare UI) — the same underlying `CharacterSpellPreparation`
 *  row, just filtered/rendered differently per tab. */
export type PreparedSpellRef = SpellRef & {
  baseClassId: string;
  preparedCount: number;
  usedCount: number;
  /** Spell's full description text, for the cast-confirmation popup (`CastSpellModal`). */
  description: string;
  /** Pre-formatted "V, S, M (...)" display string (`sheet.py`'s `_format_spell_components`) —
   *  "—" when no `BaseSpellComponent` row exists for this spell/tradition yet. */
  components: string;
};

export interface CastableSpellGrade {
  grade: number;
  locked: boolean;
  availableAtLevel?: number;
  /** Total slots/day at this grade (class table + ability-modifier bonus) — absent for a
   *  locked grade. */
  perDay?: number;
  spells: PreparedSpellRef[];
}

export interface PreparableSpellGrade {
  grade: number;
  locked: boolean;
  availableAtLevel?: number;
  perDay?: number;
  spells: PreparedSpellRef[];
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
  /** Confirms an own-state-activated bonus is already folded into `attackBonus`/`damage` above
   *  (e.g. "Heftiger Angriff aktiv") — present only while the player has actually activated it
   *  (backend `POST .../effects`, `source_type: "feat"`), absent otherwise. */
  note?: string;
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
  sourceType?: 'spell' | 'class_ability' | 'feat' | 'gear';
  sourceId?: string;
  /** Only meaningful when `sourceType` is `'gear'` — which endpoint a click should call. */
  gearActionKind?: 'use' | 'toggle';
  /** Only meaningful when `sourceType` is `'gear'` — the item's current `CharacterGear.is_active`.
   *  Purely a display flag on this card (a toggle never creates a `CharacterEffect` row, so it
   *  never shows up in "Aktive Effekte" — this is the only place its on/off state is visible). */
  isActive?: boolean;
  /** Only meaningful when `sourceType` is `'feat'` — pre-fills the activation modal's duration
   *  field from `BaseFeat.default_duration_rounds` (e.g. Heftiger Angriff's 1 round), same role
   *  `ConditionCatalogEntry.defaultDurationRounds` plays for conditions; the player can still
   *  override it. */
  defaultDurationRounds?: number | null;
  /** Present for a discrete once-a-day action with no duration to track as an active effect: a
   *  `sourceType: 'class_ability'` entry with no `gearActionKind` (e.g. Erneuerte Lebenskraft) —
   *  a click opens `UseAbilityModal` and confirming calls `PATCH .../class-abilities/{id}/use`
   *  instead of the duration-form `ActivateEffectModal` other class-ability cards use. Reset to
   *  `usesPerDay` by the same "+1 Tag"/rest calls that clear every other `DAILY_LIMITS` pool. The
   *  card is disabled once this reaches 0. */
  usesRemainingToday?: number | null;
  usesPerDay?: number | null;
  /** Present for a `sourceType: 'class_ability'` entry whose ability is both `is_persistent_effect`
   *  (needs the full `ActivateEffectModal` for duration/target-item, e.g. Kampfrausch, Kampfmagus's
   *  Arkaner Vorrat) *and* daily-pool-limited — deliberately a different pair from
   *  `usesRemainingToday`/`usesPerDay` above, which also switches `handleActionClick` to the
   *  simple "/use" endpoint; this pair is display-only; routing stays on `usesRemainingToday`.
   *  Same numbers as this ability's `ActiveEffect.dailyLimitRemaining`/`dailyLimitTotal`. */
  dailyLimitRemaining?: number | null;
  dailyLimitTotal?: number | null;
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

export type EffectSourceType = 'spell' | 'class_ability' | 'condition' | 'feat';
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
  /** See `todos.md`'s "Effekt-Handler-Inventar" — most conditions still only
   *  have a classification decision pending, no `EFFECT_HANDLERS[id]` entry
   *  yet. */
  hasHandler: boolean;
}

/** A persistent-effect spell, class ability, or feat this character actually knows/has, minimal
 *  shape since the picker just needs something to activate by id. `description`, when set, is only
 *  ever a daily-limited ability's remaining-today count (e.g. Kampfrausch's rounds/day) — most
 *  entries have none. `defaultDurationRounds` (feats, e.g. Heftiger Angriff's 1 round; class
 *  abilities, e.g. Kampfmagus's Arkaner Vorrat's 1 minute) pre-fills the activation modal's
 *  duration field, same role `ConditionCatalogEntry`'s own default plays for conditions — the
 *  player can still override it. */
export interface ActivatableRef {
  key: string;
  name: string;
  description?: string | null;
  defaultDurationRounds?: number | null;
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
  /** `false` for an effect derived from equipped gear (e.g. an item that permanently grants a
   *  spell's effect while worn) — there is no underlying row to delete, it goes away on its own
   *  when the item is unequipped, so the seal hides its remove button for these. */
  removable: boolean;
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
  /** What `armorClass` is made of (base 10, Dex mod, every equipped/granted
   * AC bonus) — absent for the two hardcoded mock fixtures, which predate
   * this field. */
  armorClassBreakdown?: BreakdownEntry[];
  /** RK while denied the Dexterity bonus to AC ("auf dem falschen Fuß") —
   * `armorClass` minus the Dex mod and any dodge-type bonus (both are lost
   * in that case per PF1e RAW). */
  armorClassFlatFooted: number;
  armorClassFlatFootedBreakdown?: BreakdownEntry[];
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
  /** Values currently legal for a favored-class-bonus level-up pick
   *  (`"hp"`/`"skill"` plus this character's race+class-specific
   *  alternates) — empty without a favored class. Absent for the two
   *  hardcoded mock fixtures, which predate this field. */
  favoredClassBonusOptions?: string[];
  /** Accumulated favored-class-bonus picks across the character's whole
   *  career (any favored class, not just the current one) — "hp"/"skill"
   *  picks never appear here, see `FavoredClassBonusEntry`'s docstring.
   *  Absent for the two hardcoded mock fixtures. */
  favoredClassBonuses?: FavoredClassBonusEntry[];
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
  /** Known feats flagged `is_persistent_effect` (backend `BaseFeat`, 2026-08-16, e.g. Heftiger
   *  Angriff) — the feat counterpart to `activatableSpells`/`activatableClassAbilities`. */
  activatableFeats: ActivatableRef[];
  /** Persistent-effect class abilities with `activation_scope` `'external'`/`'both'` (backend
   *  `BaseClassAbility`) — effects this character can receive from someone else's ability (e.g. a
   *  Barde's Lied des Mutes) even if they don't have it granted themselves. Not gated by ownership,
   *  same as `conditionsCatalog`. */
  externalClassAbilities: ActivatableRef[];
}
