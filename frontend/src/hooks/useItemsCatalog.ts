import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { ItemCatalogEntry } from '../types/creationOptions';

interface UseItemsCatalogResult {
  catalog: ItemCatalogEntry[] | null;
  loading: boolean;
  error: string | null;
}

/** The shared gear catalog (`/api/items`) — same for every character, same shape
 *  `useCreationOptions` already uses for `EquipmentStep.tsx`. Not scoped to a character id. */
export function useItemsCatalog(): UseItemsCatalogResult {
  const [catalog, setCatalog] = useState<ItemCatalogEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiGet<ItemCatalogEntry[]>('/api/items')
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
