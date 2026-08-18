import { useEffect, useState } from 'react';
import { apiGet } from '../api/client';

export interface FavoredClassBonusOptions {
  options: string[];
  shortLabels: Record<string, string>;
}

/** Fetches which favored-class-bonus values are legal for one class+race
 *  combination — "hp"/"skill" (always) plus this race's own Advanced Race
 *  Guide alternates (e.g. Halb-Ork/Ork), via `GET /api/favored-class-bonus-
 *  options`. Race filtering happens server-side (`sheet.py`'s
 *  `build_favored_class_bonus_options`, shared with the level-up wizard's
 *  own helpers) rather than client-side, same reasoning as every other
 *  composition-vs-character-scoped lookup in this app. `null` while
 *  race/class aren't both chosen yet, or while loading. */
export function useFavoredClassBonusOptions(
  raceId: string | null,
  className: string | null,
): FavoredClassBonusOptions | null {
  const [result, setResult] = useState<FavoredClassBonusOptions | null>(null);

  useEffect(() => {
    if (!raceId || !className) {
      setResult(null);
      return;
    }
    let cancelled = false;
    setResult(null);
    apiGet<FavoredClassBonusOptions>(
      `/api/favored-class-bonus-options?base_class_name=${encodeURIComponent(className)}&race_id=${encodeURIComponent(raceId)}`,
    )
      .then((data) => {
        if (!cancelled) setResult(data);
      })
      .catch(() => {
        if (!cancelled) setResult(null);
      });
    return () => {
      cancelled = true;
    };
  }, [raceId, className]);

  return result;
}
