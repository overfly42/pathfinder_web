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

  function toggleFeat(id: string) {
    setDraft((prev) => {
      const idx = prev.feats.indexOf(id);
      if (idx !== -1) return { ...prev, feats: prev.feats.filter((f) => f !== id) };
      if (prev.feats.length >= max) return prev;
      return { ...prev, feats: [...prev.feats, id] };
    });
  }

  return (
    <PickList
      items={options.feats.map((f) => ({ id: f.id, label: f.name }))}
      selected={draft.feats}
      max={max}
      onToggle={toggleFeat}
      selectedListLabel="Gewählte Talente"
      emptyText="Noch keine Talente gewählt."
      searchPlaceholder="Talente durchsuchen …"
    />
  );
}
