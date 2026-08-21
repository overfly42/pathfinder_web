/** Confirmation popup for a discrete once-a-day class ability with no duration to track as an
 *  active effect (`ActionOption.usesRemainingToday`, e.g. Erneuerte Lebenskraft) — shows the full
 *  rules text (what the player needs to do, e.g. roll dice and apply the result by hand, same
 *  "this app never rolls dice" convention as weapon/natural-attack damage) and, on confirm, spends
 *  one of today's uses via `PATCH .../class-abilities/{id}/use`. Deliberately simpler than
 *  `ActivateEffectModal` (no duration/level fields to ask for — a one-shot action has none). */
interface UseAbilityEntry {
  sourceId: string;
  name: string;
  description: string;
  icon: string;
  usesRemainingToday: number;
  usesPerDay: number;
}

interface UseAbilityModalProps {
  entry: UseAbilityEntry | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export function UseAbilityModal({ entry, onCancel, onConfirm }: UseAbilityModalProps) {
  return (
    <div
      className={`modal-overlay${entry ? ' open' : ''}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{entry?.icon} {entry?.name ?? 'Fähigkeit'}</h2>
          <button type="button" className="modal-close" onClick={onCancel}>✕</button>
        </div>
        <div className="modal-body">
          <p>{entry?.description}</p>
          <p>
            {entry?.usesRemainingToday} von {entry?.usesPerDay} Anwendungen heute übrig. Würfelergebnis bitte
            selbst über die Trefferpunkte-Anpassung eintragen.
          </p>
        </div>
        <div className="modal-foot">
          <button type="button" className="hp-btn ghost" onClick={onCancel}>Abbrechen</button>
          <button type="button" className="hp-btn confirm" onClick={onConfirm}>Einsetzen</button>
        </div>
      </div>
    </div>
  );
}
