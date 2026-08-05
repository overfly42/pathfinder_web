import type { Character, ConditionCatalogEntry, EffectsView } from '../types/character';
import type { SearchEntry } from './types';

export function buildSearchIndex(
  character: Character,
  effects: EffectsView,
  conditionsCatalog: ConditionCatalogEntry[],
): SearchEntry[] {
  const index: SearchEntry[] = [];

  index.push(
    { id: 'vital-hp', label: 'Trefferpunkte', value: `${character.hp.current} / ${character.hp.max}`, category: 'Wert' },
    { id: 'vital-ac', label: 'Rüstungsklasse', value: String(character.armorClass), category: 'Wert' },
    { id: 'vital-initiative', label: 'Initiative', value: character.initiative, category: 'Wert' },
    { id: 'vital-speed', label: 'Bewegung', value: character.speed, category: 'Wert' },
  );

  for (const ability of character.abilities) {
    index.push({ id: `ability-${ability.key}`, label: ability.label, value: `${ability.score} (${ability.mod})`, category: 'Attribut' });
  }

  for (const save of character.saves) {
    index.push({ id: `save-${save.key}`, label: save.label, value: save.value, category: 'Kampfwert' });
  }
  for (const stat of character.combat) {
    index.push({ id: `combat-${stat.key}`, label: stat.label, value: stat.value, category: 'Kampfwert' });
  }

  for (const skill of character.skills) {
    index.push({ id: `skill-${skill.key}`, label: skill.label, value: skill.value, category: 'Fertigkeit', tabGroup: 'skills', tabKey: 'skills' });
  }
  for (const feat of character.feats) {
    index.push({ id: `feat-${feat.key}`, label: feat.name, value: feat.description, category: 'Talent', tabGroup: 'skills', tabKey: 'feats' });
  }
  for (const trait of character.traits) {
    index.push({ id: `trait-${trait.key}`, label: trait.name, value: trait.description, category: 'Wesenszug', tabGroup: 'skills', tabKey: 'traits' });
  }
  for (const feature of character.classFeatures) {
    index.push({ id: `classfeature-${feature.key}`, label: feature.name, value: feature.description, category: 'Klassenfähigkeit', tabGroup: 'skills', tabKey: 'classfeatures' });
  }
  for (const ability of character.raceAbilities) {
    index.push({ id: `raceability-${ability.key}`, label: ability.name, value: ability.description, category: 'Rasseneigenschaft', tabGroup: 'skills', tabKey: 'raceabilities' });
  }

  for (const item of character.gear) {
    index.push({ id: `gear-${item.id}`, label: item.name, value: `${item.qty}×`, category: 'Ausrüstung', tabGroup: 'inventory', tabKey: 'inventory' });
  }
  for (const slot of character.equipmentSlots) {
    const selectedOption = slot.options.find((o) => o.value === slot.selected);
    index.push({ id: `slot-${slot.key}`, label: slot.label, value: selectedOption ? selectedOption.label : '— leer —', category: 'Ausrüstungsplatz', tabGroup: 'inventory', tabKey: 'slots' });
  }

  for (const action of character.actions) {
    index.push({ id: `action-${action.id}`, label: action.name, value: '', category: 'Option' });
  }

  for (const effect of effects.effectsActive) {
    index.push({ id: `effect-active-${effect.id}`, label: effect.name, value: '', category: 'Aktiver Effekt' });
  }
  for (const effect of effects.effectsAvailable) {
    index.push({ id: `effect-available-${effect.id}`, label: effect.name, value: '', category: 'Verfügbar' });
  }

  // Real backend-driven effects (roadmap slice 5) — distinct ids from the mock pair above so a
  // page never has both (a character is either a fixture or database-backed, never both), but
  // kept as their own block since the two systems' data never overlaps.
  for (const effect of character.activeEffects) {
    index.push({ id: `effect-active-${effect.id}`, label: effect.name, value: '', category: 'Aktiver Effekt' });
  }
  for (const condition of conditionsCatalog) {
    index.push({
      id: `condition-catalog-${condition.id}`,
      label: condition.name,
      value: condition.description,
      category: 'Zustand/Gift/Krankheit',
    });
  }
  for (const spell of character.activatableSpells) {
    index.push({ id: `activatable-spell-${spell.key}`, label: spell.name, value: '', category: 'Aktivierbarer Zauber' });
  }
  for (const ability of character.activatableClassAbilities) {
    index.push({
      id: `activatable-ability-${ability.key}`,
      label: ability.name,
      value: '',
      category: 'Aktivierbare Klassenfähigkeit',
    });
  }

  return index;
}
