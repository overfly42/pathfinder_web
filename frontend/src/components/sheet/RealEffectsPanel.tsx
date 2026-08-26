import { useMemo } from 'react';
import type {
  ActivatableRef,
  ActiveEffect,
  ConditionCatalogEntry,
  ConditionType,
} from '../../types/character';
import { CONDITION_TYPE_ICONS, SOURCE_TYPE_ICONS, iconForActiveEffect } from '../../lib/effectIcons';
import { Panel } from '../primitives/Panel';
import type { TimeUnit } from './EffectsPanel';
import type { AvailableEntry } from './ActivateEffectModal';

export type { ActivateEffectInput } from './ActivateEffectModal';

const TYPE_LABELS: Record<ConditionType, string> = {
  condition: 'Zustand',
  poison: 'Gift',
  disease: 'Krankheit',
};

const TIME_BUTTONS: { unit: TimeUnit; label: string; className?: string }[] = [
  { unit: 'round', label: '+1 Runde' },
  { unit: 'minute', label: '+1 Minute' },
  { unit: 'hour', label: '+1 Stunde' },
  { unit: 'day', label: '+1 Tag', className: 'day' },
];

interface ActiveEffectSealProps {
  effect: ActiveEffect;
  onRemove: (effectId: string) => void;
  onSaveResult: (effectId: string, success: boolean) => void;
}

function ActiveEffectSeal({ effect, onRemove, onSaveResult }: ActiveEffectSealProps) {
  const isFrequencyTracked = effect.frequencyRounds != null;

  let ribbon: string;
  if (!effect.removable) {
    // Item-granted (`_build_item_granted_effects` on the backend): stays on for as long as the
    // gear is equipped, no duration to count down and nothing here to remove independently.
    ribbon = 'Solange ausgerüstet';
  } else if (isFrequencyTracked) {
    ribbon = `Rettungswurf in ${effect.nextCheckIn ?? 0} ${effect.nextCheckIn === 1 ? 'Rd.' : 'Rd.'}`;
  } else if (effect.durationRemaining != null) {
    ribbon = `${effect.durationRemaining} ${effect.durationRemaining === 1 ? 'Runde' : 'Runden'}`;
  } else if (effect.incubationRemaining != null) {
    ribbon = `Inkubation ${effect.incubationRemaining}`;
  } else if (effect.dailyLimitRemaining != null) {
    // Kampfrausch-shaped abilities: no fixed duration on the effect itself (see `dailyLimitRemaining`'s
    // own docstring on the backend) — the daily pool is the only "how much longer" info there is.
    ribbon = `${effect.dailyLimitRemaining} von ${effect.dailyLimitTotal} Runden heute`;
  } else {
    ribbon = 'bis Entfernen';
  }

  return (
    <div className="seal" id={`effect-active-${effect.id}`}>
      {effect.removable && (
        <button type="button" className="seal-remove" title="Entfernen" onClick={() => onRemove(effect.id)}>✕</button>
      )}
      <div className="seal-blob buff">
        <div className="glyph">{iconForActiveEffect(effect)}</div>
        {effect.level != null && <div className="amount">Stf {effect.level}</div>}
      </div>
      <div className="seal-name">{effect.name}</div>
      <div className="seal-ribbon">{ribbon}</div>
      {isFrequencyTracked && (
        <>
          {effect.successesRequired != null && (
            <div className="pip-row" title={`${effect.successesCurrent} von ${effect.successesRequired} Erfolgen`}>
              {Array.from({ length: effect.successesRequired }).map((_, index) => (
                <span key={index} className={`pip${index < effect.successesCurrent ? ' filled' : ''}`} />
              ))}
            </div>
          )}
          <div className="seal-actions">
            <button type="button" className="seal-action-btn confirm" onClick={() => onSaveResult(effect.id, true)}>Erfolg</button>
            <button type="button" className="seal-action-btn dmg" onClick={() => onSaveResult(effect.id, false)}>Fehlschlag</button>
          </div>
        </>
      )}
    </div>
  );
}

