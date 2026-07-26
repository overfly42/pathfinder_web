import type { ActionTag } from '../../types/character';

const TAG_LABEL: Record<ActionTag, string> = {
  standard: 'Standard',
  reaction: 'Reaktion',
  move: 'Bewegung',
  full: 'Volle Aktion',
};

export function Tag({ variant }: { variant: ActionTag }) {
  return <span className={`tag ${variant}`}>{TAG_LABEL[variant]}</span>;
}
