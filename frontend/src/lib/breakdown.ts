import type { BreakdownEntry } from '../types/character';

/** Renders a value-origin breakdown (`SkillEntry.breakdown`/
 *  `Character.armorClassBreakdown`) as a multi-line tooltip string, one
 *  entry per line with an explicit sign — `undefined` when there's nothing
 *  to show, so callers can pass it straight to a `title` attribute without
 *  producing an empty tooltip. */
export function formatBreakdown(entries: BreakdownEntry[] | undefined): string | undefined {
  if (!entries || entries.length === 0) return undefined;
  return entries.map((entry) => `${entry.label}: ${entry.value >= 0 ? '+' : ''}${entry.value}`).join('\n');
}
