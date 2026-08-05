import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { ConditionCatalogEntry } from '../types/character';

interface UseConditionsCatalogResult {
  catalog: ConditionCatalogEntry[] | null;
  loading: boolean;
  error: string | null;
}

/** The shared condition/poison/disease catalog (`/api/conditions`, roadmap slice 5) — same for
 *  every character, not scoped to a character id. Distinct from the older mock `/api/effects`
 *  catalog (`useEffectsCatalog`), which predates this backend model. */
export function useConditionsCatalog(): UseConditionsCatalogResult {
  const [catalog, setCatalog] = useState<ConditionCatalogEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiGet<ConditionCatalogEntry[]>('/api/conditions')
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
