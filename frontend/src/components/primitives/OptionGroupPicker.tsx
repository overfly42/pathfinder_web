interface OptionGroupPickerProps {
  label: string;
  max: number;
  choices: string[];
  selected: string[];
  onToggle: (choice: string) => void;
}

/** Label + pick-counter + chip-row for a "choose up to N from these choices" group
 *  (class options at creation, recurring per-level class choices at level-up). */
export function OptionGroupPicker({ label, max, choices, selected, onToggle }: OptionGroupPickerProps) {
  return (
    <div className="option-group">
      <div className="og-label">
        {label} <span className="pick-counter">(<b>{selected.length}</b>/{max})</span>
      </div>
      <div className="chip-row">
        {choices.map((choice) => {
          const active = selected.includes(choice);
          const disabled = !active && selected.length >= max;
          return (
            <button
              key={choice}
              type="button"
              className={`chip${active ? ' active' : ''}${disabled ? ' disabled' : ''}`}
              onClick={disabled ? undefined : () => onToggle(choice)}
            >
              {choice}
            </button>
          );
        })}
      </div>
    </div>
  );
}
