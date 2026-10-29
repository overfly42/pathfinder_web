import { useEffect, useState } from 'react';
import type { EffectOption, EffectSourceType } from '../../types/character';
import { ROUNDS_PER_UNIT, TIME_UNIT_LABELS, roundsToUnitValue, type TimeUnit } from '../../lib/time';

/** One entry from the effects panel's "available" list (spell/class ability/condition) that the
 *  player picked to activate. `default*` fields are set for `sourceType === 'condition'` from
 *  `ConditionCatalogEntry`, and for a class ability/feat with its own catalog-side
 *  `defaultDurationRounds` (e.g. Kampfmagus's Arkaner Vorrat, Mystiker's Luftbarriere) —
 *  `RealEffectsPanel.tsx` is what actually threads either source into this shared shape.
 *  `durationRoundsPerLevel` (spells only, e.g. Magierrüstung's 600 = "1 Stunde/Stufe") is the
 *  per-level counterpart: a flat `defaultDurationRounds` can't represent a duration that scales
 *  with whatever caster level the player enters in this same form, so the modal recomputes
 *  `duration` live from `level * durationRoundsPerLevel` instead of seeding it once. */
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
  durationRoundsPerLevel?: number | null;
  /** A "pick N of these" ability (e.g. Tieraspekt) — the modal shows `optionLimit` pickers. */
  options?: EffectOption[];
  optionLimit?: number;
}

export interface ActivateEffectInput {
  sourceType: EffectSourceType;
  sourceId: string;
  level: number | null;
  incubationRemaining: number | null;
  durationRemaining: number | null;
  frequencyRounds: number | null;
  successesRequired: number | null;
  targetItemId: string | null;
  optionIds: string[];
}

/** One entry in the target-item picker — only the fields the dropdown needs, not the full
 *  `GearItem` (keeps this modal decoupled from the rest of that type's shape). */
export interface TargetItemOption {
  id: string;
  name: string;
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
  /** This character's current gear, for the optional target-item picker (e.g. Kampfmagus's
   *  Arkaner Vorrat, which buffs one specific held weapon) — shown for every activation
   *  regardless of `sourceType`, same "generic field, irrelevant ones just leave it empty"
   *  convention the level/duration/incubation/frequency/successes fields above already use. */
  gear: TargetItemOption[];
  onCancel: () => void;
  onActivate: (input: ActivateEffectInput) => void;
}

