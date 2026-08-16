import { useState } from 'react';
import { formatBreakdown } from '../../lib/breakdown';
import type { Character } from '../../types/character';
import { useClickOutside } from '../../hooks/useClickOutside';

interface VitalsBarProps {
  character: Character;
  onApplyHp: (signedAmount: number) => void;
  onSetTempHp: (amount: number) => void;
}

export function VitalsBar({ character, onApplyHp, onSetTempHp }: VitalsBarProps) {
  const [open, setOpen] = useState(false);
  const [delta, setDelta] = useState('');
  const [tempInput, setTempInput] = useState('');
  const popoverRef = useClickOutside<HTMLDivElement>(() => setOpen(false));

  const percent = Math.max(0, Math.min(100, Math.round((character.hp.current / character.hp.max) * 100)));

  function apply(sign: 1 | -1) {
    const amount = parseInt(delta, 10);
    if (!amount || amount <= 0) return;
    onApplyHp(sign * amount);
    setDelta('');
    setOpen(false);
  }

  function setTemp() {
    const amount = parseInt(tempInput, 10);
    if (!Number.isFinite(amount) || amount < 0) return;
    onSetTempHp(amount);
    setTempInput('');
    setOpen(false);
  }

  return (
    <div className="vitals">
      <div className="vital hp" ref={popoverRef}>
        <div className="k">Trefferpunkte</div>
        <div className="v" role="button" tabIndex={0} onClick={() => setOpen((o) => !o)}>
          {character.hp.current} / {character.hp.max}
          {character.hp.temporary > 0 && <span className="hp-temp"> (+{character.hp.temporary} temp.)</span>}
        </div>
        {open && (
          <div className="hp-popover-body">
            <input
              type="number"
              min={1}
              inputMode="numeric"
              placeholder="Betrag"
              value={delta}
              onChange={(e) => setDelta(e.target.value)}
            />
            <div className="hp-popover-actions">
              <button type="button" className="hp-btn dmg" onClick={() => apply(-1)}>Schaden</button>
              <button type="button" className="hp-btn heal" onClick={() => apply(1)}>Heilen</button>
            </div>
            <input
              type="number"
              min={0}
              inputMode="numeric"
              placeholder="Temporäre TP"
              value={tempInput}
              onChange={(e) => setTempInput(e.target.value)}
            />
            <div className="hp-popover-actions">
              <button type="button" className="hp-btn confirm" onClick={setTemp}>Temp-TP setzen</button>
            </div>
          </div>
        )}
        <div className="bar"><span style={{ width: `${percent}%` }} /></div>
      </div>
      <div className="vital">
        <div className="k">Rüstungsklasse</div>
        <div className="v" title={formatBreakdown(character.armorClassBreakdown)}>
          {character.armorClass}
        </div>
      </div>
      <div className="vital">
        <div className="k">Initiative</div>
        <div className="v">{character.initiative}</div>
      </div>
      <div className="vital">
        <div className="k">Bewegung</div>
        <div className="v">{character.speed}</div>
      </div>
    </div>
  );
}
