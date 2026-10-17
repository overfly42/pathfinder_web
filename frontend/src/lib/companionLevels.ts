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

/** PRD "Mit Tieren umgehen" — static help text for the companion sheet; tricks are descriptive
 *  only (roadmap slice 10: no trick tables, no stored picks). */
export const TRICK_HELP = {
  rules:
    'Einen Trick beizubringen dauert eine Woche und einen Wurf auf Mit Tieren umgehen gegen den SG. ' +
    'Ein Tier mit IN 1 kann maximal 3, mit IN 2 maximal 6 Tricks lernen; Bonustricks zählen nicht dagegen ' +
    'und brauchen weder Abrichten noch Wurf.',
  tricks: [
    'Angreifen (SG 20)',
    'Arbeiten (SG 15)',
    'Bei Fuß gehen (SG 15)',
    'Bleiben (SG 15)',
    'Bringen (SG 15)',
    'Kommen (SG 15)',
    'Kunststück (SG 15)',
    'Spuren suchen (SG 20, braucht Geruchssinn)',
    'Suchen (SG 15)',
    'Verteidigen (SG 20)',
    'Wachen (SG 20)',
    'Zurückziehen (SG 20)',
  ],
  trainings: [
    'Kampfausbildung (SG 20): Angreifen, Bei Fuß gehen, Kommen, Verteidigen, Wachen, Zurückziehen',
    'Kämpfen (SG 20): Angreifen, Bleiben, Zurückziehen',
    'Wache halten (SG 20): Angreifen, Verteidigen, Wachen, Zurückziehen',
    'Lastarbeit (SG 15): Arbeiten, Kommen',
    'Jagen (SG 20): Angreifen, Bei Fuß gehen, Bringen, Spuren suchen, Suchen, Zurückziehen',
    'Kunststück vorführen (SG 15): Bleiben, Bringen, Kommen, Kunststück',
    'Reiten (SG 15): Bei Fuß gehen, Bleiben, Kommen',
  ],
};
