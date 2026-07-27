import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { Character } from '../types/character';

/** Lightweight id -> display name lookup for the header's character picker, which needs to list
 *  every known character, not just the currently loaded one. Re-fetches the full character record
 *  since the backend has no name-only endpoint yet; fine for the current handful of mock fixtures. */
export function useCharacterNames(ids: string[]): Record<string, string> {
  const [names, setNames] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;
    Promise.all(
      ids.map((id) =>
        apiGet<Character>(`/api/characters/${id}`)
          .then((data) => [id, data.name] as const)
          .catch(() => [id, id] as const),
      ),
    ).then((entries) => {
      if (!cancelled) setNames(Object.fromEntries(entries));
    });
    return () => {
      cancelled = true;
    };
    // ids is compared by its joined value, not identity, so a fresh array literal from the
    // caller each render doesn't retrigger the fetch.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ids.join(',')]);

  return names;
}
