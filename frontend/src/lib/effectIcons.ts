import type { ActiveEffect, ConditionType, EffectSourceType } from '../types/character';

/** One glyph per condition subtype and per non-condition source type (roadmap slice 5) — shown
 *  in the effect "seal" blob, same spot the older mock catalog used its own per-def icon. */
export const CONDITION_TYPE_ICONS: Record<ConditionType, string> = {
  condition: '🌀',
  poison: '☠️',
  disease: '🦠',
};

export const SOURCE_TYPE_ICONS: Record<EffectSourceType, string> = {
  condition: CONDITION_TYPE_ICONS.condition,
  spell: '✨',
  class_ability: '⚔️',
  feat: '🎯',
};

export function iconForActiveEffect(effect: ActiveEffect): string {
  if (effect.sourceType === 'condition' && effect.conditionType) return CONDITION_TYPE_ICONS[effect.conditionType];
  return SOURCE_TYPE_ICONS[effect.sourceType];
}
