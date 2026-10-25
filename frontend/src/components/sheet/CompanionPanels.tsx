import { useState } from 'react';
import { Link } from 'react-router-dom';
import { apiPost } from '../../api/client';
import type { Character, CompanionLevel, CompanionSlot } from '../../types/character';
import { companionLevelName, formatCompanionBreakdown } from '../../lib/companionLevels';
import { CompanionTricks } from './CompanionTricks';

/** "Meister | Wolf" — switches between a master and its companions (roadmap slice 10 step 2b).
 *  On a master's sheet it lists the companions filling its slots; on a companion's sheet it
 *  links back to the master. Nothing to show for a character without either. */
export function CompanionSwitcher({ character, onOpen }: { character: Character; onOpen: (id: string) => void }) {
  if (character.companion) {
    return (
      <div className="companion-switcher">
        <button type="button" className="companion-link" onClick={() => onOpen(character.companion!.master.id)}>
          ← {character.companion.master.name}
        </button>
        <span className="companion-switcher-current">{character.name}</span>
      </div>
    );
  }
  const companions = (character.companionLevels ?? [])
    .flatMap((track) => track.slots)
    .map((slot) => slot.companion)
    .filter((c): c is { id: string; name: string } => c != null);
  if (companions.length === 0) return null;
  return (
    <div className="companion-switcher">
      <span className="companion-switcher-current">{character.name}</span>
      {companions.map((c) => (
        <button type="button" className="companion-link" key={c.id} onClick={() => onOpen(c.id)}>
          {c.name} →
        </button>
      ))}
    </div>
  );
}

/** The companion's own banner: master, effective level and where it comes from, HD, tricks.
 *  `onChanged` reloads the sheet after the tricks were edited. */
