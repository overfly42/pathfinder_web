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
      {actions.map((action) => {
        // A daily-limited action (`ActionOption.usesRemainingToday`, e.g. Erneuerte Lebenskraft —
        // gear's own uses/charges stay folded into `description` instead, see `sheet.py`'s
        // `_build_actions`) is disabled once today's use is spent, re-enabling on the next
        // "+1 Tag"/rest call that resets every `DAILY_LIMITS` pool. `dailyLimitRemaining` is the
        // same exhaustion check for the *other* daily-pool shape (Kampfrausch, Arkaner Vorrat) —
        // display-only, doesn't change `onActionClick`'s routing the way `usesRemainingToday` does.
        const exhausted =
          (action.usesRemainingToday != null && action.usesRemainingToday <= 0) ||
          (action.dailyLimitRemaining != null && action.dailyLimitRemaining <= 0);
        return (
          <button
            type="button"
            className={`option-card${action.isActive ? ' active' : ''}`}
            id={`action-${action.id}`}
            key={action.id}
            disabled={exhausted}
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
                {action.usesRemainingToday != null && (
                  <span className="active-badge">
                    {action.usesRemainingToday}/{action.usesPerDay} heute
                  </span>
                )}
                {action.dailyLimitRemaining != null && (
                  <span className="active-badge">
                    {action.dailyLimitRemaining}/{action.dailyLimitTotal} heute
                  </span>
                )}
              </div>
              {/* Full text (real rule text, e.g. Kampfrausch's whole paragraph) stays intact in the
                  data and in `title` — only the display is clamped, same pattern as
                  RealEffectsPanel's AvailableEffectSeal. */}
              <div className="desc" title={action.description}>{action.description}</div>
            </div>
          </button>
        );
      })}
    </Panel>
  );
}
