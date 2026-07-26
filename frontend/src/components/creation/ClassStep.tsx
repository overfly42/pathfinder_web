import type { Dispatch, SetStateAction } from 'react';
import type { ClassRow, CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import { createId } from '../../lib/id';
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
    const cls = classDef(options, className);
    updateRow(rowId, { className, archetype: cls?.archetypes[0] ?? 'Keiner', options: {} });
  }

  function addClassRow() {
    const first = options.classes[0];
    setDraft((prev) => ({
      ...prev,
      classRows: [
        ...prev.classRows,
        { id: createId(), className: first.name, level: 1, archetype: first.archetypes[0] ?? 'Keiner', options: {} },
      ],
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
          const archetypes = cls?.archetypes ?? ['Keiner'];
          const groups = cls?.optionGroups ?? [];
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
                <div>
                  <label>Archetyp</label>
                  <select value={row.archetype} onChange={(e) => updateRow(row.id, { archetype: e.target.value })}>
                    {archetypes.map((a) => (
                      <option key={a}>{a}</option>
                    ))}
                  </select>
                </div>
                <button type="button" className="row-del" onClick={() => removeClassRow(row.id)} title="Klasse entfernen">✕</button>
              </div>

              {groups.length > 0 && (
                <div className="class-options">
                  {groups.map((g) => (
                    <OptionGroupPicker
                      key={g.key}
                      label={g.label}
                      max={g.max}
                      choices={g.choices}
                      selected={row.options[g.key] ?? []}
                      onToggle={(choice) => toggleClassOption(row.id, g.key, choice, g.max)}
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
