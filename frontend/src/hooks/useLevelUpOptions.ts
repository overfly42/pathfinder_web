import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';
import type { AbilityDef, ClassDef, FeatDef, ItemCatalogEntry, RaceOption, SkillDef, SkillSpecializationDef, SpellDef } from '../types/creationOptions';
import type { ClassLevelOptions } from '../types/classLevelOptions';
import type { LevelUpOptions } from '../types/levelUpOptions';

interface UseLevelUpOptionsResult {
  options: LevelUpOptions | null;
  loading: boolean;
  error: string | null;
}

/** Fetches only the reference-data resources the level-up wizard needs, in parallel
 *  (not pointBuyCosts — creation-only). Mirrors useCreationOptions.ts.
 *  `characterId` scopes `/api/feats` to that character's currently eligible
 *  feats (prerequisites checked server-side against the character's current,
 *  pre-level-up state — a same-level ability-score increase can't yet unlock
 *  a same-level feat's own score prerequisite, a known simplification) so
 *  LevelFeatStep only ever offers a legal choice. */
export function useLevelUpOptions(characterId: string): UseLevelUpOptionsResult {
  const [options, setOptions] = useState<LevelUpOptions | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      apiGet<ClassDef[]>('/api/classes'),
      apiGet<FeatDef[]>(`/api/feats?character_id=${encodeURIComponent(characterId)}`),
      apiGet<SkillDef[]>('/api/skills'),
      apiGet<SkillSpecializationDef[]>('/api/skills/specializations'),
      apiGet<AbilityDef[]>('/api/abilities'),
      apiGet<Record<string, SpellDef[]>>('/api/spells-by-class'),
      apiGet<ClassLevelOptions>('/api/class-level-options'),
      apiGet<ItemCatalogEntry[]>('/api/items'),
      apiGet<string[]>('/api/spell-schools'),
      apiGet<RaceOption[]>('/api/races'),
    ])
      .then(([classes, feats, skills, skillSpecializations, abilities, spellsByClass, classLevelOptions, items, spellSchools, races]) => {
        if (!cancelled) {
          setOptions({
            classes, feats, skills, skillSpecializations, abilities, spellsByClass, classLevelOptions, items, spellSchools, races,
          });
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
  }, [characterId]);

  return { options, loading, error };
}
