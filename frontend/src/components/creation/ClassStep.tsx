import type { Dispatch, SetStateAction } from 'react';
import type { ClassRow, CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import { createId } from '../../lib/id';
import { availableOptionGroups } from '../../lib/classOptions';
import { classDef, totalLevel } from '../../lib/creationCalculations';
import { useFavoredClassBonusOptions } from '../../hooks/useFavoredClassBonusOptions';
import { OptionGroupPicker } from '../primitives/OptionGroupPicker';

interface ClassStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

export function ClassStep({ draft, options, setDraft }: ClassStepProps) {
  function updateRow(rowId: string, patch: Partial<ClassRow>) {
    setDraft((prev) => ({
      ...prev,
      classRows: prev.classRows.map((row) => (row.id === rowId ? { ...row, ...patch } : row)),
    }));
  }

  function onClassChange(rowId: string, className: string) {
    updateRow(rowId, { className, archetypes: [], options: {} });
    if (rowId === draft.classRows[0]?.id) {
      setDraft((prev) => ({ ...prev, favoredClassBonus: null }));
    }
  }

  function setFavoredClassBonus(value: string) {
    setDraft((prev) => ({ ...prev, favoredClassBonus: prev.favoredClassBonus === value ? null : value }));
  }

  function addClassRow() {
    const first = options.classes[0];
    setDraft((prev) => ({
      ...prev,
      classRows: [
        ...prev.classRows,
        { id: createId(), className: first.name, level: 1, archetypes: [], options: {} },
      ],
    }));
  }

  function toggleArchetype(rowId: string, archetype: string, max: number) {
    const row = draft.classRows.find((r) => r.id === rowId);
    const cls = row ? classDef(options, row.className) : undefined;
    // Deselecting an archetype that required a weapon choice drops its
    // now-stale entry too — `classWeaponChoicesForSubmission` would already
    // filter it out at submit time, but leaving it in the draft would still
    // show the picker's old value if the same archetype gets re-selected.
    const droppedAbilityId = row?.archetypes.includes(archetype) ? cls?.archetypeWeaponChoiceAbilityId[archetype] : undefined;
    setDraft((prev) => {
      const nextClassWeaponChoices = { ...prev.classWeaponChoices };
      if (droppedAbilityId) delete nextClassWeaponChoices[droppedAbilityId];
      return {
        ...prev,
        classWeaponChoices: nextClassWeaponChoices,
        classRows: prev.classRows.map((r) => {
          if (r.id !== rowId) return r;
          const idx = r.archetypes.indexOf(archetype);
          let next: string[];
          if (idx !== -1) next = r.archetypes.filter((a) => a !== archetype);
          else if (r.archetypes.length < max) next = [...r.archetypes, archetype];
          else next = r.archetypes;
          return { ...r, archetypes: next };
        }),
      };
    });
  }

  function setClassWeaponChoice(abilityId: string, weaponId: string) {
    setDraft((prev) => ({ ...prev, classWeaponChoices: { ...prev.classWeaponChoices, [abilityId]: weaponId } }));
  }

  function removeClassRow(rowId: string) {
    setDraft((prev) => {
      if (prev.classRows.length <= 1) return prev;
      const wasFavored = prev.classRows[0]?.id === rowId;
      return {
        ...prev,
        classRows: prev.classRows.filter((r) => r.id !== rowId),
        favoredClassBonus: wasFavored ? null : prev.favoredClassBonus,
      };
    });
  }

  function toggleClassOption(rowId: string, groupKey: string, choice: string, max: number) {
    setDraft((prev) => ({
      ...prev,
      classRows: prev.classRows.map((row) => {
        if (row.id !== rowId) return row;
        const chosen = row.options[groupKey] ?? [];
        const idx = chosen.indexOf(choice);
        let next: string[];
        if (idx !== -1) next = chosen.filter((c) => c !== choice);
        else if (chosen.length < max) next = [...chosen, choice];
        else next = chosen;
        return { ...row, options: { ...row.options, [groupKey]: next } };
      }),
    }));
  }

  const weapons = options.items.filter((i) => i.category === 'weapon');
  const level = totalLevel(draft);
  const favoredClassBonusOptions = useFavoredClassBonusOptions(draft.raceId, draft.classRows[0]?.className ?? null);
  const alternateFavoredClassBonuses = (favoredClassBonusOptions?.options ?? []).filter(
    (name) => name !== 'hp' && name !== 'skill',
  );

  return (
    <>
      <div className="field-label">
        Ein Charakter kann mehrere Klassenstufen haben; die Summe ergibt die Charakterstufe. Zusatzoptionen (z. B.
        Domänen, Blutlinie, Günstlingsfeind) erscheinen automatisch, sobald eine passende Klasse gewählt ist.
      </div>

      <div style={{ marginTop: 14 }}>
        {draft.classRows.map((row, index) => {
          const cls = classDef(options, row.className);
          const archetypeChoices = (cls?.archetypes ?? []).filter((a) => a !== 'Keiner');
          const groups = availableOptionGroups(
            cls?.optionGroups ?? [],
            row.level,
            row.archetypes,
            cls?.archetypeOptionOverrides ?? {},
          );
          return (
            <div className="class-row-wrap" key={row.id}>
              <div className="class-row">
                <div>
                  <label>Klasse</label>
                  <select value={row.className} onChange={(e) => onClassChange(row.id, e.target.value)}>
                    {options.classes.map((c) => (
                      <option value={c.name} key={c.name}>{c.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label>Stufe</label>
                  <input
                    type="number"
                    min={1}
                    value={row.level}
                    onChange={(e) => updateRow(row.id, { level: parseInt(e.target.value, 10) || 0 })}
                  />
                </div>
                <button type="button" className="row-del" onClick={() => removeClassRow(row.id)} title="Klasse entfernen">✕</button>
              </div>

              {archetypeChoices.length > 0 && (
                <OptionGroupPicker
                  label="Archetypen"
                  max={archetypeChoices.length}
                  choices={archetypeChoices}
                  selected={row.archetypes}
                  onToggle={(a) => toggleArchetype(row.id, a, archetypeChoices.length)}
                />
              )}

              {row.archetypes.map((archetypeName) => {
                const abilityId = cls?.archetypeWeaponChoiceAbilityId[archetypeName];
                if (!abilityId) return null;
                return (
                  <div key={abilityId} style={{ marginTop: 14 }}>
                    <label>Waffe ({archetypeName})</label>
                    <select
                      value={draft.classWeaponChoices[abilityId] ?? ''}
                      onChange={(e) => setClassWeaponChoice(abilityId, e.target.value)}
                    >
                      <option value="">– wählen –</option>
                      {weapons.map((w) => (
                        <option value={w.id} key={w.id}>{w.name}</option>
                      ))}
                    </select>
                  </div>
                );
              })}

              {groups.length > 0 && (
                <div className="class-options">
                  {groups.map((g) => (
                    <OptionGroupPicker
                      key={g.key}
                      label={g.label}
                      max={g.effectiveMax}
                      choices={g.availableChoiceNames}
                      selected={row.options[g.key] ?? []}
                      onToggle={(choice) => toggleClassOption(row.id, g.key, choice, g.effectiveMax)}
                    />
                  ))}
                </div>
              )}

              {index === 0 && draft.raceId && (
                <>
                  <div className="field-label" style={{ marginTop: 18 }}>
                    Bevorzugte Klasse (1. Stufe): zusätzlicher Bonus (1 Trefferpunkt, 1 Fertigkeitsrang, oder ein
                    rassenspezifischer Alternativbonus).
                  </div>
                  {favoredClassBonusOptions ? (
                    <div className="chip-row" style={{ marginTop: 10 }}>
                      <button
                        type="button"
                        className={`chip${draft.favoredClassBonus === 'hp' ? ' active' : ''}`}
                        onClick={() => setFavoredClassBonus('hp')}
                      >
                        +1 Trefferpunkt
                      </button>
                      <button
                        type="button"
                        className={`chip${draft.favoredClassBonus === 'skill' ? ' active' : ''}`}
                        onClick={() => setFavoredClassBonus('skill')}
                      >
                        +1 Fertigkeitsrang
                      </button>
                      {alternateFavoredClassBonuses.map((name) => (
                        <button
                          key={name}
                          type="button"
                          className={`chip${draft.favoredClassBonus === name ? ' active' : ''}`}
                          onClick={() => setFavoredClassBonus(name)}
                        >
                          {favoredClassBonusOptions.shortLabels[name] ?? name}
                        </button>
                      ))}
                    </div>
                  ) : (
                    <div className="warning-note" style={{ marginTop: 10 }}>Lade Optionen …</div>
                  )}
                </>
              )}
            </div>
          );
        })}
      </div>

      <button type="button" className="add-link" onClick={addClassRow}>+ Weitere Klasse hinzufügen</button>

      <div className="total-level-banner">
        <span className="k">Charakterstufe (Summe)</span>
        <span className="v">{level}</span>
      </div>
    </>
  );
}
