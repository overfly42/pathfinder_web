import type { CompanionLevel } from '../types/character';

type Breakdown = { label: string; value: number; detail: string | null }[];

/** "Druide 4 + Waldläufer 6 − 3 + Stallmeister +1" — the backend's per-source breakdown
 *  (`rules/companions.py`), plus a note when the character level capped the sum. */
export function formatCompanionBreakdown(entry: { breakdown: Breakdown; level?: number | null; uncapped?: number }): string {
  const parts = entry.breakdown.map((b) => (b.detail ? b.detail : `${b.label} +${b.value}`));
  const capped =
    entry.uncapped != null && entry.level != null && entry.uncapped > entry.level
      ? ` (max. Charakterstufe, ohne Begrenzung ${entry.uncapped})`
      : '';
  return `${parts.join(' + ')}${capped}`;
}

/** What the track's level stands for in PF1e terms. */
export function companionLevelName(track: CompanionLevel['track']): string {
  return track === 'familiar' ? 'Magierstufe' : 'effektive Druidenstufe';
}

/** PRD "Mit Tieren umgehen" — the rules text shown next to the companion's tricks. The tricks
 *  and trainings themselves come from `GET /api/companion-tricks` (roadmap slice 10 step 5). */
export const TRICK_HELP =
  'Einen Trick beizubringen dauert eine Woche und einen Wurf auf Mit Tieren umgehen gegen den SG. ' +
  'Ein Tier mit IN 1 kann maximal 3, mit IN 2 maximal 6 Tricks lernen (ab IN 3 unbegrenzt, das PRD ' +
  'nennt dafür kein Limit); Bonustricks zählen nicht dagegen und brauchen weder Abrichten noch Wurf. Eine ' +
  'Aufgabe ist ein Paket von Tricks (ein Wurf statt einem je Trick), ein Tier kann nur eine Aufgabe haben; ' +
  'eine Aufgabe mit mehr als 3 Tricks braucht IN 2. "Angreifen (alle Wesen)" zählt als zwei Tricks.';
