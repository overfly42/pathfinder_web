import { useRef, useState } from 'react';
import type { Effect, EffectDef } from '../../types/character';
import { Panel, PanelSearch } from '../primitives/Panel';

export type TimeUnit = 'round' | 'minute' | 'hour' | 'day';

interface EffectsPanelProps {
  effectsActive: Effect[];
  effectsAvailable: EffectDef[];
  onAdvanceTime: (unit: TimeUnit) => void;
  onShortRest: () => void;
  onActivateEffect: (defId: string) => void;
  onRemoveEffect: (effectId: string) => void;
  onAddCustomEffect: (name: string, rounds: number | null) => void;
}

function ActiveSeal({ effect, onRemove }: { effect: Effect; onRemove: (id: string) => void }) {
  return (
    <div className="seal" id={`effect-active-${effect.id}`}>
      <button type="button" className="seal-remove" title="Entfernen" onClick={() => onRemove(effect.id)}>✕</button>
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

function AvailableSeal({ effect, onActivate }: { effect: EffectDef; onActivate: (id: string) => void }) {
  return (
    <button type="button" className="seal inactive" id={`effect-available-${effect.id}`} onClick={() => onActivate(effect.id)}>
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
    </button>
  );
}

function CustomEffectForm({ onAdd }: { onAdd: (name: string, rounds: number | null) => void }) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  const [name, setName] = useState('');
  const [rounds, setRounds] = useState('');

  function handleAdd() {
    const trimmed = name.trim();
    if (!trimmed) return;
    const parsed = rounds.trim() ? parseInt(rounds, 10) : null;
    onAdd(trimmed, Number.isFinite(parsed) ? parsed : null);
    setName('');
    setRounds('');
    detailsRef.current?.removeAttribute('open');
  }

  return (
    <details className="gear-add" ref={detailsRef}>
      <summary className="gear-add-btn">+ Eigener Zustand</summary>
      <div className="hp-popover-body gear-form">
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Bezeichnung" />
        <input
          type="number"
          min={1}
          value={rounds}
          onChange={(e) => setRounds(e.target.value)}
          placeholder="Dauer in Runden (leer = bis Rast)"
        />
        <div className="hp-popover-actions">
          <button type="button" className="hp-btn confirm" onClick={handleAdd}>Hinzufügen</button>
        </div>
      </div>
    </details>
  );
}

const TIME_BUTTONS: { unit: TimeUnit; label: string; className?: string }[] = [
  { unit: 'round', label: '+1 Runde' },
  { unit: 'minute', label: '+1 Minute' },
  { unit: 'hour', label: '+1 Stunde' },
  { unit: 'day', label: '+1 Tag', className: 'day' },
];

export function EffectsPanel({
  effectsActive,
  effectsAvailable,
  onAdvanceTime,
  onShortRest,
  onActivateEffect,
  onRemoveEffect,
  onAddCustomEffect,
}: EffectsPanelProps) {
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
              <button type="button" className="time-btn rest" onClick={onShortRest}>Kurze Rast</button>
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
          <ActiveSeal effect={effect} key={effect.id} onRemove={onRemoveEffect} />
        ))}
      </div>

      <div className="section-label">Verfügbare Zustände &amp; Zauber</div>
      <div className="seal-grid">
        {effectsAvailable.map((effect) => (
          <AvailableSeal effect={effect} key={effect.id} onActivate={onActivateEffect} />
        ))}
      </div>

      <CustomEffectForm onAdd={onAddCustomEffect} />
    </Panel>
  );
}
