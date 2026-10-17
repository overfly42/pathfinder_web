import type { CreationDraft } from '../types/creationDraft';
import type { CreationOptions } from '../types/creationOptions';

/** Language-neutral alignment codes, as stored by the backend
 *  (`Character.alignment`, `rules/alignment.py`'s `ALIGNMENTS`). */
export type Alignment = 'LG' | 'NG' | 'CG' | 'LN' | 'N' | 'CN' | 'LE' | 'NE' | 'CE';

export const ALIGNMENTS: { code: Alignment; label: string }[] = [
  { code: 'LG', label: 'Rechtschaffen gut' },
  { code: 'NG', label: 'Neutral gut' },
  { code: 'CG', label: 'Chaotisch gut' },
  { code: 'LN', label: 'Rechtschaffen neutral' },
  { code: 'N', label: 'Neutral' },
  { code: 'CN', label: 'Chaotisch neutral' },
  { code: 'LE', label: 'Rechtschaffen böse' },
  { code: 'NE', label: 'Neutral böse' },
  { code: 'CE', label: 'Chaotisch böse' },
];

export function alignmentLabel(code: string | null | undefined): string {
  return ALIGNMENTS.find((a) => a.code === code)?.label ?? '—';
}

/** Classes of the draft whose `allowedAlignments` the draft's current alignment doesn't
 *  satisfy (an unset alignment conflicts with every restricted class) — mirrors the backend's
 *  `_check_alignment`, which is what actually enforces it. */
export function alignmentConflicts(draft: CreationDraft, options: CreationOptions): string[] {
  const names = new Set(draft.classRows.map((row) => row.className));
  return options.classes
    .filter((c) => names.has(c.name) && c.allowedAlignments && !c.allowedAlignments.includes(draft.alignment as Alignment))
    .map((c) => c.name);
}
