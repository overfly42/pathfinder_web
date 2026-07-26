import type { Dispatch, SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import { featMax, totalLevel } from '../../lib/creationCalculations';
import { PickList } from './PickList';

interface FeatsStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

export function FeatsStep({ draft, options, setDraft }: FeatsStepProps) {
  const max = featMax(totalLevel(draft));

  function toggleFeat(name: string) {
    setDraft((prev) => {
      const idx = prev.feats.indexOf(name);
      if (idx !== -1) return { ...prev, feats: prev.feats.filter((f) => f !== name) };
      if (prev.feats.length >= max) return prev;
      return { ...prev, feats: [...prev.feats, name] };
    });
  }

  return (
    <PickList
      items={options.feats}
      selected={draft.feats}
      max={max}
      onToggle={toggleFeat}
      selectedListLabel="Gewählte Talente"
      emptyText="Noch keine Talente gewählt."
      searchPlaceholder="Talente durchsuchen …"
    />
  );
}
