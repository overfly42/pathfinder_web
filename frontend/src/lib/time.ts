export type TimeUnit = 'round' | 'minute' | 'hour' | 'day';

export const ROUNDS_PER_UNIT: Record<TimeUnit, number> = {
  round: 1,
  minute: 10,
  hour: 600,
  /** A day is a large but finite round count (24h), not Infinity — timed effects should decrement
   *  and expire like any other unit, not get silently dropped. */
  day: 600 * 24,
};

export const TIME_UNIT_LABELS: Record<TimeUnit, string> = {
  round: 'Runde(n)',
  minute: 'Minute(n)',
  hour: 'Stunde(n)',
  day: 'Tag(e)',
};

/** Renders a round count back in the largest unit it divides evenly into, so a stored value of
 *  e.g. 100 rounds displays as "10 Minuten" instead of "100 Runden". Falls back to rounds when
 *  the value doesn't line up with a bigger unit (e.g. an odd number of rounds). */
export function roundsToUnitValue(rounds: number): { value: number; unit: TimeUnit } {
  const units: TimeUnit[] = ['day', 'hour', 'minute', 'round'];
  for (const unit of units) {
    if (rounds % ROUNDS_PER_UNIT[unit] === 0) return { value: rounds / ROUNDS_PER_UNIT[unit], unit };
  }
  return { value: rounds, unit: 'round' };
}
