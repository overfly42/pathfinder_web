import type { Dispatch, SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import { PickList } from './PickList';

const MAX_TRAITS = 2;

interface TraitsStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

export function TraitsStep({ draft, options, setDraft }: TraitsStepProps) {
  function toggleTrait(name: string) {
    setDraft((prev) => {
      const idx = prev.traits.indexOf(name);
      if (idx !== -1) return { ...prev, traits: prev.traits.filter((t) => t !== name) };
      if (prev.traits.length >= MAX_TRAITS) return prev;
      return { ...prev, traits: [...prev.traits, name] };
    });
  }

  return (
    <PickList
      items={options.traits.map((name) => ({ id: name, label: name }))}
      selected={draft.traits}
      max={MAX_TRAITS}
      onToggle={toggleTrait}
      selectedListLabel="Gewählte Wesenszüge"
      emptyText="Noch keine Wesenszüge gewählt."
    />
  );
}
