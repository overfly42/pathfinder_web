import { ABILITY_KEYS, type AbilityKey } from '../types/abilities';
import type { CreationDraft, DraftGearItem } from '../types/creationDraft';
import type { ClassDef, CreationOptions, RaceOption } from '../types/creationOptions';

export function abilityMod(score: number): number {
  return Math.floor((score - 10) / 2);
}

export function formatMod(mod: number): string {
  return (mod >= 0 ? '+' : '') + mod;
}

export function selectedRace(draft: CreationDraft, options: CreationOptions): RaceOption | undefined {
  return options.races.find((r) => r.id === draft.raceId);
}

export function raceMod(draft: CreationDraft, options: CreationOptions, key: AbilityKey): number {
  const race = selectedRace(draft, options);
  if (!race) return 0;
  let mod = race.mods[key] ?? 0;
  if (race.flex && draft.flexAbility === key) mod += 2;
  return mod;
}

export function totalAbility(draft: CreationDraft, options: CreationOptions, key: AbilityKey): number {
  return draft.abilityScores[key] + raceMod(draft, options, key);
}

export function spentPoints(draft: CreationDraft, options: CreationOptions): number {
  return ABILITY_KEYS.reduce((sum, key) => sum + (options.pointBuyCosts[draft.abilityScores[key]] ?? 0), 0);
}

export function totalLevel(draft: CreationDraft): number {
  return draft.classRows.reduce((sum, row) => sum + (row.level || 0), 0);
}

/** Base progression (1st level, then every odd level after) plus any bonus feat
 *  slots granted by race (Human's "Bonustalent") or class (e.g. Krieger's bonus
 *  combat feats, via each class's `bonusFeatLevels` — not a hardcoded class name,
 *  since Fighter isn't the only source of bonus feats in the core rules and more
 *  can be added as pure data later). Mirrors the backend's
 *  `_feat_max`/`rules/feat_slots.py`; keep both in sync. Human can trade
 *  "Bonustalent" away via the "Bemerkenswerte Fertigkeit" alternate trait, tracked
 *  the same way as any other replaced trait. */
export function featMax(draft: CreationDraft, options: CreationOptions): number {
  const base = Math.ceil(totalLevel(draft) / 2);

  const race = selectedRace(draft, options);
  const replaced = replacedTraitNames(draft, options);
  const raceBonus = race?.traits.some((t) => t.name === 'Bonustalent') && !replaced.has('Bonustalent') ? 1 : 0;

  const levelByClassName = new Map<string, number>();
  for (const row of draft.classRows) {
    levelByClassName.set(row.className, (levelByClassName.get(row.className) ?? 0) + (row.level || 0));
  }
  let classBonus = 0;
  for (const [className, level] of levelByClassName) {
    const bonusFeatLevels = classDef(options, className)?.bonusFeatLevels ?? [];
    classBonus += bonusFeatLevels.filter((grantLevel) => grantLevel <= level).length;
  }

  return base + raceBonus + classBonus;
}

export function classDef(options: CreationOptions, className: string) {
  return options.classes.find((c) => c.name === className);
}

/** Total level taken in one specific class across every `classRows` entry
 *  with that name (a class picked non-contiguously across multiple rows
 *  still has one combined level for spell-budget purposes). */
export function classTotalLevel(draft: CreationDraft, className: string): number {
  return draft.classRows.filter((r) => r.className === className).reduce((sum, r) => sum + (r.level || 0), 0);
}

/** Non-grade-0 spellbook picks available to an arcane-prepared (Wizard-style)
 *  caster: `2 + ability_mod` from reaching 1st level, +2 more per level
 *  after. Grade-0 spells are handled separately (all of them, always) — see
 *  `spellIdsForSubmission`. Mirrors the backend's
 *  `rules/spells.py::arcane_prepared_budget` — keep both in sync. */
export function arcanePreparedBudget(level: number, abilityModValue: number): number {
  if (level < 1) return 0;
  return (2 + abilityModValue) + 2 * (level - 1);
}

/** Which spell grades are castable at all at this class level, and (for
 *  spontaneous casters) the known-spell cap per grade — straight from
 *  `ClassDef.spellsKnownByLevel`, itself sourced from `BaseClassSpellsKnown`.
 *  `null` counts (arcane-prepared classes) mean "accessible, uncapped". */
export function spellGradeBudgetAtLevel(cls: ClassDef, level: number): Record<string, number | null> {
  return cls.spellsKnownByLevel[String(level)] ?? {};
}

