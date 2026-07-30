import type { Dispatch, SetStateAction } from 'react';
import type { CreationDraft } from '../../types/creationDraft';
import type { CreationOptions } from '../../types/creationOptions';
import { PickList } from './PickList';

const MAX_TRAITS = 2;

const AREA_LABELS: Record<string, string> = {
  combat: 'Kampf',
  faith: 'Glauben',
  magic: 'Magie',
  race: 'Rasse',
  region: 'Region',
  social: 'Sozial',
  campaign: 'Kampagne',
  general: 'Allgemein',
};

function areaLabel(area: string): string {
  return AREA_LABELS[area] ?? area;
}

interface TraitsStepProps {
  draft: CreationDraft;
  options: CreationOptions;
  setDraft: Dispatch<SetStateAction<CreationDraft>>;
}

export function TraitsStep({ draft, options, setDraft }: TraitsStepProps) {
  const areaById = new Map(options.traits.map((t) => [t.id, t.area]));
  // PF1e rule: at most one trait per area — a character can't take two
  // "combat" traits, for example.
  const selectedAreas = new Set(draft.traits.map((id) => areaById.get(id)));

  function toggleTrait(id: string) {
    setDraft((prev) => {
      const idx = prev.traits.indexOf(id);
      if (idx !== -1) return { ...prev, traits: prev.traits.filter((t) => t !== id) };
      if (prev.traits.length >= MAX_TRAITS) return prev;
      const area = areaById.get(id);
      if (area && prev.traits.some((t) => areaById.get(t) === area)) return prev;
      return { ...prev, traits: [...prev.traits, id] };
    });
  }

  const disabledIds = options.traits
    .filter((t) => !draft.traits.includes(t.id) && selectedAreas.has(t.area))
    .map((t) => t.id);

  return (
    <PickList
      items={options.traits.map((t) => ({ id: t.id, label: `${t.name} (${areaLabel(t.area)})` }))}
      selected={draft.traits}
      max={MAX_TRAITS}
      onToggle={toggleTrait}
      selectedListLabel="Gewählte Wesenszüge"
      emptyText="Noch keine Wesenszüge gewählt."
      disabledIds={disabledIds}
    />
  );
}
