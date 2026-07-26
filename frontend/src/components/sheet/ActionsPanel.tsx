import type { ActionOption } from '../../types/character';
import { Panel, PanelSearch } from '../primitives/Panel';
import { Tag } from '../primitives/Tag';

interface ActionsPanelProps {
  actions: ActionOption[];
  roundLabel: string;
}

export function ActionsPanel({ actions, roundLabel }: ActionsPanelProps) {
  return (
    <Panel title="Aktuelle Optionen" hint={roundLabel} beforeBody={<PanelSearch placeholder="Optionen durchsuchen" />}>
      {actions.map((action) => (
        <div className="option-card" id={`action-${action.id}`} key={action.id}>
          <div className="icon">{action.icon}</div>
          <div className="body">
            <div className="row1">
              <span className="name">{action.name}</span>
              <Tag variant={action.tag} />
            </div>
            <div className="desc">{action.description}</div>
          </div>
        </div>
      ))}
    </Panel>
  );
}
