/** Confirmation popup for restoring an already-cast spell via a Perle der Macht
 *  (`SheetTabs.tsx`'s spell chips — tapping a used chip when a matching-grade pearl still has a
 *  use left routes here instead of `CastSpellModal`) — same "confirm before spending a resource"
 *  shape as `UseAbilityModal`, sized for this narrower action (no components/range/save block,
 *  the spell is already known to the player from having cast it once today). */
interface RestoreSpellEntry {
  name: string;
  pearlsAvailable: number;
  pearlsTotal: number;
}

interface RestoreSpellModalProps {
  entry: RestoreSpellEntry | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export function RestoreSpellModal({ entry, onCancel, onConfirm }: RestoreSpellModalProps) {
  return (
    <div
      className={`modal-overlay${entry ? ' open' : ''}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{entry?.name ?? 'Zauber'} zurückrufen</h2>
          <button type="button" className="modal-close" onClick={onCancel}>✕</button>
        </div>
        <div className="modal-body">
          <p>
            Eine Perle der Macht ruft den bereits gewirkten Zauber wieder ins Gedächtnis — er gilt
            danach wieder als vorbereitet, als sei er noch nicht gewirkt worden.
          </p>
          <p>{entry?.pearlsAvailable} von {entry?.pearlsTotal} Perlen heute noch verfügbar.</p>
        </div>
        <div className="modal-foot">
          <button type="button" className="hp-btn ghost" onClick={onCancel}>Abbrechen</button>
          <button type="button" className="hp-btn confirm" onClick={onConfirm}>Zurückrufen</button>
        </div>
      </div>
    </div>
  );
}
