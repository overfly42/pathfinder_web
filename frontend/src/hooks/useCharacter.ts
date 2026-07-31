import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { Character } from '../types/character';

interface UseCharacterResult {
  character: Character | null;
  setCharacter: React.Dispatch<React.SetStateAction<Character | null>>;
  loading: boolean;
  error: string | null;
  /** Re-fetches the character from the backend — for real (database-backed)
   *  characters, call this after a gear/slot mutation to pull the freshly
   *  computed sheet (armorClass, equipmentSlots, ...) instead of hand-patching
   *  local state. */
  refetch: () => void;
}

export function useCharacter(id: string): UseCharacterResult {
  const [character, setCharacter] = useState<Character | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

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
  }, [id, reloadKey]);

  function refetch() {
    setReloadKey((key) => key + 1);
  }

  return { character, setCharacter, loading, error, refetch };
}
