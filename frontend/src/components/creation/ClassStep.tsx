import type { Dispatch, SetStateAction } from 'react';
import type { ClassRow, CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import { createId } from '../../lib/id';
import { availableOptionGroups } from '../../lib/classOptions';
import { classDef, totalLevel } from '../../lib/creationCalculations';
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
    setDraft((prev) => ({
      ...prev,
      classRows: prev.classRows.map((row) => {
        if (row.id !== rowId) return row;
        const idx = row.archetypes.indexOf(archetype);
        let next: string[];
        if (idx !== -1) next = row.archetypes.filter((a) => a !== archetype);
        else if (row.archetypes.length < max) next = [...row.archetypes, archetype];
        else next = row.archetypes;
        return { ...row, archetypes: next };
      }),
    }));
  }

  function removeClassRow(rowId: string) {
    setDraft((prev) => (prev.classRows.length <= 1 ? prev : { ...prev, classRows: prev.classRows.filter((r) => r.id !== rowId) }));
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

  const level = totalLevel(draft);

  return (
    <>
      <div className="field-label">
        Ein Charakter kann mehrere Klassenstufen haben; die Summe ergibt die Charakterstufe. Zusatzoptionen (z. B.
        Domänen, Blutlinie, Günstlingsfeind) erscheinen automatisch, sobald eine passende Klasse gewählt ist.
      </div>

      <div style={{ marginTop: 14 }}>
        {draft.classRows.map((row) => {
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
