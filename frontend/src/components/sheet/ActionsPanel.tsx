import type { ActionOption } from '../../types/character';
import { Panel, PanelSearch } from '../primitives/Panel';
import { Tag } from '../primitives/Tag';

interface ActionsPanelProps {
  actions: ActionOption[];
  roundLabel: string;
  onActionClick: (action: ActionOption) => void;
}

export function ActionsPanel({ actions, roundLabel, onActionClick }: ActionsPanelProps) {
  return (
    <Panel title="Aktuelle Optionen" hint={roundLabel} beforeBody={<PanelSearch placeholder="Optionen durchsuchen" />}>
      {actions.map((action) => (
        <button
          type="button"
          className={`option-card${action.isActive ? ' active' : ''}`}
          id={`action-${action.id}`}
          key={action.id}
          onClick={() => onActionClick(action)}
        >
          <div className="icon">{action.icon}</div>
          <div className="body">
            <div className="row1">
              <span className="name">{action.name}</span>
              {action.tag && <Tag variant={action.tag} />}
              {/* Gear toggle state only — a toggle never creates a CharacterEffect row, so this
                  card is the only place its on/off state is visible (not "Aktive Effekte"). */}
              {action.isActive && <span className="active-badge">Aktiv</span>}
            </div>
            {/* Full text (real rule text, e.g. Kampfrausch's whole paragraph) stays intact in the
                data and in `title` — only the display is clamped, same pattern as
                RealEffectsPanel's AvailableEffectSeal. */}
            <div className="desc" title={action.description}>{action.description}</div>
          </div>
        </button>
      ))}
    </Panel>
  );
}
