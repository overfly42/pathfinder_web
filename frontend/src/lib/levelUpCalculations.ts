import type { AbilityKey } from '../types/abilities';
import type { CharacterProgression } from '../types/characterProgression';
import type { LevelUpTarget } from '../types/levelUpDraft';
import type { ClassDef, RaceOption } from '../types/creationOptions';

export function getOldTotalLevel(progression: CharacterProgression): number {
  return progression.classes.reduce((sum, c) => sum + c.level, 0);
}

export function getNewLevel(progression: CharacterProgression): number {
  return getOldTotalLevel(progression) + 1;
}

export function getReceivingClassName(progression: CharacterProgression, target: LevelUpTarget): string | null {
  if (target.mode === 'existing') {
    return progression.classes.find((c) => c.id === target.classId)?.className ?? null;
  }
  return target.className;
}

export function getReceivingClassAndLevel(
  progression: CharacterProgression,
  target: LevelUpTarget,
): { className: string; level: number } | null {
  if (target.mode === 'existing') {
    const c = progression.classes.find((x) => x.id === target.classId);
    return c ? { className: c.className, level: c.level + 1 } : null;
  }
  return target.className ? { className: target.className, level: 1 } : null;
}

export function effectiveClassNames(progression: CharacterProgression, target: LevelUpTarget): string[] {
  const names = progression.classes.map((c) => c.className);
  if (target.mode === 'new' && target.className) names.push(target.className);
  return names;
}

export function effectiveAbilityTotal(
  progression: CharacterProgression,
  key: AbilityKey,
  abilityIncrease: AbilityKey | null,
): number {
  const base = progression.abilityScores[key];
  return abilityIncrease === key ? base + 1 : base;
}

export function abilityIncreaseGrantedThisLevel(newLevel: number): boolean {
  return newLevel % 4 === 0;
}

export function featGrantedThisLevel(newLevel: number): boolean {
  return newLevel % 2 === 1;
}

/** Whether the receiving class grants a bonus feat slot at its own new level (e.g.
 *  Kämpfer's 1st and every even level) — driven by each class's real `bonusFeatLevels`
 *  data (see `ClassDef.bonusFeatLevels`), not a hardcoded class name, since other
 *  classes can grant bonus feats too. Keyed by the class's own level (`classLevel`),
 *  not the character's total level, so multiclassing resolves correctly. Mirrors the
 *  backend's `_feat_max`/`rules/feat_slots.py`; keep both in sync. */
export function classBonusFeatGrantedThisLevel(
  receivingClassName: string | null,
  classLevel: number | null,
  classes: ClassDef[],
): boolean {
  if (receivingClassName === null || classLevel === null) return false;
  const cls = classes.find((c) => c.name === receivingClassName);
  return cls?.bonusFeatLevels.includes(classLevel) ?? false;
}

export function classSkillSetForLevelUp(
  progression: CharacterProgression,
  target: LevelUpTarget,
  classes: ClassDef[],
): Set<string> {
  const set = new Set<string>();
  for (const className of effectiveClassNames(progression, target)) {
    const cls = classes.find((c) => c.name === className);
    cls?.classSkills.forEach((key) => set.add(key));
  }
  return set;
}

export function skillPointsForThisLevel(
  receivingClassName: string | null,
  classes: ClassDef[],
  effectiveIntMod: number,
): number {
  const cls = receivingClassName ? classes.find((c) => c.name === receivingClassName) : undefined;
  const base = cls?.skillPointsBase ?? 2;
  return Math.max(1, base + effectiveIntMod);
}

/** Whether this character's race grants a flat +1 skill rank per character
 *  level (Human's "Geschult"), accounting for it having been traded away
 *  via an alternate trait — mirrors creation's `skillPointsTotal`
 *  (`creationCalculations.ts`); keep both in sync. Mirrors the backend's
 *  `rules/skill_points.py::race_grants_bonus_skill_point_per_level`. */
export function raceGrantsSkillBonusPerLevel(progression: CharacterProgression, races: RaceOption[]): boolean {
  const race = races.find((r) => r.name === progression.race);
  if (!race) return false;
  const replaced = new Set<string>();
  for (const altName of progression.altTraits) {
    const alt = race.alt.find((a) => a.name === altName);
    alt?.replaces.forEach((t) => replaced.add(t));
  }
  return race.traits.some((t) => t.name === 'Geschult') && !replaced.has('Geschult');
}
