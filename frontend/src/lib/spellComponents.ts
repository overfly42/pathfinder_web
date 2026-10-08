import type { SpellComponents } from '../types/character';

export type Language = 'de' | 'en';

/** Per-language component abbreviations (PRD "V, G, M, F, GF" vs. core rulebook "V, S, M, F, DF").
 *  Only the abbreviations are translated; the `materialDescription`/`focusDescription` free text
 *  stays German until content translation exists. */
const LABELS: Record<Language, { verbal: string; somatic: string; material: string; focus: string; divineFocus: string }> = {
  de: { verbal: 'V', somatic: 'G', material: 'M', focus: 'F', divineFocus: 'GF' },
  en: { verbal: 'V', somatic: 'S', material: 'M', focus: 'F', divineFocus: 'DF' },
};

/** "V, G, M (...)"-style display string; "—" when no component row is seeded for the spell. */
export function formatSpellComponents(components: SpellComponents | null | undefined, language: Language): string {
  if (!components) return '—';
  const l = LABELS[language];
  const parts: string[] = [];
  if (components.verbal) parts.push(l.verbal);
  if (components.somatic) parts.push(l.somatic);
  if (components.material) parts.push(components.materialDescription ? `${l.material} (${components.materialDescription})` : l.material);
  if (components.focus) parts.push(components.focusDescription ? `${l.focus} (${components.focusDescription})` : l.focus);
  if (components.divineFocus) parts.push(l.divineFocus);
  return parts.length ? parts.join(', ') : '—';
}
