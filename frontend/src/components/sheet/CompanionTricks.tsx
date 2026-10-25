import { useEffect, useState } from 'react';
import { apiGet, apiPut } from '../../api/client';
import type { Character, CompanionInfo, TrickCatalog } from '../../types/character';
import { TRICK_HELP } from '../../lib/companionLevels';

type Source = 'bonus' | 'trained';
type Limits = NonNullable<CompanionInfo['trickLimits']>;

/** "Bonustricks 1/2 · Abgerichtet 4/6" */
function formatLimits(bonusUsed: number, trainedUsed: number, limits: Limits): string {
  const trainedMax = limits.trained.max == null ? 'unbegrenzt' : limits.trained.max;
  return `Bonustricks ${bonusUsed}/${limits.bonus.max} · Abgerichtet ${trainedUsed}/${trainedMax}`;
}

/** An animal companion's known tricks (roadmap slice 10 step 5): badges per pool, counters, the
 *  training (Aufgabe) and an edit dialog. Nothing for a familiar (`trickLimits` is `null`). */
export function CompanionTricks({ character, onChanged }: { character: Character; onChanged: () => void }) {
  const info = character.companion;
  const [editing, setEditing] = useState(false);
  if (!info || !info.trickLimits) return null;
  const limits = info.trickLimits;
  const openBonus = limits.bonus.max - limits.bonus.used;
  return (
    <div className="companion-tricks">
      <div className="companion-tricks-head">
        <strong>Tricks</strong>
        <span>{formatLimits(limits.bonus.used, limits.trained.used, limits)}</span>
        {info.trickPurpose && <span>· Aufgabe: {info.trickPurpose.name}</span>}
        <button type="button" className="companion-link" onClick={() => setEditing(true)}>
          Bearbeiten
        </button>
      </div>
      {openBonus > 0 && <p className="companion-open">{openBonus} Bonustrick{openBonus === 1 ? '' : 's'} offen</p>}
      {limits.overLimit && (
        <p className="companion-warning">
          Zu viele Tricks für das aktuelle Limit (IN {limits.intelligence}) — die Tricks bleiben erhalten.
        </p>
      )}
      {info.tricks.length > 0 && (
        <ul className="companion-trick-list">
          {info.tricks.map((trick) => (
            <li key={trick.id} title={trick.description}>
              {trick.name} <span className="desc">(SG {trick.dc})</span>{' '}
              <span className={`trick-badge ${trick.source}`}>{trick.source === 'bonus' ? 'Bonus' : 'Abgerichtet'}</span>
              {trick.purposeName && <span className="desc"> · {trick.purposeName}</span>}
            </li>
          ))}
        </ul>
      )}
      <details>
        <summary>Regeln (Mit Tieren umgehen)</summary>
        <p className="desc">{TRICK_HELP}</p>
      </details>
      {editing && (
        <TrickEditModal
          character={character}
          onCancel={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            onChanged();
          }}
        />
      )}
    </div>
  );
}

