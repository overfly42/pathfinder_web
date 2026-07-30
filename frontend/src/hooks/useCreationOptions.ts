import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { AbilityDef, ClassDef, CreationOptions, FeatDef, ItemCatalogEntry, RaceOption, SkillDef } from '../types/creationOptions';

interface UseCreationOptionsResult {
  options: CreationOptions | null;
  loading: boolean;
  error: string | null;
}

/** Fetches the reference-data resources the character-creation wizard needs, in parallel,
 *  and assembles them into one CreationOptions object (so step components don't need to
 *  know these come from separate endpoints). Level-up will use its own hook that only
 *  fetches the subset it needs (classes/feats/traits/skills/abilities/spellsByClass). */
export function useCreationOptions(): UseCreationOptionsResult {
  const [options, setOptions] = useState<CreationOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      apiGet<RaceOption[]>('/api/races'),
      apiGet<ClassDef[]>('/api/classes'),
      apiGet<FeatDef[]>('/api/feats'),
      apiGet<string[]>('/api/traits'),
      apiGet<SkillDef[]>('/api/skills'),
      apiGet<AbilityDef[]>('/api/abilities'),
      apiGet<Record<string, string[]>>('/api/spells-by-class'),
      apiGet<Record<number, number>>('/api/point-buy-costs'),
      apiGet<ItemCatalogEntry[]>('/api/items'),
    ])
      .then(([races, classes, feats, traits, skills, abilities, spellsByClass, pointBuyCosts, items]) => {
        if (!cancelled) {
          setOptions({ races, classes, feats, traits, skills, abilities, spellsByClass, pointBuyCosts, items });
        }
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

  return { options, loading, error };
}
