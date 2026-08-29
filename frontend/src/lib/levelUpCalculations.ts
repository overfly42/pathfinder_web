import type { AbilityKey } from '../types/abilities';
import type { CharacterProgression } from '../types/characterProgression';
import type { LevelUpSkillSpecializationEntry, LevelUpTarget } from '../types/levelUpDraft';
import type { ClassDef, RaceOption, SkillDef } from '../types/creationOptions';

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

/** Archetype names already applied to the class this level-up targets — an
 *  existing class's own picks (`ClassProgressionEntry.archetypes`) for
 *  `mode: 'existing'`, or the ones just chosen for a brand-new class row
 *  (`target.archetypes`) for `mode: 'new'`. Mirrors creation's
 *  `archetypesForClass`, just against a `LevelUpTarget` instead of a
 *  `CreationDraft` class row. */
export function receivingArchetypeNames(progression: CharacterProgression, target: LevelUpTarget): string[] {
  if (target.mode === 'existing') {
    return progression.classes.find((c) => c.id === target.classId)?.archetypes ?? [];
  }
  return target.archetypes;
}

/** `progression.abilityScores` is already the character's full effective score
 *  (race/flex/equipped-gear/ability-damage, backend `sheet.py`'s
 *  `build_character_progression`) — a past level's own permanent increase is
 *  folded in too (persisted straight onto the base column at the time), so
 *  this only has to add *this* level-up's own still-pending pick on top. */
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

/** Full per-class {className, level} list after this level-up is applied —
 *  the receiving class's level +1 (or a new level-1 entry for a brand-new
 *  class), everything else unchanged. Mirrors the backend's
 *  `_apply_target_to_selections`. */
export function classesAfterLevelUp(
  progression: CharacterProgression,
  target: LevelUpTarget,
): { className: string; level: number }[] {
  if (target.mode === 'existing') {
    return progression.classes.map((c) =>
      c.id === target.classId
        ? { className: c.className, level: c.level + 1 }
        : { className: c.className, level: c.level },
    );
  }
  return [
    ...progression.classes.map((c) => ({ className: c.className, level: c.level })),
    ...(target.className ? [{ className: target.className, level: 1 }] : []),
  ];
}

/** Per class-taken, max(1, class's base skill points + INT modifier) times
 *  the levels taken in it, summed across all classes, plus a flat
 *  race-bonus rank per *character* level. Mirrors the backend's
 *  `_skill_points_total` / creation's `skillPointsTotal`
 *  (creationCalculations.ts). */
function classesSkillPointsTotal(
  classEntries: { className: string; level: number }[],
  classes: ClassDef[],
  intMod: number,
  raceBonusPerLevel: number,
): number {
  let total = 0;
  let totalLevel = 0;
  for (const entry of classEntries) {
    const base = classes.find((c) => c.name === entry.className)?.skillPointsBase ?? 2;
    total += Math.max(1, base + intMod) * entry.level;
    totalLevel += entry.level;
  }
  return total + raceBonusPerLevel * totalLevel;
}

/** New regular skill-point budget granted by this level-up. PF1e ability-score
 *  bonuses are retroactive (unlike 3.5e's skill-point exception —
 *  http://paizo.com/threads/rzs2kpru&page=1?Int-and-Skills#9, James Jacobs:
 *  "Skill ranks not being retroactive are a 3.5 convention we specifically
 *  removed from the game"): a permanent INT increase this level (`newIntMod`
 *  vs. `oldIntMod`, the mod just before it) also recomputes every
 *  already-completed level's skill points, across every class the character
 *  has, not just the class being leveled. Comparing the whole-character total
 *  at the old mod (before this level) against the whole-character total at
 *  the new mod (after) folds that catch-up in automatically. Mirrors the
 *  backend's `skill_budget_delta` (routers/characters.py's
 *  `level_up_character`); keep both in sync. */
export function skillBudgetDeltaForLevelUp(
  progression: CharacterProgression,
  target: LevelUpTarget,
  classes: ClassDef[],
  oldIntMod: number,
  newIntMod: number,
  raceBonusPerLevel: number,
): number {
  const before = progression.classes.map((c) => ({ className: c.className, level: c.level }));
  const after = classesAfterLevelUp(progression, target);
  return (
    classesSkillPointsTotal(after, classes, newIntMod, raceBonusPerLevel) -
    classesSkillPointsTotal(before, classes, oldIntMod, raceBonusPerLevel)
  );
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

/** A level-up always adds exactly one character level, so the
 *  "Hintergrundfertigkeiten" background-skill budget granted this level is
 *  always the flat +2 — mirrors the backend's
 *  `rules/skill_points.py::background_skill_points_total` delta
 *  (`routers/characters.py`'s `background_budget_delta`). Only meaningful
 *  when `progression.useBackgroundSkills` is set. */
export function backgroundSkillPointsForThisLevel(): number {
  return 2;
}

/** New ranks picked this level-up, split into background-skill
 *  (`SkillDef.isBackground`) vs. regular ("adventure") skills — same split
 *  creation's `skillPointsSpentByCategory` computes, just against
 *  `LevelUpDraft.skillIncreases` instead of a full skill-rank map. Budget
 *  pools are per base skill, not per specialization, so
 *  `specializationIncreases` entries fold into the same two totals. */
export function skillIncreasesByCategory(
  skillIncreases: Record<string, number>,
  skills: SkillDef[],
  specializationIncreases: LevelUpSkillSpecializationEntry[] = [],
): { background: number; regular: number } {
  const backgroundIds = new Set(skills.filter((skill) => skill.isBackground).map((skill) => skill.id));
  let background = 0;
  let regular = 0;
  for (const [skillId, ranks] of Object.entries(skillIncreases)) {
    if (backgroundIds.has(skillId)) background += ranks || 0;
    else regular += ranks || 0;
  }
  for (const entry of specializationIncreases) {
    if (backgroundIds.has(entry.skillId)) background += entry.newRanks || 0;
    else regular += entry.newRanks || 0;
  }
  return { background, regular };
}

/** Regular ("adventure") skill points still available this level-up —
 *  mirrors creation's `skillPointsRemaining` / the backend's
 *  `_skill_ranks_exceed_budget` (routers/characters.py): background-skill
 *  ranks draw from `backgroundBudget` first, only the excess competes with
 *  regular-skill ranks for `regularBudget`. */
export function skillPointsRemainingForLevelUp(
  skillIncreases: Record<string, number>,
  skills: SkillDef[],
  regularBudget: number,
  backgroundBudget: number,
  specializationIncreases: LevelUpSkillSpecializationEntry[] = [],
): number {
  const { background, regular } = skillIncreasesByCategory(skillIncreases, skills, specializationIncreases);
  const overflow = Math.max(0, background - backgroundBudget);
  return regularBudget - (regular + overflow);
}

/** Same computation as `skillBonus`-style totals, sourced from one
 *  specialization entry's existing + new ranks — `existingRanks` comes from
 *  `CharacterProgression.skillRankDetails` (0 for a brand-new specialization
 *  added this level-up), `entry.newRanks` from the draft. Mirrors the
 *  backend's `sheet.py`'s per-specialization `class_bonus` (only applies
 *  once *that* specialization has ≥1 total rank). */
export function skillSpecializationBonusForLevelUp(
  existingRanks: number,
  entry: LevelUpSkillSpecializationEntry,
  abilityMod: number,
  isClassSkill: boolean,
): number {
  const totalRanks = existingRanks + entry.newRanks;
  return totalRanks + abilityMod + (isClassSkill && totalRanks > 0 ? 3 : 0);
}
