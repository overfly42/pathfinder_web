import { useAppState } from '../../state/AppStateContext';
import type { Language } from '../../lib/spellComponents';
import { formatSpellComponents } from '../../lib/spellComponents';
import type { SpellComponents } from '../../types/character';

/** Confirmation popup for casting a prepared spell from the "Zauber" cast bar (`SheetTabs.tsx`) —
 *  shows components and the spell's full description before actually consuming a prepared copy,
 *  same "confirm before spending a resource" shape as `UseAbilityModal`. */
/** Popup field labels per UI language (the values themselves are German PRD text for now). */
const LABELS: Record<Language, Record<string, string>> = {
  de: {
    school: 'Schule', castingTime: 'Zeitaufwand', components: 'Komponenten', range: 'Reichweite',
    target: 'Ziel', duration: 'Wirkungsdauer', savingThrow: 'Rettungswurf', spellResistance: 'Zauberresistenz', dc: 'SG',
  },
  en: {
    school: 'School', castingTime: 'Casting Time', components: 'Components', range: 'Range',
    target: 'Target', duration: 'Duration', savingThrow: 'Saving Throw', spellResistance: 'Spell Resistance', dc: 'DC',
  },
};

interface CastSpellEntry {
  name: string;
  description: string;
  components: SpellComponents | null;
  school: string | null;
  castingTime: string | null;
  range: string | null;
  target: string | null;
  duration: string | null;
  savingThrow: string | null;
  spellResistance: string | null;
  dc?: number;
  remaining: number;
  preparedCount: number;
}

interface CastSpellModalProps {
  entry: CastSpellEntry | null;
  onCancel: () => void;
  onConfirm: () => void;
}

export function CastSpellModal({ entry, onCancel, onConfirm }: CastSpellModalProps) {
  const { language } = useAppState();
  const t = LABELS[language];
  return (
    <div
      className={`modal-overlay${entry ? ' open' : ''}`}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{entry?.name ?? 'Zauber'}</h2>
          <button type="button" className="modal-close" onClick={onCancel}>✕</button>
        </div>
        <div className="modal-body">
          {entry?.school && <p><strong>{t.school}:</strong> {entry.school}</p>}
          {entry?.castingTime && <p><strong>{t.castingTime}:</strong> {entry.castingTime}</p>}
          <p><strong>{t.components}:</strong> {formatSpellComponents(entry?.components, language)}</p>
          <p><strong>{t.range}:</strong> {entry?.range ?? '—'}</p>
          {entry?.target && <p><strong>{t.target}:</strong> {entry.target}</p>}
          {entry?.duration && <p><strong>{t.duration}:</strong> {entry.duration}</p>}
          <p>
            <strong>{t.savingThrow}:</strong> {entry?.savingThrow ?? '—'}
            {entry?.savingThrow != null && entry?.dc != null ? ` (${t.dc} ${entry.dc})` : ''}
          </p>
          {entry?.spellResistance && <p><strong>{t.spellResistance}:</strong> {entry.spellResistance}</p>}
          <p>{entry?.description}</p>
          <p>{entry?.remaining} von {entry?.preparedCount} heute noch verfügbar.</p>
        </div>
        <div className="modal-foot">
          <button type="button" className="hp-btn ghost" onClick={onCancel}>Abbrechen</button>
          <button type="button" className="hp-btn confirm" onClick={onConfirm}>Wirken</button>
        </div>
      </div>
    </div>
  );
}
