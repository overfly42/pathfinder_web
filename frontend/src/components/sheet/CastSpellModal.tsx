/** Confirmation popup for casting a prepared spell from the "Zauber" cast bar (`SheetTabs.tsx`) —
 *  shows components and the spell's full description before actually consuming a prepared copy,
 *  same "confirm before spending a resource" shape as `UseAbilityModal`. */
interface CastSpellEntry {
  name: string;
  description: string;
  components: string;
  range: string | null;
  savingThrow: string | null;
  remaining: number;
  preparedCount: number;
}

interface CastSpellModalProps {
  entry: CastSpellEntry | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export function CastSpellModal({ entry, onCancel, onConfirm }: CastSpellModalProps) {
  return (
    <div
      className={`modal-overlay${entry ? ' open' : ''}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{entry?.name ?? 'Zauber'}</h2>
          <button type="button" className="modal-close" onClick={onCancel}>✕</button>
        </div>
        <div className="modal-body">
          <p><strong>Komponenten:</strong> {entry?.components}</p>
          <p><strong>Reichweite:</strong> {entry?.range ?? '—'}</p>
          <p><strong>Rettungswurf:</strong> {entry?.savingThrow ?? '—'}</p>
          <p>{entry?.description}</p>
          <p>{entry?.remaining} von {entry?.preparedCount} heute noch verfügbar.</p>
        </div>
        <div className="modal-foot">
          <button type="button" className="hp-btn ghost" onClick={onCancel}>Abbrechen</button>
          <button type="button" className="hp-btn confirm" onClick={onConfirm}>Wirken</button>
        </div>
      </div>
    </div>
  );
}
