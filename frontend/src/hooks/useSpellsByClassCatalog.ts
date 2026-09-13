import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { SpellDef } from '../types/creationOptions';

interface UseSpellsByClassCatalogResult {
  catalog: Record<string, SpellDef[]> | null;
  loading: boolean;
  error: string | null;
}

/** `/api/spells-by-class` (class name -> its fixed spell list, grade included) — same catalog
 *  `useCreationOptions`/`useLevelUpOptions` already fetch for their spell pickers, reused here for
 *  the character sheet's in-play "add to spellbook" picker (`Spellbook.tsx`). Not scoped to a
 *  character id, same as `useItemsCatalog`. */
export function useSpellsByClassCatalog(): UseSpellsByClassCatalogResult {
  const [catalog, setCatalog] = useState<Record<string, SpellDef[]> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiGet<Record<string, SpellDef[]>>('/api/spells-by-class')
      .then((data) => {
        if (!cancelled) setCatalog(data);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { catalog, loading, error };
}
