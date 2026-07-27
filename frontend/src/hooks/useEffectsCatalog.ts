import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { EffectDef } from '../types/character';

interface UseEffectsCatalogResult {
  catalog: EffectDef[] | null;
  loading: boolean;
  error: string | null;
}

/** The shared conditions/effects catalog (`/api/effects`) — same for every character, same as
 *  useCreationOptions fetching /api/feats or /api/traits. Not scoped to a character id. */
export function useEffectsCatalog(): UseEffectsCatalogResult {
  const [catalog, setCatalog] = useState<EffectDef[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiGet<EffectDef[]>('/api/effects')
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
