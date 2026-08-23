import { useEffect, useState } from 'react';

interface InfoButtonProps {
  label: string;
  content: string;
}

/** Tap/click-triggered replacement for `title`-attribute tooltips, which are unreachable on
 *  touch devices (no hover state) — see the (i) icons next to skill entries. */
export function InfoButton({ label, content }: InfoButtonProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open]);

  return (
    <>
      <button
        type="button"
        className="skill-note"
        aria-label={content}
        onClick={(e) => {
          e.stopPropagation();
          setOpen(true);
        }}
      >
        ⓘ
      </button>
      {open && (
        <div
          className="modal-overlay open"
          onClick={(e) => {
            if (e.target === e.currentTarget) setOpen(false);
          }}
        >
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h2>{label}</h2>
              <button type="button" className="modal-close" onClick={() => setOpen(false)}>✕</button>
            </div>
            <div className="modal-body" style={{ whiteSpace: 'pre-line' }}>{content}</div>
          </div>
        </div>
      )}
    </>
  );
}
