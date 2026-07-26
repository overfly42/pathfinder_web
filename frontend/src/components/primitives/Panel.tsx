import type { ReactNode } from 'react';

interface PanelProps {
  title: string;
  hint?: string;
  /** Rendered between the head and the scrollable body, e.g. time controls or a search box. */
  beforeBody?: ReactNode;
  children: ReactNode;
  id?: string;
}

export function Panel({ title, hint, beforeBody, children, id }: PanelProps) {
  return (
    <section className="panel" id={id}>
      <div className="panel-head">
        <h2>{title}</h2>
        {hint && <span className="hint">{hint}</span>}
      </div>
      {beforeBody}
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function PanelSearch({ placeholder }: { placeholder: string }) {
  return (
    <div className="panel-search">
      <input type="text" placeholder={placeholder} />
    </div>
  );
}
