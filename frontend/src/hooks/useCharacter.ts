import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { Character } from '../types/character';

interface UseCharacterResult {
  character: Character | null;
  setCharacter: React.Dispatch<React.SetStateAction<Character | null>>;
  loading: boolean;
  error: string | null;
}

export function useCharacter(id: string): UseCharacterResult {
  const [character, setCharacter] = useState<Character | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    if (!id) {
      // No character owned/selected (e.g. a freshly created user) — nothing to fetch.
      setCharacter(null);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    apiGet<Character>(`/api/characters/${id}`)
      .then((data) => {
        if (!cancelled) setCharacter(data);
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
  }, [id]);

  return { character, setCharacter, loading, error };
}
