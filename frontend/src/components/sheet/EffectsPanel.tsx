import type { Effect } from '../../types/character';
import { Panel, PanelSearch } from '../primitives/Panel';

export type TimeUnit = 'round' | 'minute' | 'hour' | 'day';

interface EffectsPanelProps {
  effectsActive: Effect[];
  effectsAvailable: Effect[];
  onAdvanceTime: (unit: TimeUnit) => void;
}

function ActiveSeal({ effect }: { effect: Effect }) {
  return (
    <div className="seal" id={`effect-active-${effect.id}`}>
      <div className={`seal-blob ${effect.variant}`}>
        <div className="glyph">{effect.icon}</div>
        <div className="amount">{effect.amount}</div>
      </div>
      <div className="seal-name">
        {effect.name}
        <br />
        {effect.detail}
      </div>
      <div className="seal-ribbon">{effect.durationLabel}</div>
    </div>
  );
}

function AvailableSeal({ effect }: { effect: Effect }) {
  return (
    <div className="seal inactive" id={`effect-available-${effect.id}`}>
      <div className="seal-blob inactive">
        <div className="glyph">{effect.icon}</div>
        <div className="amount">{effect.amount}</div>
      </div>
      <div className="seal-name">
        {effect.name}
        <br />
        {effect.detail}
      </div>
      <div className="seal-ribbon inactive">{effect.durationLabel}</div>
    </div>
  );
}

const TIME_BUTTONS: { unit: TimeUnit; label: string; className?: string }[] = [
  { unit: 'round', label: '+1 Runde' },
  { unit: 'minute', label: '+1 Minute' },
  { unit: 'hour', label: '+1 Stunde' },
  { unit: 'day', label: '+1 Tag', className: 'day' },
];

export function EffectsPanel({ effectsActive, effectsAvailable, onAdvanceTime }: EffectsPanelProps) {
  const hint = `${effectsActive.length} aktiv · ${effectsAvailable.length} verfügbar`;

  return (
    <Panel
      title="Effekte"
      hint={hint}
      id="effectsPanel"
      beforeBody={
        <>
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
          <PanelSearch placeholder="Effekte durchsuchen" />
        </>
      }
    >
      <div className="section-label">Aktive Effekte</div>
      <div className="seal-grid">
        {effectsActive.map((effect) => (
          <ActiveSeal effect={effect} key={effect.id} />
        ))}
      </div>

      <div className="section-label">Verfügbare Zustände &amp; Zauber</div>
      <div className="seal-grid">
        {effectsAvailable.map((effect) => (
          <AvailableSeal effect={effect} key={effect.id} />
        ))}
      </div>
    </Panel>
  );
}
