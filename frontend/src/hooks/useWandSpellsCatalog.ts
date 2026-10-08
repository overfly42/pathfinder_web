import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { SpellDef } from '../types/creationOptions';

/** `/api/wand-spells` (every spell of grade 4 or lower, across all classes) — the wand picker's
 *  options. Not scoped to a character id, same as `useItemsCatalog`. */
export function useWandSpellsCatalog(): SpellDef[] | null {
  const [catalog, setCatalog] = useState<SpellDef[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiGet<SpellDef[]>('/api/wand-spells')
      .then((data) => {
        if (!cancelled) setCatalog(data);
      })
      .catch(() => {
        if (!cancelled) setCatalog([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return catalog;
}
