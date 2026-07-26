import type { ClassOptionGroup } from './creationOptions';

export interface ClassLevelOptionGroup extends ClassOptionGroup {
  /** Character levels at which this choice recurs (e.g. a ranger's 2nd favored enemy at 5/10/15/20). */
  levels: number[];
}

export type ClassLevelOptions = Record<string, ClassLevelOptionGroup[]>;
