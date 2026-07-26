export interface StepDef {
  key: string;
  label: string;
}

interface StepperProps {
  steps: StepDef[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

export function Stepper({ steps, activeIndex, onSelect }: StepperProps) {
  return (
    <div className="stepper">
      {steps.map((step, i) => {
        const state = i === activeIndex ? 'active' : i < activeIndex ? 'done' : '';
        return (
          <div className={`step-item${state ? ` ${state}` : ''}`} key={step.key} onClick={() => onSelect(i)}>
            <div className="line" />
            <div className="dot">{i < activeIndex ? '✓' : i + 1}</div>
            <div className="label">{step.label}</div>
          </div>
        );
      })}
    </div>
  );
}