function TrickEditModal({
  character,
  onCancel,
  onSaved,
}: {
  character: Character;
  onCancel: () => void;
  onSaved: () => void;
}) {
  const info = character.companion!;
  const limits = info.trickLimits!;
  const [catalog, setCatalog] = useState<TrickCatalog | null>(null);
  const [picks, setPicks] = useState<Record<string, Source>>(() =>
    Object.fromEntries(info.tricks.map((t) => [t.id, t.source])),
  );
  const [purposeId, setPurposeId] = useState<string>(info.trickPurpose?.id ?? '');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiGet<TrickCatalog>(`/api/companion-tricks?character_id=${character.id}`)
      .then(setCatalog)
      .catch(() => setError('Tricks konnten nicht geladen werden.'));
  }, [character.id]);

  const tricksById = new Map((catalog?.tricks ?? []).map((t) => [t.id, t]));
  const purpose = catalog?.purposes.find((p) => p.id === purposeId) ?? null;
  // A variant ("Angreifen (alle Wesen)") covers the trick it includes.
  const covered = new Set(
    Object.keys(picks).flatMap((id) => [id, tricksById.get(id)?.variantOfId].filter((x): x is string => !!x)),
  );
  const missing = (purpose?.trickIds ?? []).filter((id) => !covered.has(id));
  const used = (source: Source) =>
    Object.entries(picks)
      .filter(([, s]) => s === source)
      .reduce((sum, [id]) => sum + (tricksById.get(id)?.cost ?? 1), 0);
  const bonusUsed = used('bonus');
  const trainedUsed = used('trained');
  const overBonus = bonusUsed > limits.bonus.max;
  const overTrained = limits.trained.max != null && trainedUsed > limits.trained.max;

  function setPick(id: string, value: Source | '') {
    setPicks((prev) => {
      const next = { ...prev };
      if (value) next[id] = value;
      else delete next[id];
      // A trick and its variant can't both be known.
      const variantOf = tricksById.get(id)?.variantOfId;
      if (value && variantOf) delete next[variantOf];
      if (value) for (const t of tricksById.values()) if (t.variantOfId === id) delete next[t.id];
      return next;
    });
  }

  function choosePurpose(id: string) {
    setPurposeId(id);
    const chosen = catalog?.purposes.find((p) => p.id === id);
    if (!chosen) return;
    // Add the training's tricks the companion doesn't know yet, as trained.
    setPicks((prev) => {
      const next = { ...prev };
      const known = new Set(
        Object.keys(next).flatMap((k) => [k, tricksById.get(k)?.variantOfId].filter((x): x is string => !!x)),
      );
      for (const trickId of chosen.trickIds) if (!known.has(trickId)) next[trickId] = 'trained';
      return next;
    });
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      await apiPut(`/api/characters/${character.id}/tricks`, {
        purpose_id: purposeId || null,
        tricks: Object.entries(picks).map(([trick_id, source]) => ({ trick_id, source })),
      });
      onSaved();
    } catch {
      setError('Tricks konnten nicht gespeichert werden.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="modal-overlay open"
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>Tricks von {character.name}</h2>
          <button type="button" className="modal-close" onClick={onCancel}>✕</button>
        </div>
        <div className="modal-body trick-edit">
          {!catalog ? (
            <p>{error ?? 'Lade …'}</p>
          ) : (
            <>
              <p className={overBonus || overTrained ? 'companion-warning' : ''}>
                {formatLimits(bonusUsed, trainedUsed, limits)} (IN {limits.intelligence})
              </p>
              <label className="detail-label" htmlFor="trick-purpose">Aufgabe</label>
              <select id="trick-purpose" value={purposeId} onChange={(e) => choosePurpose(e.target.value)}>
                <option value="">— keine —</option>
                {catalog.purposes.map((p) => (
                  <option key={p.id} value={p.id} disabled={p.unavailableReason != null}>
                    {p.name} (SG {p.dc}, {p.weeks} Wochen){p.unavailableReason ? ` — ${p.unavailableReason}` : ''}
                  </option>
                ))}
              </select>
              {purpose && <p className="desc">{purpose.description}</p>}
              {missing.length > 0 && (
                <p className="companion-warning">
                  Die Aufgabe umfasst auch: {missing.map((id) => tricksById.get(id)?.name).join(', ')}
                </p>
              )}
              <table className="trick-table">
                <tbody>
                  {catalog.tricks.map((t) => (
                    <tr key={t.id} title={t.description}>
                      <td>
                        {t.name} <span className="desc">(SG {t.dc}{t.cost > 1 ? `, zählt ${t.cost}×` : ''})</span>
                        {t.unavailableReason && <div className="desc">{t.unavailableReason}</div>}
                      </td>
                      <td>
                        <select
                          value={picks[t.id] ?? ''}
                          disabled={t.unavailableReason != null && !picks[t.id]}
                          onChange={(e) => setPick(t.id, e.target.value as Source | '')}
                        >
                          <option value="">—</option>
                          <option value="bonus">Bonus</option>
                          <option value="trained">Abgerichtet</option>
                        </select>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {error && <p className="companion-warning">{error}</p>}
            </>
          )}
        </div>
        <div className="modal-foot">
          <button type="button" className="hp-btn ghost" onClick={onCancel}>Abbrechen</button>
          <button
            type="button"
            className="hp-btn confirm"
            disabled={!catalog || saving || overBonus || overTrained || missing.length > 0}
            onClick={save}
          >
            Speichern
          </button>
        </div>
      </div>
    </div>
  );
}
