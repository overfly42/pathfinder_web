import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { CharacterProgression } from '../types/characterProgression';

interface UseCharacterProgressionResult {
  progression: CharacterProgression | null;
  loading: boolean;
  error: string | null;
}

export function useCharacterProgression(characterId: string): UseCharacterProgressionResult {
  const [progression, setProgression] = useState<CharacterProgression | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    apiGet<CharacterProgression>(`/api/characters/${characterId}/progression`)
      .then((data) => {
        if (!cancelled) setProgression(data);
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
  }, [characterId]);

  return { progression, loading, error };
}