interface AvailableEffectSealProps {
  entry: AvailableEntry;
  onPick: (entry: AvailableEntry) => void;
}

function AvailableEffectSeal({ entry, onPick }: AvailableEffectSealProps) {
  // Class-ability entries only ever carry a short "X von Y ... heute übrig" pool summary in
  // `description` here (`sheet.py`'s `_build_activatable_class_abilities` — never the ability's
  // full rules text), so it's safe to surface directly on the card instead of hover-only, the same
  // way `ActionsPanel`'s own daily-limited cards already show their remaining count visibly. Every
  // other source type's `description` is the full catalog text (spell/feat/condition), which stays
  // hover-only via `title` — showing that inline would blow up the card.
  const visibleDescription = entry.sourceType === 'class_ability' ? entry.description : undefined;
  return (
    <button
      type="button"
      className="seal inactive"
      id={entry.domId}
      title={entry.description}
      onClick={() => onPick(entry)}
    >
      <div className="seal-blob inactive">
        <div className="glyph">{entry.icon}</div>
      </div>
      <div className="seal-name">{entry.name}</div>
      <div className="seal-ribbon inactive">{entry.tag}</div>
      {visibleDescription && <div className="seal-daily-limit">{visibleDescription}</div>}
    </button>
  );
}

interface RealEffectsPanelProps {
  activeEffects: ActiveEffect[];
  conditionsCatalog: ConditionCatalogEntry[];
  activatableSpells: ActivatableRef[];
  activatableClassAbilities: ActivatableRef[];
  activatableFeats: ActivatableRef[];
  externalClassAbilities: ActivatableRef[];
  search: string;
  onSearchChange: (value: string) => void;
  typeFilter: ConditionType | '';
  onTypeFilterChange: (value: ConditionType | '') => void;
  onAdvanceTime: (unit: TimeUnit) => void;
  onPick: (entry: AvailableEntry) => void;
  onRemove: (effectId: string) => void;
  onSaveResult: (effectId: string, success: boolean) => void;
}