export function ActivateEffectModal({ entry, characterLevel, gear, onCancel, onActivate }: ActivateEffectModalProps) {
  const [level, setLevel] = useState('');
  const [duration, setDuration] = useState<UnitField>(EMPTY_FIELD);
  const [incubation, setIncubation] = useState<UnitField>(EMPTY_FIELD);
  const [frequency, setFrequency] = useState<UnitField>(EMPTY_FIELD);
  const [successesRequired, setSuccessesRequired] = useState('');
  const [targetItemId, setTargetItemId] = useState('');
  // One slot per pickable option (`optionLimit`); the first must be filled, the rest may stay empty.
  const [optionPicks, setOptionPicks] = useState<string[]>([]);
  const options = entry?.options ?? [];
  const optionSlots = options.length > 0 ? Math.max(1, entry?.optionLimit ?? 1) : 0;

  // Re-seed every field from this entry's defaults whenever a (different) entry is opened —
  // spells/class abilities default their level to the character's current level (the usual
  // caster-level stand-in), conditions/poisons/diseases have no level concept and default the
  // duration/incubation/frequency/successes fields from the catalog's parsed defaults instead.
  // A `durationRoundsPerLevel` entry (a "X/Stufe" spell) seeds duration from *this* initial level
  // instead of `defaultDurationRounds` — see `handleLevelChange` for what keeps it in sync
  // afterwards as the player edits the level field.
  useEffect(() => {
    if (!entry) return;
    const initialLevel = entry.sourceType === 'condition' ? '' : String(characterLevel);
    setLevel(initialLevel);
    setDuration(
      entry.durationRoundsPerLevel != null
        ? fieldFromRounds(entry.durationRoundsPerLevel * characterLevel)
        : fieldFromRounds(entry.defaultDurationRounds)
    );
    setIncubation(fieldFromRounds(entry.defaultIncubationRounds));
    setFrequency(fieldFromRounds(entry.defaultFrequencyRounds));
    setSuccessesRequired(entry.defaultSuccessesRequired != null ? String(entry.defaultSuccessesRequired) : '');
    setTargetItemId('');
    setOptionPicks([]);
  }, [entry, characterLevel]);

  // For a `durationRoundsPerLevel` entry, typing a new level recomputes the duration field to
  // match (still overridable afterwards — editing duration itself doesn't get overwritten again
  // unless the level field changes once more). Ignored for every other entry, and for a level
  // field the player has cleared or left non-numeric.
  function handleLevelChange(value: string) {
    setLevel(value);
    if (entry?.durationRoundsPerLevel == null) return;
    const parsedLevel = parseInt(value, 10);
    if (Number.isFinite(parsedLevel) && parsedLevel >= 0) {
      setDuration(fieldFromRounds(entry.durationRoundsPerLevel * parsedLevel));
    }
  }

  function handleOptionChange(slot: number, key: string) {
    setOptionPicks((prev) => {
      const next = [...prev];
      next[slot] = key;
      return next;
    });
  }

  const pickedOptionIds = [...new Set(optionPicks.filter(Boolean))];
  const missingOption = optionSlots > 0 && pickedOptionIds.length === 0;

  function handleActivate() {
    if (!entry || missingOption) return;
    const parsedLevel = parseInt(level, 10);
    onActivate({
      sourceType: entry.sourceType,
      sourceId: entry.sourceId,
      level: level.trim() && Number.isFinite(parsedLevel) ? parsedLevel : null,
      incubationRemaining: fieldToRounds(incubation),
      durationRemaining: fieldToRounds(duration),
      frequencyRounds: fieldToRounds(frequency),
      successesRequired: successesRequired.trim() ? parseInt(successesRequired, 10) || null : null,
      targetItemId: targetItemId || null,
      optionIds: pickedOptionIds,
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
          {Array.from({ length: optionSlots }, (_, slot) => {
            const picked = options.find((option) => option.key === optionPicks[slot]);
            return (
              <div className="activate-effect-field" key={slot}>
                <div className="detail-label">
                  {optionSlots > 1 ? `Auswahl ${slot + 1}${slot > 0 ? ' (optional)' : ''}` : 'Auswahl'}
                </div>
                <div className="activate-effect-value-row">
                  <select
                    className="activate-effect-option"
                    value={optionPicks[slot] ?? ''}
                    onChange={(e) => handleOptionChange(slot, e.target.value)}
                  >
                    <option value="">— wählen —</option>
                    {options.map((option) => (
                      <option
                        key={option.key}
                        value={option.key}
                        disabled={optionPicks.some((key, other) => other !== slot && key === option.key)}
                      >
                        {option.name}
                        {option.hasHandler ? '' : ' (nur Text)'}
                      </option>
                    ))}
                  </select>
                </div>
                {picked && (
                  <div className="activate-effect-option-text">
                    {picked.description.replace(/^\(..\) [^:]*: /, '')}
                    {picked.partialNote && <em> Nicht berechnet: {picked.partialNote}</em>}
                  </div>
                )}
              </div>
            );
          })}
          <div className="activate-effect-field">
            <div className="detail-label">Stufe</div>
            <div className="activate-effect-value-row">
              <input type="number" min={0} value={level} onChange={(e) => handleLevelChange(e.target.value)} />
            </div>
          </div>
          <UnitValueField label="Dauer" field={duration} onChange={setDuration} />
          <UnitValueField label="Inkubation" field={incubation} onChange={setIncubation} />
          <UnitValueField label="Frequenz" field={frequency} onChange={setFrequency} />
          {gear.length > 0 && (
            <div className="activate-effect-field">
              <div className="detail-label">Zielgegenstand (optional)</div>
              <div className="activate-effect-value-row">
                <select value={targetItemId} onChange={(e) => setTargetItemId(e.target.value)}>
                  <option value="">— keine —</option>
                  {gear.map((item) => (
                    <option key={item.id} value={item.id}>{item.name}</option>
                  ))}
                </select>
              </div>
            </div>
          )}
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
          <button type="button" className="hp-btn confirm" onClick={handleActivate} disabled={missingOption}>
            Aktivieren
          </button>
        </div>
      </div>
    </div>
  );
}
