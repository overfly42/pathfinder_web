import type { GearItem } from '../types/character';

/** One-line detail summary of a gear item (enhancement, charges, special abilities, ...). */
export function gearLine(item: GearItem): string {
  const parts: string[] = [];
  if (item.enhancement) parts.push(item.enhancement);
  if (item.isMasterwork) parts.push('Meisterarbeit');
  if (item.storedSpell) parts.push(`Zauber: ${item.storedSpell}`);
  if (item.maxCharges != null) parts.push(`Ladungen ${item.chargesRemaining ?? 0}/${item.maxCharges}`);
  if (item.usesPerDay != null) parts.push(`${item.usesRemainingToday ?? 0}/${item.usesPerDay} pro Tag`);
  if (item.properties?.length) parts.push(item.properties.join(', '));
  if (item.specialAbilities?.length) {
    parts.push(item.specialAbilities.map((a) => (a.description ? `${a.name} (${a.description})` : a.name)).join('; '));
  }
  return parts.join(' · ');
}
