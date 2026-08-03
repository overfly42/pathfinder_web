import type { Dispatch, SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import { featMax } from '../../lib/creationCalculations';
import { PickList } from './PickList';

interface FeatsStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

export function FeatsStep({ draft, options, setDraft }: FeatsStepProps) {
  const max = featMax(draft, options);
  const featById = new Map(options.feats.map((f) => [f.id, f]));
  const weapons = options.items.filter((i) => i.category === 'weapon');

  function toggleFeat(id: string) {
    setDraft((prev) => {
      const idx = prev.feats.indexOf(id);
      if (idx !== -1) {
        const nextSubChoices = { ...prev.featSubChoices };
        delete nextSubChoices[id];
        return { ...prev, feats: prev.feats.filter((f) => f !== id), featSubChoices: nextSubChoices };
      }
      if (prev.feats.length >= max) return prev;
      return { ...prev, feats: [...prev.feats, id] };
    });
  }

  function setSubChoice(featId: string, value: string) {
    setDraft((prev) => ({ ...prev, featSubChoices: { ...prev.featSubChoices, [featId]: value } }));
  }

  const needingSubChoice = draft.feats
    .map((id) => featById.get(id))
    .filter((feat): feat is NonNullable<typeof feat> => feat !== undefined && feat.subChoiceType !== null);

  return (
    <>
      <PickList
        items={options.feats.map((f) => ({ id: f.id, label: f.name }))}
        selected={draft.feats}
        max={max}
        onToggle={toggleFeat}
        selectedListLabel="Gewählte Talente"
        emptyText="Noch keine Talente gewählt."
        searchPlaceholder="Talente durchsuchen …"
      />
      {needingSubChoice.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <div className="field-label">Talent-Details</div>
          {needingSubChoice.map((feat) => (
            <div className="field-row" key={feat.id} style={{ maxWidth: 320 }}>
              <div className="field-label">{feat.name}</div>
              {feat.subChoiceType === 'weapon' && (
                <select value={draft.featSubChoices[feat.id] ?? ''} onChange={(e) => setSubChoice(feat.id, e.target.value)}>
                  <option value="">– Waffe wählen –</option>
                  {weapons.map((w) => (
                    <option key={w.id} value={w.id}>{w.name}</option>
                  ))}
                </select>
              )}
              {feat.subChoiceType === 'skill' && (
                <select value={draft.featSubChoices[feat.id] ?? ''} onChange={(e) => setSubChoice(feat.id, e.target.value)}>
                  <option value="">– Fertigkeit wählen –</option>
                  {options.skills.map((s) => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
              )}
              {feat.subChoiceType === 'spell_school' && (
                <select value={draft.featSubChoices[feat.id] ?? ''} onChange={(e) => setSubChoice(feat.id, e.target.value)}>
                  <option value="">– Zauberschule wählen –</option>
                  {options.spellSchools.map((school) => (
                    <option key={school} value={school}>{school}</option>
                  ))}
                </select>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
