import type { Dispatch, SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import type { AbilityKey } from '../../types/abilities';
import { replacedTraitNames, selectedRace as findSelectedRace } from '../../lib/creationCalculations';

interface BasicsStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

export function BasicsStep({ draft, options, setDraft }: BasicsStepProps) {
  const race = findSelectedRace(draft, options);

  function selectRace(id: string) {
    setDraft((prev) => ({
      ...prev,
      raceId: id,
      flexAbility: id !== prev.raceId ? null : prev.flexAbility,
      altTraits: id !== prev.raceId ? [] : prev.altTraits,
      favoredClassBonus: id !== prev.raceId ? null : prev.favoredClassBonus,
    }));
  }

  function toggleAltTrait(name: string) {
    if (!race) return;
    const isActive = draft.altTraits.includes(name);
    if (isActive) {
      setDraft((prev) => ({ ...prev, altTraits: prev.altTraits.filter((n) => n !== name) }));
      return;
    }
    const alt = race.alt.find((a) => a.name === name);
    if (!alt) return;
    const replaced = replacedTraitNames(draft, options);
    const conflict = alt.replaces.some((t) => replaced.has(t));
    if (conflict) return;
    setDraft((prev) => ({ ...prev, altTraits: [...prev.altTraits, name] }));
  }

  const replaced = replacedTraitNames(draft, options);

  return (
    <>
      <div className="field-grid">
        <div className="field-row">
          <div className="field-label">Charaktername</div>
          <input
            type="text"
            className="text-input"
            placeholder="z. B. Elyra Silberauge"
            value={draft.name}
            onChange={(e) => setDraft((prev) => ({ ...prev, name: e.target.value }))}
          />
        </div>
        <div className="field-row">
          <div className="field-label">Geschlecht</div>
          <select
            className="text-input"
            value={draft.gender}
            onChange={(e) => setDraft((prev) => ({ ...prev, gender: e.target.value as CreationDraft['gender'] }))}
          >
            <option value="maennlich">Männlich</option>
            <option value="weiblich">Weiblich</option>
            <option value="">Keine Angabe</option>
          </select>
        </div>
      </div>

      <div className="section-label">Rasse</div>
      <div className="race-grid">
        {options.races.map((r) => (
          <div
            className={`race-card${draft.raceId === r.id ? ' selected' : ''}`}
            key={r.id}
            onClick={() => selectRace(r.id)}
          >
            <div className="name">{r.name}</div>
            <div className="desc">{r.short}</div>
          </div>
        ))}
      </div>

      {race && (
        <div className="race-detail">
          <div className="rd-title">{race.name} — Rasseneigenschaften</div>
          <div>
            {race.traits.map((t) => {
              const isReplaced = replaced.has(t.name);
              return (
                <div className={`trait-item${isReplaced ? ' replaced' : ''}`} key={t.name}>
                  <div className="name">
                    {t.name}
                    {isReplaced && <span className="tag replaced-tag"> Ersetzt</span>}
                  </div>
                  <div className="desc">{t.desc}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {race && race.alt.length > 0 && (
        <div className="race-detail">
          <div className="rd-title">Alternative Volksmerkmale (optional)</div>
          <div className="field-label">
            Ersetzt jeweils ein Standard-Volksmerkmal derselben Rasse. Pro ersetztem Merkmal ist nur eine Alternative wählbar.
          </div>
          <div>
            {race.alt.map((a) => {
              const active = draft.altTraits.includes(a.name);
              const disabled = !active && a.replaces.some((t) => replaced.has(t));
              return (
                <div
                  className={`trait-item alt-trait-item${active ? ' active' : ''}${disabled ? ' disabled' : ''}`}
                  key={a.name}
                  onClick={disabled ? undefined : () => toggleAltTrait(a.name)}
                >
                  <div className="name">
                    {a.name}
                    <span className="pick-indicator">{active ? '✓ Gewählt' : 'Wählen'}</span>
                  </div>
                  <div className="desc">
                    {a.desc} <span className="alt-replaces">(ersetzt {a.replaces.join(', ')})</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {race && race.flex && (
        <div className="race-detail">
          <div className="rd-title">Freier Attributsbonus (+2)</div>
          <div className="field-label">Diese Rasse gewährt +2 auf ein frei wählbares Attribut.</div>
          <select
            className="text-input"
            style={{ maxWidth: 240 }}
            value={draft.flexAbility ?? ''}
            onChange={(e) => setDraft((prev) => ({ ...prev, flexAbility: (e.target.value || null) as AbilityKey | null }))}
          >
            <option value="">— Attribut wählen —</option>
            {options.abilities.map((a) => (
              <option value={a.key} key={a.key}>{a.name}</option>
            ))}
          </select>
        </div>
      )}
    </>
  );
}