export function CompanionBanner({ character, onChanged }: { character: Character; onChanged: () => void }) {
  const info = character.companion;
  if (!info) return null;
  const hdMismatch = info.expectedHitDice != null && info.expectedHitDice !== info.hitDice;
  return (
    <div className="companion-banner">
      {info.orphaned ? (
        <p className="companion-warning">
          Ohne Anspruch: {info.master.name} hat derzeit keinen Anspruch mehr auf diesen Gefährten. Der Gefährte
          bleibt erhalten; seine Werte richten sich nach seinen aktuellen Trefferwürfeln.
        </p>
      ) : (
        <p>
          {info.trackLabel} von <strong>{info.master.name}</strong> — {companionLevelName(info.track)}{' '}
          {info.effectiveLevel}: {formatCompanionBreakdown(info)}
        </p>
      )}
      {info.track === 'familiar' ? (
        <p>
          Stufe des Meisters: {info.hitDice} — TP (halbe TP des Meisters), GAB, Rettungswürfe und
          Fertigkeitsränge kommen vom Meister.
        </p>
      ) : (
        <p>
          Trefferwürfel: {info.hitDice}
          {hdMismatch && ` (laut Tabelle ${info.expectedHitDice})`}
          {' · '}Aufstieg: {info.advancementChoice === 'dex_con' ? '+2 GE/+2 KO statt Tierart' : info.advanced ? 'erreicht' : 'noch nicht erreicht'}
        </p>
      )}
      {info.openHitDice > 0 && (
        <p className="companion-open">
          {info.openHitDice} TW mit offenen Entscheidungen (Fertigkeiten, Talente
          {info.openHitPoints > 0 ? `, ${info.openHitPoints}× Trefferpunkte` : ''}) —{' '}
          <Link className="companion-link" to={`/levelup/${character.id}`}>
            jetzt ausfüllen
          </Link>
        </p>
      )}
      {info.masterNotes.length > 0 && (
        <ul className="companion-master-notes">
          {info.masterNotes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}
      <CompanionTricks character={character} onChanged={onChanged} />
    </div>
  );
}

/** A master's "Gefährten" section: effective level per track with its breakdown, and for every
 *  slot either the companion filling it or a form to create one. */
export function CompanionLevelsSection({
  character,
  onOpen,
  onCreated,
}: {
  character: Character;
  onOpen: (id: string) => void;
  onCreated: (id: string) => void;
}) {
  const levels = character.companionLevels ?? [];
  if (levels.length === 0) return null;
  return (
    <>
      <div className="section-label" style={{ marginTop: 14 }}>
        Gefährten
      </div>
      {levels.map((entry: CompanionLevel) => (
        <div className="trait-item" id={`companionlevel-${entry.track}`} key={entry.track}>
          <div className="name">
            {entry.label} — {companionLevelName(entry.track)} {entry.level}
          </div>
          <div className="desc">{formatCompanionBreakdown(entry)}</div>
          {entry.slots.map((slot) =>
            slot.companion ? (
              <div className="desc" key={slot.slotKey}>
                <button type="button" className="companion-link" onClick={() => onOpen(slot.companion!.id)}>
                  {slot.companion.name} öffnen
                </button>
              </div>
            ) : (
              <CompanionCreateForm key={slot.slotKey} masterId={character.id} slot={slot} onCreated={onCreated} />
            ),
          )}
        </div>
      ))}
    </>
  );
}

function CompanionCreateForm({
  masterId,
  slot,
  onCreated,
}: {
  masterId: string;
  slot: CompanionSlot;
  onCreated: (id: string) => void;
}) {
  const hitDice = slot.hitDice ?? 0;
  // A familiar (roadmap slice 10 step 4) has no HD of its own and no advancement choice.
  const isFamiliar = slot.track === 'familiar';
  const [speciesId, setSpeciesId] = useState('');
  const [name, setName] = useState('');
  const [advancement, setAdvancement] = useState<'species' | 'dex_con'>('species');
  const [hitPoints, setHitPoints] = useState<string[]>(() => Array.from({ length: hitDice }, () => '5'));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit() {
    const values = hitPoints.slice(0, hitDice).map((v) => parseInt(v, 10));
    if (!speciesId || !name.trim() || values.some((v) => !Number.isFinite(v) || v < 1 || v > 8)) {
      setError(
        isFamiliar
          ? 'Bitte Tierart und Namen angeben.'
          : 'Bitte Tierart, Namen und für jeden Trefferwürfel 1–8 Trefferpunkte angeben.',
      );
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const created = await apiPost<{ id: string }>(`/api/characters/${masterId}/companions`, {
        track: slot.track,
        slot_key: slot.slotKey,
        species_id: speciesId,
        name: name.trim(),
        hit_points: values,
        advancement_choice: advancement,
      });
      onCreated(created.id);
    } catch {
      setError(isFamiliar ? 'Vertrauter konnte nicht angelegt werden.' : 'Gefährte konnte nicht angelegt werden.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <details className="gear-add companion-create">
      <summary className="gear-add-btn">{isFamiliar ? '+ Vertrauten anlegen' : '+ Gefährten anlegen'}</summary>
      <div className="hp-popover-body gear-form">
        <select value={speciesId} onChange={(e) => setSpeciesId(e.target.value)}>
          <option value="">— Tierart wählen —</option>
          {slot.species.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name" />
        {!isFamiliar && (
          <select value={advancement} onChange={(e) => setAdvancement(e.target.value as 'species' | 'dex_con')}>
            <option value="species">Aufstieg der Tierart</option>
            <option value="dex_con">+2 GE/KO statt Aufstieg</option>
          </select>
        )}
        {isFamiliar ? (
          <div className="detail-label">TP, GAB, Rettungswürfe und Ränge kommen vom Meister.</div>
        ) : (
          <div className="detail-label">Trefferpunkte je Trefferwürfel (W8)</div>
        )}
        <div className="companion-hp-row">
          {Array.from({ length: hitDice }, (_, i) => (
            <input
              key={i}
              type="number"
              min={1}
              max={8}
              value={hitPoints[i] ?? ''}
              onChange={(e) =>
                setHitPoints((prev) => {
                  const next = [...prev];
                  next[i] = e.target.value;
                  return next;
                })
              }
            />
          ))}
        </div>
        {error && <p style={{ color: '#e29a9a' }}>{error}</p>}
        <div className="hp-popover-actions">
          <button type="button" className="hp-btn confirm" disabled={saving} onClick={submit}>
            Anlegen
          </button>
        </div>
      </div>
    </details>
  );
}