export function RealEffectsPanel({
  activeEffects,
  conditionsCatalog,
  activatableSpells,
  activatableClassAbilities,
  activatableFeats,
  externalClassAbilities,
  search,
  onSearchChange,
  typeFilter,
  onTypeFilterChange,
  onAdvanceTime,
  onPick,
  onRemove,
  onSaveResult,
}: RealEffectsPanelProps) {
  const hint = `${activeEffects.length} aktiv · ${conditionsCatalog.length} im Kompendium`;

  const availableEntries = useMemo<AvailableEntry[]>(() => {
    const term = search.trim().toLowerCase();
    const entries: AvailableEntry[] = [];

    if (!typeFilter) {
      for (const spell of activatableSpells) {
        if (term && !spell.name.toLowerCase().includes(term)) continue;
        entries.push({
          domId: `activatable-spell-${spell.key}`,
          sourceType: 'spell',
          sourceId: spell.key,
          name: spell.name,
          icon: SOURCE_TYPE_ICONS.spell,
          tag: 'Zauber',
        });
      }
      const ownAbilityIds = new Set<string>();
      for (const ability of activatableClassAbilities) {
        ownAbilityIds.add(ability.key);
        if (term && !ability.name.toLowerCase().includes(term)) continue;
        entries.push({
          domId: `activatable-ability-${ability.key}`,
          sourceType: 'class_ability',
          sourceId: ability.key,
          name: ability.name,
          description: ability.description ?? undefined,
          icon: SOURCE_TYPE_ICONS.class_ability,
          tag: 'Klassenfähigkeit',
          defaultDurationRounds: ability.defaultDurationRounds,
        });
      }
      for (const feat of activatableFeats) {
        if (term && !feat.name.toLowerCase().includes(term)) continue;
        entries.push({
          domId: `activatable-feat-${feat.key}`,
          sourceType: 'feat',
          sourceId: feat.key,
          name: feat.name,
          description: feat.description ?? undefined,
          icon: SOURCE_TYPE_ICONS.feat,
          tag: 'Talent',
          defaultDurationRounds: feat.defaultDurationRounds,
        });
      }
      // Effects received from someone else's ability (e.g. a Barde's Lied des Mutes) — offered to
      // every character regardless of whether they have it granted, same as conditionsCatalog below.
      // Skipped here if already listed above (an ability with activation_scope 'both' appears in
      // both backend lists for the character who owns it; the picker only needs it once).
      for (const ability of externalClassAbilities) {
        if (ownAbilityIds.has(ability.key)) continue;
        if (term && !ability.name.toLowerCase().includes(term)) continue;
        entries.push({
          domId: `external-ability-${ability.key}`,
          sourceType: 'class_ability',
          sourceId: ability.key,
          name: ability.name,
          icon: SOURCE_TYPE_ICONS.class_ability,
          tag: 'Klassenfähigkeit (von außen)',
        });
      }
    }

    for (const condition of conditionsCatalog) {
      if (typeFilter && condition.type !== typeFilter) continue;
      if (term && !condition.name.toLowerCase().includes(term)) continue;
      entries.push({
        domId: `condition-catalog-${condition.id}`,
        sourceType: 'condition',
        sourceId: condition.id,
        name: condition.name,
        description: condition.description,
        icon: CONDITION_TYPE_ICONS[condition.type],
        tag: TYPE_LABELS[condition.type],
        defaultIncubationRounds: condition.defaultIncubationRounds,
        defaultDurationRounds: condition.defaultDurationRounds,
        defaultFrequencyRounds: condition.defaultFrequencyRounds,
        defaultSuccessesRequired: condition.defaultSuccessesRequired,
      });
    }

    return entries;
  }, [
    conditionsCatalog,
    activatableSpells,
    activatableClassAbilities,
    activatableFeats,
    externalClassAbilities,
    search,
    typeFilter,
  ]);

  return (
    <Panel
      title="Effekte"
      hint={hint}
      id="effectsPanel"
      beforeBody={
        <div className="time-controls">
          <span className="time-label">Zeit vergeht</span>
          <div className="time-btn-group">
            {TIME_BUTTONS.map((btn) => (
              <button
                key={btn.unit}
                type="button"
                className={`time-btn${btn.className ? ` ${btn.className}` : ''}`}
                onClick={() => onAdvanceTime(btn.unit)}
              >
                {btn.label}
              </button>
            ))}
          </div>
        </div>
      }
    >
      <div className="section-label">Aktive Effekte</div>
      {activeEffects.length === 0 && <p className="effect-empty-hint">Keine aktiven Effekte.</p>}
      <div className="seal-grid">
        {activeEffects.map((effect) => (
          <ActiveEffectSeal key={effect.id} effect={effect} onRemove={onRemove} onSaveResult={onSaveResult} />
        ))}
      </div>

      <div className="section-label">Verfügbare Zustände, Gifte, Krankheiten &amp; mehr</div>
      <div className="effect-filter-row">
        <input
          type="text"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Effekte durchsuchen …"
        />
        <select value={typeFilter} onChange={(e) => onTypeFilterChange(e.target.value as ConditionType | '')}>
          <option value="">Alle</option>
          <option value="condition">Zustände</option>
          <option value="poison">Gifte</option>
          <option value="disease">Krankheiten</option>
        </select>
      </div>
      <div className="seal-grid">
        {availableEntries.map((entry) => (
          <AvailableEffectSeal key={entry.domId} entry={entry} onPick={onPick} />
        ))}
      </div>
      {availableEntries.length === 0 && <p className="effect-empty-hint">Keine Treffer.</p>}
    </Panel>
  );
}
