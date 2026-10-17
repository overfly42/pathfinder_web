import type { ClassOptionChoice, ClassOptionGroup } from '../types/creationOptions';

/** Which of a class's option groups are legal to pick from at `level`, each
 *  with its own effective cap for *this* level and its own filtered list of
 *  legal choice names — shared by the creation wizard (`ClassStep.tsx`) and
 *  the level-up wizard's new-multiclass picker (`ClassLevelStep.tsx`), the
 *  two places a player picks a class's option groups from scratch (the
 *  level-up wizard's *existing*-class picker, `ClassChoiceStep.tsx`, reads
 *  from a different, already-level-filtered endpoint instead, see its own
 *  component).
 *
 *  A one-time group (`occurrenceLevels` empty, e.g. domain/bloodline/school)
 *  always shows with its full `max`; a recurring group (Kampfrauschkraft/
 *  Trick/Offenbarung) only shows once its first occurrence is reached,
 *  capped at however many occurrences have been reached so far (not the
 *  group's lifetime `max`) — an occurrence any chosen `archetypes` has
 *  replaced (`overrides`, `ClassDef.archetypeOptionOverrides`) doesn't count
 *  as reached either, e.g. a level-1 Narbiger-Hexendoktor Hexe gets zero
 *  `hexerei` picks, not one, since Narbenschild already took that slot.
 *  `choices` is filtered by each choice's own `minLevel` so e.g. a level-1
 *  Hexe never sees 10th-level Major Hexes as a pickable option, and by the
 *  chosen `archetypes` (a Bärenschamane only sees his four domains).
 *
 *  Pure display filtering over backend-computed data — `_validate_options`
 *  on the backend is what actually enforces all of this, see
 *  `ClassOptionGroup`'s docstring. */
export function availableOptionGroups(
  groups: ClassOptionGroup[],
  level: number,
  archetypes: string[],
  overrides: Record<string, Record<string, number[]>>,
  selected: Record<string, string[]> = {},
): (ClassOptionGroup & { effectiveMax: number; availableChoiceNames: string[] })[] {
  return groups
    .map((g) => {
      const removedLevels = new Set(archetypes.flatMap((a) => overrides[a]?.[g.key] ?? []));
      const reachedLevels = g.occurrenceLevels.filter((l) => l <= level && !removedLevels.has(l));
      return {
        ...g,
        effectiveMax: g.occurrenceLevels.length === 0 ? g.max : reachedLevels.length,
        availableChoiceNames: g.choices
          .filter(
            (c) =>
              (c.minLevel === null || c.minLevel <= level) &&
              prerequisiteMet(c, selected) &&
              archetypeAllows(c, archetypes),
          )
          .map((c) => c.name),
      };
    })
    .filter((g) => g.effectiveMax > 0 && g.availableChoiceNames.length > 0);
}

/** Whether the chosen `archetypes` allow `choice` (its `onlyForArchetypes`/
 *  `excludedForArchetypes` scoping). */
function archetypeAllows(choice: ClassOptionChoice, archetypes: string[]): boolean {
  if (choice.onlyForArchetypes && !choice.onlyForArchetypes.some((a) => archetypes.includes(a))) return false;
  return !(choice.excludedForArchetypes ?? []).some((a) => archetypes.includes(a));
}

/** Whether `choice`'s `requiresChoice` (if any) is among the `selected`
 *  picks (group key -> chosen names) of the same class. */
function prerequisiteMet(choice: ClassOptionChoice, selected: Record<string, string[]>): boolean {
  const req = choice.requiresChoice;
  return req === null || (selected[req.groupKey] ?? []).includes(req.name);
}

/** `selected` with every pick whose prerequisite is no longer picked removed
 *  — called after each toggle so un-picking e.g. the Druide's "Domäne
 *  (Natur)" bond also drops the domain that depended on it, instead of
 *  leaving a hidden pick the backend would reject. Repeats until stable so a
 *  chain of prerequisites unwinds fully. */
export function pruneUnmetPrerequisites(
  groups: ClassOptionGroup[],
  selected: Record<string, string[]>,
): Record<string, string[]> {
  let current = selected;
  for (;;) {
    let changed = false;
    const next: Record<string, string[]> = {};
    for (const [groupKey, names] of Object.entries(current)) {
      const group = groups.find((g) => g.key === groupKey);
      const kept = names.filter((name) => {
        const choice = group?.choices.find((c) => c.name === name);
        return choice === undefined || prerequisiteMet(choice, current);
      });
      if (kept.length !== names.length) changed = true;
      next[groupKey] = kept;
    }
    if (!changed) return current;
    current = next;
  }
}

/** `selected` without picks the chosen `archetypes` don't allow (e.g. a Feuer domain once
 *  Bärenschamane is picked), then without anything that depended on them — called when the
 *  archetype selection changes. */
export function pruneForArchetypes(
  groups: ClassOptionGroup[],
  selected: Record<string, string[]>,
  archetypes: string[],
): Record<string, string[]> {
  const allowed: Record<string, string[]> = {};
  for (const [groupKey, names] of Object.entries(selected)) {
    const group = groups.find((g) => g.key === groupKey);
    allowed[groupKey] = names.filter((name) => {
      const choice = group?.choices.find((c) => c.name === name);
      return choice === undefined || archetypeAllows(choice, archetypes);
    });
  }
  return pruneUnmetPrerequisites(groups, allowed);
}