/** Every id a spontaneous/arcane-prepared class-row's picks should be
 *  submitted as: for arcane-prepared classes this unions in every grade-0
 *  spell (mandatory, not itself a player pick — see `SpellsStep.tsx`) with
 *  whatever the player chose; for spontaneous classes it's just the picks.
 *  Divine-prepared/none classes never appear here (no known-spell list to
 *  submit). Keyed by `base_class_id`, matching `CharacterCreate.spell_ids`. */
export function spellIdsForSubmission(draft: CreationDraft, options: CreationOptions): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const className of spellcastingClasses(draft, options)) {
    const cls = classDef(options, className);
    if (!cls?.id) continue;
    const picked = draft.spellSelections[cls.id] ?? [];
    if (cls.spellType === 'arcane-prepared') {
      const mandatory = (options.spellsByClass[className] ?? []).filter((s) => s.grade === 0).map((s) => s.id);
      result[cls.id] = Array.from(new Set([...mandatory, ...picked]));
    } else {
      result[cls.id] = picked;
    }
  }
  return result;
}

export function classSkillSet(draft: CreationDraft, options: CreationOptions): Set<string> {
  const set = new Set<string>();
  for (const row of draft.classRows) {
    const cls = classDef(options, row.className);
    cls?.classSkills.forEach((key) => set.add(key));
  }
  return set;
}

/** Mirrors the backend's `_skill_points_total`/`rules/skill_points.py`; keep both in sync.
 *  Human's "Geschult" (Skilled) racial trait grants +1 skill rank per *character* level, not
 *  per class — same trade-away-via-alternate-trait handling as `featMax`'s "Bonustalent". */
export function skillPointsTotal(draft: CreationDraft, options: CreationOptions): number {
  const intMod = abilityMod(totalAbility(draft, options, 'IN'));

  const race = selectedRace(draft, options);
  const replaced = replacedTraitNames(draft, options);
  const raceBonusPerLevel = race?.traits.some((t) => t.name === 'Geschult') && !replaced.has('Geschult') ? 1 : 0;

  return draft.classRows.reduce((sum, row) => {
    const cls = classDef(options, row.className);
    const base = cls?.skillPointsBase ?? 2;
    const level = row.level || 0;
    return sum + Math.max(1, base + intMod) * level + raceBonusPerLevel * level;
  }, 0);
}

export function skillPointsSpent(draft: CreationDraft): number {
  return Object.values(draft.skillRanks).reduce((sum, ranks) => sum + (ranks || 0), 0);
}

export function skillBonus(draft: CreationDraft, options: CreationOptions, skillKey: string, ability: AbilityKey): number {
  const ranks = draft.skillRanks[skillKey] || 0;
  const abMod = abilityMod(totalAbility(draft, options, ability));
  const isClassSkill = classSkillSet(draft, options).has(skillKey);
  return ranks + abMod + (isClassSkill && ranks > 0 ? 3 : 0);
}

/** Spellcasting class rows with a fixed, learnable spell list (arcane-prepared / spontaneous), deduped by class name. */
export function spellcastingClasses(draft: CreationDraft, options: CreationOptions): string[] {
  const result: string[] = [];
  for (const row of draft.classRows) {
    const cls = classDef(options, row.className);
    const type = cls?.spellType ?? 'none';
    if ((type === 'arcane-prepared' || type === 'spontaneous') && !result.includes(row.className)) {
      result.push(row.className);
    }
  }
  return result;
}

/** Alt-trait names of the selected race that are currently chosen and therefore replace a base trait. */
export function replacedTraitNames(draft: CreationDraft, options: CreationOptions): Set<string> {
  const race = selectedRace(draft, options);
  const names = new Set<string>();
  if (!race) return names;
  for (const altName of draft.altTraits) {
    const alt = race.alt.find((a) => a.name === altName);
    alt?.replaces.forEach((t) => names.add(t));
  }
  return names;
}

export function formatPrice(gm: number): string {
  const rounded = Math.round(gm * 100) / 100;
  if (rounded >= 1 || rounded === 0) return `${rounded} GM`;
  const sm = Math.round(rounded * 10 * 100) / 100;
  if (sm >= 1) return `${sm} SM`;
  const km = Math.round(rounded * 100 * 100) / 100;
  return `${km} KM`;
}

export function gearTotalValue(gear: DraftGearItem[]): number {
  return gear.reduce((sum, item) => sum + (item.price || 0) * item.qty, 0);
}

export function genderLabel(value: CreationDraft['gender']): string {
  if (value === 'maennlich') return 'Männlich';
  if (value === 'weiblich') return 'Weiblich';
  return 'Keine Angabe';
}
