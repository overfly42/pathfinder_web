import { useState } from 'react';
import type { Character } from '../../types/character';
import { useClickOutside } from '../../hooks/useClickOutside';

interface VitalsBarProps {
  character: Character;
  onApplyHp: (signedAmount: number) => void;
}

export function VitalsBar({ character, onApplyHp }: VitalsBarProps) {
  const [open, setOpen] = useState(false);
  const [delta, setDelta] = useState('');
  const popoverRef = useClickOutside<HTMLDivElement>(() => setOpen(false));

  const damage = character.hp.max - character.hp.current;
  const percent = Math.max(0, Math.min(100, Math.round((character.hp.current / character.hp.max) * 100)));

  function apply(sign: 1 | -1) {
    const amount = parseInt(delta, 10);
    if (!amount || amount <= 0) return;
    onApplyHp(sign * amount);
    setDelta('');
    setOpen(false);
  }

  return (
    <div className="vitals">
      <div className="vital hp" ref={popoverRef}>
        <div className="k">Schaden</div>
        <div className="v" role="button" tabIndex={0} onClick={() => setOpen((o) => !o)}>
          {damage} / {character.hp.max}
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
          </div>
        )}
        <div className="bar"><span style={{ width: `${percent}%` }} /></div>
      </div>
      <div className="vital">
        <div className="k">Rüstungsklasse</div>
        <div className="v">{character.armorClass}</div>
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
