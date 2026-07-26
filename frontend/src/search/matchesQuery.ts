import type { SearchEntry } from './types';

const SEARCH_ALIASES: Record<string, string> = {
  bab: 'gab',
  cmb: 'kmb',
  cmd: 'kmd',
  ac: 'rüstungsklasse',
  hp: 'trefferpunkte',
  perc: 'wahrnehmung',
  init: 'initiative',
  spd: 'bewegung',
};

export function matchesQuery(entry: SearchEntry, query: string): boolean {
  const haystack = `${entry.label} ${entry.value} ${entry.category}`.toLowerCase();
  if (haystack.includes(query)) return true;
  const alias = SEARCH_ALIASES[query];
  return !!alias && haystack.includes(alias);
}
