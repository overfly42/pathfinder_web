import { ABILITY_KEYS, type AbilityKey } from '../types/abilities';
import type { CreationDraft, DraftGearItem } from '../types/creationDraft';
import type { CreationOptions, RaceOption } from '../types/creationOptions';

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

export function featMax(level: number): number {
  return 1 + Math.floor(level / 2);
}

export function spellPickMax(level: number): number {
  return 2 + Math.floor(level / 4);
}

export function classDef(options: CreationOptions, className: string) {
  return options.classes.find((c) => c.name === className);
}

export function classSkillSet(draft: CreationDraft, options: CreationOptions): Set<string> {
  const set = new Set<string>();
  for (const row of draft.classRows) {
    const cls = classDef(options, row.className);
    cls?.classSkills.forEach((key) => set.add(key));
  }
  return set;
}

export function skillPointsTotal(draft: CreationDraft, options: CreationOptions): number {
  const intMod = abilityMod(totalAbility(draft, options, 'int'));
  return draft.classRows.reduce((sum, row) => {
    const cls = classDef(options, row.className);
    const base = cls?.skillPointsBase ?? 2;
    return sum + Math.max(1, base + intMod) * (row.level || 0);
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

export function priceForItemName(options: CreationOptions, name: string): number | null {
  const found = options.items.find((i) => i.name === name);
  return found ? found.price : null;
}

export function genderLabel(value: CreationDraft['gender']): string {
  if (value === 'maennlich') return 'Männlich';
  if (value === 'weiblich') return 'Weiblich';
  return 'Keine Angabe';
}
