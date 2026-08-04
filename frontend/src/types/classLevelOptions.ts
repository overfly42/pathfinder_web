export interface ClassLevelOptionGroup {
  key: string;
  label: string;
  max: number;
  /** Choice names legal to pick at each occurrence level — already filtered
   *  server-side against each choice's `min_level` (e.g. Kampfrauschkraft's
   *  "Innere Zähigkeit" is only present under level 8's key), since this
   *  wizard is not a player-facing rules reference and must never offer a
   *  choice the character isn't eligible for yet. */
  choicesByLevel: Record<number, string[]>;
  /** Character levels at which this choice recurs (e.g. a ranger's 2nd favored enemy at 5/10/15/20). */
  levels: number[];
}

export type ClassLevelOptions = Record<string, ClassLevelOptionGroup[]>;
