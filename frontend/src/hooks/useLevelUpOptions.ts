import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { AbilityDef, ClassDef, SkillDef } from '../types/creationOptions';
import type { ClassLevelOptions } from '../types/classLevelOptions';
import type { LevelUpOptions } from '../types/levelUpOptions';

interface UseLevelUpOptionsResult {
  options: LevelUpOptions | null;
  loading: boolean;
  error: string | null;
}

/** Fetches only the reference-data resources the level-up wizard needs, in parallel
 *  (not races/items/pointBuyCosts — those are creation-only). Mirrors useCreationOptions.ts. */
export function useLevelUpOptions(): UseLevelUpOptionsResult {
  const [options, setOptions] = useState<LevelUpOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      apiGet<ClassDef[]>('/api/classes'),
      apiGet<string[]>('/api/feats'),
      apiGet<SkillDef[]>('/api/skills'),
      apiGet<AbilityDef[]>('/api/abilities'),
      apiGet<Record<string, string[]>>('/api/spells-by-class'),
      apiGet<ClassLevelOptions>('/api/class-level-options'),
    ])
      .then(([classes, feats, skills, abilities, spellsByClass, classLevelOptions]) => {
        if (!cancelled) {
          setOptions({ classes, feats, skills, abilities, spellsByClass, classLevelOptions });
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
