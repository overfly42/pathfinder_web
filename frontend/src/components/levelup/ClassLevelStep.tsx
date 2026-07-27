import type { Dispatch, SetStateAction } from 'react';
import type { CharacterProgression } from '../../types/characterProgression';
import type { LevelUpDraft } from '../../types/levelUpDraft';
import type { LevelUpOptions } from '../../types/levelUpOptions';
import { OptionGroupPicker } from '../primitives/OptionGroupPicker';

interface ClassLevelStepProps {
  progression: CharacterProgression;
  options: LevelUpOptions;
  draft: LevelUpDraft;
  setDraft: Dispatch<SetStateAction<LevelUpDraft>>;
}

export function ClassLevelStep({ progression, options, draft, setDraft }: ClassLevelStepProps) {
  const knownClassNames = progression.classes.map((c) => c.className);
  const availableNewClasses = options.classes.filter((c) => !knownClassNames.includes(c.name));

  function onTargetChange(value: string) {
    if (value === 'new') {
      const first = availableNewClasses[0] ?? options.classes[0];
      setDraft((prev) => ({
        ...prev,
        target: { mode: 'new', className: first.name, archetypes: [], options: {} },
      }));
      return;
    }
    const classId = value.split(':')[1];
    setDraft((prev) => ({ ...prev, target: { mode: 'existing', classId } }));
  }

  function onNewClassChange(className: string) {
    setDraft((prev) => ({
      ...prev,
      target: { mode: 'new', className, archetypes: [], options: {} },
    }));
  }

  function toggleNewArchetype(archetype: string, max: number) {
    setDraft((prev) => {
      if (prev.target.mode !== 'new') return prev;
      const chosen = prev.target.archetypes;
      const idx = chosen.indexOf(archetype);
      let next: string[];
      if (idx !== -1) next = chosen.filter((a) => a !== archetype);
      else if (chosen.length < max) next = [...chosen, archetype];
      else next = chosen;
      return { ...prev, target: { ...prev.target, archetypes: next } };
    });
  }

  function toggleNewClassOption(groupKey: string, choice: string, max: number) {
    setDraft((prev) => {
      if (prev.target.mode !== 'new') return prev;
      const chosen = prev.target.options[groupKey] ?? [];
      const idx = chosen.indexOf(choice);
      let next: string[];
      if (idx !== -1) next = chosen.filter((c) => c !== choice);
      else if (chosen.length < max) next = [...chosen, choice];
      else next = chosen;
      return { ...prev, target: { ...prev.target, options: { ...prev.target.options, [groupKey]: next } } };
    });
  }

  const target = draft.target;
  const selectValue = target.mode === 'new' ? 'new' : `existing:${target.classId}`;
  const newClassDef = target.mode === 'new' ? options.classes.find((c) => c.name === target.className) : undefined;

  return (
    <>
      <div className="section-label">Bestehende Klassen</div>
      <div>
        {progression.classes.map((c) => {
          const optLines = Object.entries(c.options)
            .filter(([, values]) => values.length > 0)
            .map(([key, values]) => `${key}: ${values.join(', ')}`)
            .join(' · ');
          const archetypeLabel = c.archetypes.length ? c.archetypes.join(', ') : 'Keiner';
          return (
            <div className="summary-block" style={{ marginBottom: 10 }} key={c.id}>
              <div className="sb-title">{c.className} — Archetypen: {archetypeLabel}</div>
              <div className="sb-line"><span>Aktuelle Stufe</span><span className="val">{c.level}</span></div>
              {optLines && <div className="sb-line"><span>Zusatzoptionen</span><span className="val">{optLines}</span></div>}
            </div>
          );
        })}
      </div>

      <div className="section-label">Diese Stufe erhält</div>
      <div className="field-row" style={{ maxWidth: 340 }}>
        <select className="text-input" value={selectValue} onChange={(e) => onTargetChange(e.target.value)}>
          {progression.classes.map((c) => (
            <option value={`existing:${c.id}`} key={c.id}>{c.className} (Stufe {c.level} → {c.level + 1})</option>
          ))}
          <option value="new">+ Neue Klasse (Multiclass, Stufe 1)</option>
        </select>
      </div>

      {target.mode === 'new' && (
        <div className="class-row-wrap">
          <div className="class-row class-row--compact">
            <div>
              <label>Klasse</label>
              <select value={target.className} onChange={(e) => onNewClassChange(e.target.value)}>
                {availableNewClasses.map((c) => (
                  <option value={c.name} key={c.name}>{c.name}</option>
                ))}
              </select>
            </div>
          </div>
          {newClassDef && (() => {
            const archetypeChoices = newClassDef.archetypes.filter((a) => a !== 'Keiner');
            return archetypeChoices.length > 0 ? (
              <OptionGroupPicker
                label="Archetypen"
                max={archetypeChoices.length}
                choices={archetypeChoices}
                selected={target.archetypes}
                onToggle={(a) => toggleNewArchetype(a, archetypeChoices.length)}
              />
            ) : null;
          })()}
          {newClassDef && newClassDef.optionGroups.length > 0 && (
            <div className="class-options">
              {newClassDef.optionGroups.map((g) => (
                <OptionGroupPicker
                  key={g.key}
                  label={g.label}
                  max={g.max}
                  choices={g.choices}
                  selected={target.options[g.key] ?? []}
                  onToggle={(choice) => toggleNewClassOption(g.key, choice, g.max)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </>
  );
}
