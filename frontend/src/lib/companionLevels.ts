import type { CompanionLevel } from '../types/character';

/** "Druide 4 + Waldläufer 6 − 3 + Stallmeister +1" — the backend's per-source breakdown
 *  (`rules/companions.py`), plus a note when the character level capped the sum. */
export function formatCompanionBreakdown(entry: CompanionLevel): string {
  const parts = entry.breakdown.map((b) => (b.detail ? b.detail : `${b.label} +${b.value}`));
  const capped = entry.uncapped > entry.level ? ` (max. Charakterstufe, ohne Begrenzung ${entry.uncapped})` : '';
  return `${parts.join(' + ')}${capped}`;
}

/** What the track's level stands for in PF1e terms. */
export function companionLevelName(entry: CompanionLevel): string {
  return entry.track === 'familiar' ? 'Magierstufe' : 'effektive Druidenstufe';
}
