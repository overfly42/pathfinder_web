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
 *  slots granted by race (Human's "Bonustalent") or class (e.g. Kämpfer's bonus
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

/** Builds `CharacterCreate.feats` (backend's `FeatSelection` list) from
 *  `draft.feats`/`draft.featSubChoices` — pairs each chosen feat with its
 *  sub-choice (roadmap.md's "Talent-Sub-Wahl-Schema"), keyed by the feat's
 *  own `subChoiceType` so the right field gets populated. A feat needing a
 *  sub-choice that hasn't been picked yet (`FeatsStep.tsx`'s dropdown still
 *  empty) is submitted with none set — the backend rejects that with a 422,
 *  same as any other incomplete required field. */
export function featSelectionsForSubmission(draft: CreationDraft, options: CreationOptions) {
  const featById = new Map(options.feats.map((f) => [f.id, f]));
  return draft.feats.map((featId) => {
    const feat = featById.get(featId);
    const subChoice = draft.featSubChoices[featId];
    return {
      feat_id: featId,
      chosen_weapon_id: feat?.subChoiceType === 'weapon' ? subChoice ?? null : null,
      chosen_skill_id: feat?.subChoiceType === 'skill' ? subChoice ?? null : null,
      chosen_spell_school: feat?.subChoiceType === 'spell_school' ? subChoice ?? null : null,
    };
  });
}

/** Builds `CharacterCreate.trait_skill_choices` from `draft.traits`/
 *  `draft.traitSkillChoices` — only an entry for a chosen trait whose
 *  `TraitDef.skillChoiceAbility` isn't null (the backend rejects a stray
 *  entry for a trait that doesn't take one, `_validate_trait_skill_choice`),
 *  same "empty submission unless a chosen trait actually needs a sub-choice"
 *  reasoning as `featSelectionsForSubmission`. */
export function traitSkillChoicesForSubmission(draft: CreationDraft, options: CreationOptions): Record<string, string> {
  const traitById = new Map(options.traits.map((t) => [t.id, t]));
  const result: Record<string, string> = {};
  for (const traitId of draft.traits) {
    const trait = traitById.get(traitId);
    const skillChoice = draft.traitSkillChoices[traitId];
    if (trait?.skillChoiceAbility && skillChoice) {
      result[traitId] = skillChoice;
    }
  }
  return result;
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

/** Mirrors the backend's `rules/skill_points.py::background_skill_points_total`;
 *  keep both in sync. 2 ranks per character level, never modified by Int mod
 *  or any race/class bonus — only meaningful when `draft.useBackgroundSkills`
 *  is on (http://prd.5footstep.de/Alternativregeln/Fertigkeiten/Hintergrundfertigkeiten). */
export function backgroundSkillPointsTotal(draft: CreationDraft): number {
  return 2 * totalLevel(draft);
}

/** Ranks spent so far, split into background-skill (`SkillDef.isBackground`)
 *  vs. regular ("adventure") skills — the split `skillPointsRemaining` needs
 *  to apply the "Hintergrundfertigkeiten" overflow rule. */
export function skillPointsSpentByCategory(
  draft: CreationDraft,
  options: CreationOptions,
): { background: number; regular: number } {
  const backgroundIds = new Set(options.skills.filter((skill) => skill.isBackground).map((skill) => skill.id));
  let background = 0;
  let regular = 0;
  for (const [skillId, ranks] of Object.entries(draft.skillRanks)) {
    if (backgroundIds.has(skillId)) background += ranks || 0;
    else regular += ranks || 0;
  }
  return { background, regular };
}

/** Regular ("adventure") skill points still available, mirrors the backend's
 *  `_skill_ranks_exceed_budget` (routers/characters.py): with
 *  `useBackgroundSkills` off, `backgroundBudget` is 0 and this is a plain
 *  `regularBudget - spent`. With it on, background-skill ranks draw from
 *  `backgroundBudget` first — only the excess beyond it competes with
 *  regular-skill ranks for `regularBudget`; background points that go
 *  unspent are simply lost, never covering a regular skill. */
export function skillPointsRemaining(
  draft: CreationDraft,
  options: CreationOptions,
  regularBudget: number,
  backgroundBudget: number,
): number {
  const { background, regular } = skillPointsSpentByCategory(draft, options);
  const overflow = Math.max(0, background - backgroundBudget);
  return regularBudget - (regular + overflow);
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

/** Archetypes chosen for a given class name — read off the first `classRows`
 *  entry with that name (a class's archetype choice is one pick shared
 *  across every row of it, not per-row). */
export function archetypesForClass(draft: CreationDraft, className: string): string[] {
  return draft.classRows.find((r) => r.className === className)?.archetypes ?? [];
}

/** The casting ability actually in effect once the row's chosen archetype(s)
 *  are factored in: an archetype's own override when it has one (Hexe's
 *  Narbiger Hexendoktor casts on KO instead of IN — `ClassDef.
 *  archetypeCastingAbility`), else the class's own `castingAbility`. Mirrors
 *  the backend's `_resolve_casting_ability`; keep both in sync. */
export function effectiveCastingAbility(cls: ClassDef, archetypeNames: string[]): AbilityKey | null {
  for (const name of archetypeNames) {
    const override = cls.archetypeCastingAbility[name];
    if (override) return override;
  }
  return cls.castingAbility;
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
