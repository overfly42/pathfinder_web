import { useMemo, useState } from 'react';
import type {
  ActivatableRef,
  ActiveEffect,
  ConditionCatalogEntry,
  ConditionType,
  EffectSourceType,
} from '../../types/character';
import { CONDITION_TYPE_ICONS, SOURCE_TYPE_ICONS, iconForActiveEffect } from '../../lib/effectIcons';
import { Panel } from '../primitives/Panel';
import type { TimeUnit } from './EffectsPanel';

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

export interface ActivateEffectInput {
  sourceType: EffectSourceType;
  sourceId: string;
  level: number | null;
  incubationRemaining: number | null;
  durationRemaining: number | null;
  frequencyRounds: number | null;
  successesRequired: number | null;
}

interface ActiveEffectSealProps {
  effect: ActiveEffect;
  onRemove: (effectId: string) => void;
  onSaveResult: (effectId: string, success: boolean) => void;
}

function ActiveEffectSeal({ effect, onRemove, onSaveResult }: ActiveEffectSealProps) {
  const isFrequencyTracked = effect.frequencyRounds != null;

  let ribbon: string;
  if (isFrequencyTracked) {
    ribbon = `Rettungswurf in ${effect.nextCheckIn ?? 0} ${effect.nextCheckIn === 1 ? 'Rd.' : 'Rd.'}`;
  } else if (effect.durationRemaining != null) {
    ribbon = `${effect.durationRemaining} ${effect.durationRemaining === 1 ? 'Runde' : 'Runden'}`;
  } else if (effect.incubationRemaining != null) {
    ribbon = `Inkubation ${effect.incubationRemaining}`;
  } else {
    ribbon = 'bis Entfernen';
  }

  return (
    <div className="seal" id={`effect-active-${effect.id}`}>
      <button type="button" className="seal-remove" title="Entfernen" onClick={() => onRemove(effect.id)}>✕</button>
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

interface AvailableEntry {
  domId: string;
  sourceType: EffectSourceType;
  sourceId: string;
  name: string;
  description?: string;
  icon: string;
  tag: string;
}

interface AvailableEffectSealProps {
  entry: AvailableEntry;
  onPick: (entry: AvailableEntry) => void;
}

function AvailableEffectSeal({ entry, onPick }: AvailableEffectSealProps) {
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
    </button>
  );
}

function toNumberOrNull(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

interface ActivateFieldsProps {
  picked: AvailableEntry;
  onCancel: () => void;
  onActivate: (input: ActivateEffectInput) => void;
}

function ActivateFields({ picked, onCancel, onActivate }: ActivateFieldsProps) {
  const [level, setLevel] = useState('');
  const [duration, setDuration] = useState('');
  const [incubation, setIncubation] = useState('');
  const [frequency, setFrequency] = useState('');
  const [successesRequired, setSuccessesRequired] = useState('');

  function handleActivate() {
    onActivate({
      sourceType: picked.sourceType,
      sourceId: picked.sourceId,
      level: toNumberOrNull(level),
      incubationRemaining: toNumberOrNull(incubation),
      durationRemaining: toNumberOrNull(duration),
      frequencyRounds: toNumberOrNull(frequency),
      successesRequired: toNumberOrNull(successesRequired),
    });
  }

  return (
    <div className="effect-activate-inline">
      <div className="effect-activate-inline-title">{picked.name} aktivieren</div>
      <div className="effect-activate-inline-fields">
        <input type="number" min={0} value={level} onChange={(e) => setLevel(e.target.value)} placeholder="Stufe" />
        <input type="number" min={0} value={duration} onChange={(e) => setDuration(e.target.value)} placeholder="Dauer (Runden)" />
        <input type="number" min={0} value={incubation} onChange={(e) => setIncubation(e.target.value)} placeholder="Inkubation (Runden)" />
        <input type="number" min={0} value={frequency} onChange={(e) => setFrequency(e.target.value)} placeholder="Frequenz (Runden)" />
        <input
          type="number"
          min={0}
          value={successesRequired}
          onChange={(e) => setSuccessesRequired(e.target.value)}
          placeholder="Erfolge benötigt"
        />
      </div>
      <div className="hp-popover-actions">
        <button type="button" className="hp-btn ghost" onClick={onCancel}>Abbrechen</button>
        <button type="button" className="hp-btn confirm" onClick={handleActivate}>Aktivieren</button>
      </div>
    </div>
  );
}

interface RealEffectsPanelProps {
  activeEffects: ActiveEffect[];
  conditionsCatalog: ConditionCatalogEntry[];
  activatableSpells: ActivatableRef[];
  activatableClassAbilities: ActivatableRef[];
  search: string;
  onSearchChange: (value: string) => void;
  typeFilter: ConditionType | '';
  onTypeFilterChange: (value: ConditionType | '') => void;
  onAdvanceTime: (unit: TimeUnit) => void;
  onActivate: (input: ActivateEffectInput) => void;
  onRemove: (effectId: string) => void;
  onSaveResult: (effectId: string, success: boolean) => void;
}

export function RealEffectsPanel({
  activeEffects,
  conditionsCatalog,
  activatableSpells,
  activatableClassAbilities,
  search,
  onSearchChange,
  typeFilter,
  onTypeFilterChange,
  onAdvanceTime,
  onActivate,
  onRemove,
  onSaveResult,
}: RealEffectsPanelProps) {
  const [picked, setPicked] = useState<AvailableEntry | null>(null);
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
      for (const ability of activatableClassAbilities) {
        if (term && !ability.name.toLowerCase().includes(term)) continue;
        entries.push({
          domId: `activatable-ability-${ability.key}`,
          sourceType: 'class_ability',
          sourceId: ability.key,
          name: ability.name,
          icon: SOURCE_TYPE_ICONS.class_ability,
          tag: 'Klassenfähigkeit',
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
      });
    }

    return entries;
  }, [conditionsCatalog, activatableSpells, activatableClassAbilities, search, typeFilter]);

  function handleActivate(input: ActivateEffectInput) {
    onActivate(input);
    setPicked(null);
  }

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
          <AvailableEffectSeal key={entry.domId} entry={entry} onPick={setPicked} />
        ))}
      </div>
      {availableEntries.length === 0 && <p className="effect-empty-hint">Keine Treffer.</p>}

      {picked && <ActivateFields picked={picked} onCancel={() => setPicked(null)} onActivate={handleActivate} />}
    </Panel>
  );
}
