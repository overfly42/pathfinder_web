import { useEffect, useState } from 'react';
import type { EffectSourceType } from '../../types/character';
import { ROUNDS_PER_UNIT, TIME_UNIT_LABELS, roundsToUnitValue, type TimeUnit } from '../../lib/time';

/** One entry from the effects panel's "available" list (spell/class ability/condition) that the
 *  player picked to activate. `default*` fields are only ever set for `sourceType === 'condition'`
 *  — spells/class abilities have no catalog-side defaults to pre-fill from (see `ConditionCatalogEntry`). */
export interface AvailableEntry {
  domId: string;
  sourceType: EffectSourceType;
  sourceId: string;
  name: string;
  description?: string;
  icon: string;
  tag: string;
  defaultIncubationRounds?: number | null;
  defaultDurationRounds?: number | null;
  defaultFrequencyRounds?: number | null;
  defaultSuccessesRequired?: number | null;
}

export interface ActivateEffectInput {
  sourceType: EffectSourceType;
  sourceId: string;
  level: number | null;
  incubationRemaining: number | null;
  durationRemaining: number | null;
  frequencyRounds: number | null;
  successesRequired: number | null;
}

interface UnitField {
  value: string;
  unit: TimeUnit;
}

const EMPTY_FIELD: UnitField = { value: '', unit: 'round' };

function fieldFromRounds(rounds: number | null | undefined): UnitField {
  if (rounds == null) return EMPTY_FIELD;
  const { value, unit } = roundsToUnitValue(rounds);
  return { value: String(value), unit };
}

function fieldToRounds(field: UnitField): number | null {
  if (!field.value.trim()) return null;
  const parsed = parseInt(field.value, 10);
  return Number.isFinite(parsed) ? parsed * ROUNDS_PER_UNIT[field.unit] : null;
}

interface UnitValueFieldProps {
  label: string;
  field: UnitField;
  onChange: (field: UnitField) => void;
}

function UnitValueField({ label, field, onChange }: UnitValueFieldProps) {
  return (
    <div className="activate-effect-field">
      <div className="detail-label">{label}</div>
      <div className="activate-effect-value-row">
        <input
          type="number"
          min={0}
          value={field.value}
          onChange={(e) => onChange({ ...field, value: e.target.value })}
        />
        <select value={field.unit} onChange={(e) => onChange({ ...field, unit: e.target.value as TimeUnit })}>
          {(Object.entries(TIME_UNIT_LABELS) as [TimeUnit, string][]).map(([unit, unitLabel]) => (
            <option key={unit} value={unit}>{unitLabel}</option>
          ))}
        </select>
      </div>
    </div>
  );
}

interface ActivateEffectModalProps {
  entry: AvailableEntry | null;
  characterLevel: number;
  onCancel: () => void;
  onActivate: (input: ActivateEffectInput) => void;
}

export function ActivateEffectModal({ entry, characterLevel, onCancel, onActivate }: ActivateEffectModalProps) {
  const [level, setLevel] = useState('');
  const [duration, setDuration] = useState<UnitField>(EMPTY_FIELD);
  const [incubation, setIncubation] = useState<UnitField>(EMPTY_FIELD);
  const [frequency, setFrequency] = useState<UnitField>(EMPTY_FIELD);
  const [successesRequired, setSuccessesRequired] = useState('');

  // Re-seed every field from this entry's defaults whenever a (different) entry is opened —
  // spells/class abilities default their level to the character's current level (the usual
  // caster-level stand-in), conditions/poisons/diseases have no level concept and default the
  // duration/incubation/frequency/successes fields from the catalog's parsed defaults instead.
  useEffect(() => {
    if (!entry) return;
    setLevel(entry.sourceType === 'condition' ? '' : String(characterLevel));
    setDuration(fieldFromRounds(entry.defaultDurationRounds));
    setIncubation(fieldFromRounds(entry.defaultIncubationRounds));
    setFrequency(fieldFromRounds(entry.defaultFrequencyRounds));
    setSuccessesRequired(entry.defaultSuccessesRequired != null ? String(entry.defaultSuccessesRequired) : '');
  }, [entry, characterLevel]);

  function handleActivate() {
    if (!entry) return;
    const parsedLevel = parseInt(level, 10);
    onActivate({
      sourceType: entry.sourceType,
      sourceId: entry.sourceId,
      level: level.trim() && Number.isFinite(parsedLevel) ? parsedLevel : null,
      incubationRemaining: fieldToRounds(incubation),
      durationRemaining: fieldToRounds(duration),
      frequencyRounds: fieldToRounds(frequency),
      successesRequired: successesRequired.trim() ? parseInt(successesRequired, 10) || null : null,
    });
  }

  return (
    <div
      className={`modal-overlay${entry ? ' open' : ''}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{entry?.name ?? 'Effekt'} aktivieren</h2>
          <button type="button" className="modal-close" onClick={onCancel}>✕</button>
        </div>
        <div className="modal-body">
          <div className="activate-effect-field">
            <div className="detail-label">Stufe</div>
            <div className="activate-effect-value-row">
              <input type="number" min={0} value={level} onChange={(e) => setLevel(e.target.value)} />
            </div>
          </div>
          <UnitValueField label="Dauer" field={duration} onChange={setDuration} />
          <UnitValueField label="Inkubation" field={incubation} onChange={setIncubation} />
          <UnitValueField label="Frequenz" field={frequency} onChange={setFrequency} />
          <div className="activate-effect-field">
            <div className="detail-label">Erfolge benötigt</div>
            <div className="activate-effect-value-row">
              <input
                type="number"
                min={0}
                value={successesRequired}
                onChange={(e) => setSuccessesRequired(e.target.value)}
              />
            </div>
          </div>
        </div>
        <div className="modal-foot">
          <button type="button" className="hp-btn ghost" onClick={onCancel}>Abbrechen</button>
          <button type="button" className="hp-btn confirm" onClick={handleActivate}>Aktivieren</button>
        </div>
      </div>
    </div>
  );
}
