import type { AbilityKey } from '../types/abilities';
import type { CharacterProgression } from '../types/characterProgression';
import type { LevelUpTarget } from '../types/levelUpDraft';
import type { ClassDef } from '../types/creationOptions';

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

/** Krieger (Fighter) gets an additional bonus combat feat on every even level, on top of the
 *  normal odd-level feat progression shared by all classes. */
export function fighterBonusFeatGrantedThisLevel(receivingClassName: string | null, newLevel: number): boolean {
  return receivingClassName === 'Krieger' && newLevel % 2 === 0;
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
